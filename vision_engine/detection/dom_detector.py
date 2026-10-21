
"""Heuristic detector for common issues in saved HTML DOM snapshots."""

from html.parser import HTMLParser
from pathlib import Path

from vision_engine.models import EvidenceReferences, VisionFinding, VisionInput


class _DOMIssueParser(HTMLParser):
    """Collect common image and form-label issues from HTML."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.issues: list[dict[str, str]] = []
        self.labelled_ids: set[str] = set()
        self.controls: list[dict[str, str | bool]] = []
        self.label_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)

        if tag == "label":
            self.label_depth += 1
            label_for = attributes.get("for")
            if label_for:
                self.labelled_ids.add(label_for)

        if tag in {"input", "select", "textarea"}:
            element_id = attributes.get("id", "")
            input_type = attributes.get("type", "").lower()

            # These input types do not normally require accessible labels.
            excluded = tag == "input" and input_type in {
                "hidden", "submit", "reset", "button", "image"
            }

            self.controls.append({
                "tag": tag,
                "id": element_id,
                "type": input_type,
                "selector": f"#{element_id}" if element_id else tag,
                "aria_label": bool(attributes.get("aria-label", "").strip()),
                "aria_labelledby": bool(
                    attributes.get("aria-labelledby", "").strip()
                ),
                "wrapped_label": self.label_depth > 0,
                "excluded": excluded,
            })

        if tag == "img":
            src = attributes.get("src")
            selector = f"#{attributes['id']}" if attributes.get("id") else "img"

            if not src or not src.strip():
                self.issues.append({
                    "category": "broken_image",
                    "severity": "medium",
                    "description": (
                        "DOM heuristic: image has a missing or empty src attribute."
                    ),
                    "selector": selector,
                })

            alt = attributes.get("alt")
            if alt is None or not alt.strip():
                self.issues.append({
                    "category": "missing_visible_element",
                    "severity": "low",
                    "description": (
                        "DOM heuristic: image has missing or empty alt text."
                    ),
                    "selector": selector,
                })

    def handle_endtag(self, tag: str) -> None:
        if tag == "label" and self.label_depth:
            self.label_depth -= 1

    def finalize_issues(self) -> None:
        """Check controls after all explicit label references are known."""
        for control in self.controls:
            element_id = str(control["id"])

            if control["excluded"]:
                continue

            has_label = (
                control["aria_label"]
                or control["aria_labelledby"]
                or control["wrapped_label"]
                or (element_id and element_id in self.labelled_ids)
            )

            if not has_label:
                self.issues.append({
                    "category": "missing_visible_element",
                    "severity": "low",
                    "description": (
                        f"DOM heuristic: <{control['tag']}> may lack "
                        "an accessible label."
                    ),
                    "selector": str(control["selector"]),
                })


def detect_dom_issues(input_data: VisionInput) -> list[VisionFinding]:
    """
    Analyze saved HTML for common image and form-label issues.

    This static heuristic does not execute JavaScript, inspect rendered layout,
    fetch image URLs, or prove that an image is broken.
    """
    if not input_data.dom_snapshot_path:
        raise ValueError("A DOM snapshot path is required.")

    path = Path(input_data.dom_snapshot_path)

    try:
        html = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Cannot read DOM snapshot: {path}") from exc

    if not html.strip():
        raise ValueError(f"DOM snapshot is empty: {path}")

    parser = _DOMIssueParser()

    try:
        parser.feed(html)
        parser.close()
        parser.finalize_issues()
    except Exception as exc:
        raise ValueError("DOM snapshot could not be parsed.") from exc

    evidence = EvidenceReferences(
        screenshot_path=input_data.screenshot_path,
        dom_snapshot_path=input_data.dom_snapshot_path,
    )

    return [
        VisionFinding(
            finding_id=f"{input_data.run_id}-dom-{index:03d}",
            category=issue["category"],
            severity=issue["severity"],
            confidence=0.70,
            description=issue["description"],
            selector=issue["selector"],
            evidence=evidence,
            source="mock",
        )
        for index, issue in enumerate(parser.issues, start=1)
    ]
