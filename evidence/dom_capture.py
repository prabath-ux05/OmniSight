
"""
DOM Capture

Features:
- Capture website HTML
- Save before and after DOM snapshots
- Collect DOM element information
- Collect image, form, and interactive element details
- Save DOM metadata as JSON
- Verify evidence files
- Maintain backward compatibility
"""

from pathlib import Path
from datetime import datetime, timezone
from html.parser import HTMLParser
import json

from navigation.url_validator import validate_run_id


class DOMMetadataParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.total_elements = 0
        self.tag_counts = {}
        self.images = []
        self.forms = []
        self.interactive_elements = []
        self.current_form = None

    def handle_starttag(self, tag, attrs):

        attributes = dict(attrs)

        self.total_elements += 1

        self.tag_counts[tag] = (
            self.tag_counts.get(tag, 0) + 1
        )

        if tag == "img":
            self.images.append({
                "alt": attributes.get("alt", ""),
                "has_alt": bool(attributes.get("alt"))
            })

        if tag == "form":
            self.current_form = {
                "method": attributes.get(
                    "method", "get"
                ).lower(),
                "field_types": []
            }
            self.forms.append(self.current_form)

        if tag in ("input", "textarea", "select"):
            if self.current_form is not None:

                field_type = (
                    attributes.get("type", "text")
                    if tag == "input"
                    else tag
                )

                self.current_form["field_types"].append(
                    field_type
                )

        if tag in ("button", "a", "select", "textarea"):
            self.interactive_elements.append({
                "tag": tag,
                "type": attributes.get("type"),
                "role": attributes.get("role"),
                "aria_label": attributes.get("aria-label")
            })

        elif attributes.get("role") in (
            "button", "link", "checkbox",
            "radio", "tab", "menuitem"
        ):
            self.interactive_elements.append({
                "tag": tag,
                "type": attributes.get("type"),
                "role": attributes.get("role"),
                "aria_label": attributes.get("aria-label")
            })

    def handle_endtag(self, tag):
        if tag == "form":
            self.current_form = None


class DOMCapture:

    @staticmethod
    def save_dom_snapshot(
        page,
        run_id: str,
        artifact_root: str = "artifacts",
        stage: str = None
    ) -> str:

        # Validate run ID
        is_valid, message = validate_run_id(run_id)

        if not is_valid:
            raise ValueError(message)

        run_id = run_id.strip()

        # Validate stage
        if stage not in (None, "before", "after"):
            raise ValueError(
                "stage must be 'before', 'after', or None"
            )

        # Create run directory
        run_dir = Path(artifact_root) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Preserve existing filenames
        if stage is None:
            dom_filename = "dom.html"
            metadata_filename = "dom_metadata.json"
        else:
            dom_filename = f"{stage}_dom.html"
            metadata_filename = f"{stage}_dom_metadata.json"

        dom_path = run_dir / dom_filename

        # Capture HTML
        html_content = page.content()

        if not html_content:
            raise ValueError("DOM snapshot is empty")

        # Save staged or default HTML snapshot
        dom_path.write_text(
            html_content,
            encoding="utf-8"
        )

        # Save backward-compatible filenames for the before stage
        if stage == "before":
            legacy_dom_path = run_dir / "dom.html"
            legacy_dom_path.write_text(
                html_content,
                encoding="utf-8"
            )

        # Verify HTML file
        if not dom_path.exists() or dom_path.stat().st_size == 0:
            raise FileNotFoundError(
                "DOM snapshot file was not created"
            )

        # Parse DOM information
        parser = DOMMetadataParser()
        parser.feed(html_content)
        parser.close()

        # Collect page metadata
        metadata = {
            "run_id": run_id,
            "stage": stage or "default",
            "url": getattr(page, "url", ""),
            "page_title": "",
            "captured_at": datetime.now(
                timezone.utc
            ).isoformat(),
            "dom_snapshot_path": str(dom_path),
            "total_elements": parser.total_elements,
            "tag_counts": parser.tag_counts,
            "total_images": len(parser.images),
            "images": parser.images,
            "total_forms": len(parser.forms),
            "forms": parser.forms,
            "total_interactive_elements": len(
                parser.interactive_elements
            ),
            "interactive_elements": parser.interactive_elements
        }

        # Capture page title safely
        try:
            metadata["page_title"] = page.title()
        except Exception:
            metadata["page_title"] = ""

        # Save metadata JSON
        metadata_path = run_dir / metadata_filename

        with open(
            metadata_path,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                metadata,
                file,
                indent=4,
                ensure_ascii=False
            )

        # Save backward-compatible metadata for before stage
        if stage == "before":
            legacy_metadata_path = run_dir / "dom_metadata.json"

            with open(
                legacy_metadata_path,
                "w",
                encoding="utf-8"
            ) as file:
                json.dump(
                    metadata,
                    file,
                    indent=4,
                    ensure_ascii=False
                )

        return str(dom_path)
