"""Real Vision-Language Model detector for the OmniSight Vision Engine."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from vision_engine.detection.providers import (
    BaseVLMProvider,
    VLMConfigurationError,
    VLMError,
    VLMProviderError,
    create_vlm_provider,
)
from vision_engine.evidence_validator import validate_evidence
from vision_engine.models import (
    BoundingBox,
    EvidenceReferences,
    VisionFinding,
    VisionInput,
)

logger = logging.getLogger(__name__)

# Category mapping and normalization
CATEGORY_NORMALIZATION: dict[str, str] = {
    "layout_overflow": "layout_overflow",
    "overflow": "layout_overflow",
    "clipping": "layout_overflow",
    "text_overlap": "layout_overflow",
    "missing_visible_element": "missing_visible_element",
    "missing_element": "missing_visible_element",
    "missing": "missing_visible_element",
    "broken_image": "broken_image",
    "missing_image": "broken_image",
    "image_error": "broken_image",
}

VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def normalize_category(raw_category: str | None) -> str | None:
    """Normalize raw model category into supported VisionFinding categories."""
    if not raw_category:
        return None
    cleaned = str(raw_category).strip().lower().replace("-", "_")
    return CATEGORY_NORMALIZATION.get(cleaned)


def normalize_severity(raw_severity: str | None) -> str:
    """Normalize model severity into valid VisionFinding severity."""
    if not raw_severity:
        return "medium"
    cleaned = str(raw_severity).strip().lower()
    return cleaned if cleaned in VALID_SEVERITIES else "medium"


def normalize_confidence(raw_confidence: Any) -> float:
    """Ensure confidence is a valid float in range [0.0, 1.0]."""
    try:
        val = float(raw_confidence)
        return max(0.0, min(1.0, val))
    except (ValueError, TypeError):
        return 0.85


def parse_bounding_box(raw_box: Any) -> BoundingBox | None:
    """Parse bounding box coordinates safely."""
    if not isinstance(raw_box, dict):
        return None
    try:
        x = float(raw_box["x"])
        y = float(raw_box["y"])
        width = max(0.0, float(raw_box["width"]))
        height = max(0.0, float(raw_box["height"]))
        return BoundingBox(x=x, y=y, width=width, height=height)
    except (KeyError, ValueError, TypeError):
        return None


def detect_vlm(
    input_data: VisionInput,
    provider: BaseVLMProvider | None = None,
    *,
    allow_fallback: bool = False,
) -> list[VisionFinding]:
    """Detect UI defects using a Vision-Language Model.

    Args:
        input_data: Inspection input containing run ID, URL, and evidence paths.
        provider: Optional pre-configured VLM provider. If None, created from environment.
        allow_fallback: If True, fall back to DOM heuristic detector when credentials
            are unavailable or an unrecoverable provider error occurs.

    Returns:
        List of structured VisionFinding objects with source="vlm" (or source="mock"
        if fallback was explicitly engaged).

    Raises:
        ValueError: If evidence validation fails.
        VLMConfigurationError: If provider credentials are missing and fallback is disabled.
        VLMProviderError: If the model API call fails and fallback is disabled.
    """
    # 1. Validate evidence files
    validation_errors = validate_evidence(input_data)
    if validation_errors:
        raise ValueError("Evidence validation failed: " + "; ".join(validation_errors))

    # 2. Resolve VLM Provider
    active_provider = provider
    if active_provider is None:
        try:
            active_provider = create_vlm_provider()
        except VLMConfigurationError as exc:
            if allow_fallback:
                logger.warning(
                    "VLM credentials not configured; falling back to deterministic DOM detector: %s",
                    exc,
                )
                from vision_engine.detection.dom_detector import detect_dom_issues
                return detect_dom_issues(input_data)
            raise

    # 3. Read evidence content
    screenshot_bytes: bytes | None = None
    if input_data.screenshot_path:
        p = Path(input_data.screenshot_path)
        if p.is_file():
            screenshot_bytes = p.read_bytes()

    dom_text: str | None = None
    if input_data.dom_snapshot_path:
        p = Path(input_data.dom_snapshot_path)
        if p.is_file():
            dom_text = p.read_text(encoding="utf-8", errors="replace")

    # 4. Invoke VLM inference
    try:
        raw_result = active_provider.analyze_ui(
            screenshot_bytes=screenshot_bytes,
            dom_text=dom_text,
            url=input_data.url,
        )
    except VLMError as exc:
        if allow_fallback:
            logger.warning(
                "VLM provider call failed; falling back to deterministic DOM detector: %s",
                exc,
            )
            from vision_engine.detection.dom_detector import detect_dom_issues
            return detect_dom_issues(input_data)
        raise

    # 5. Normalize and validate findings
    raw_defects = raw_result.get("defects")
    if raw_defects is None:
        raw_defects = raw_result.get("findings", [])
    if not isinstance(raw_defects, list):
        logger.warning("VLM response 'defects' field was not a list: %r", type(raw_defects))
        return []

    evidence = EvidenceReferences(
        screenshot_path=input_data.screenshot_path,
        dom_snapshot_path=input_data.dom_snapshot_path,
    )

    findings: list[VisionFinding] = []
    finding_counter = 1

    for defect in raw_defects:
        if not isinstance(defect, dict):
            continue

        raw_cat = defect.get("category") or defect.get("defect_category")
        category = normalize_category(raw_cat)
        if not category:
            logger.debug("Skipping defect with unsupported category: %r", raw_cat)
            continue


        severity = normalize_severity(defect.get("severity"))
        confidence = normalize_confidence(defect.get("confidence"))
        description = str(defect.get("description", "")).strip()
        if not description:
            description = f"VLM detected {category} defect."

        raw_selector = defect.get("selector")
        selector = str(raw_selector).strip() if raw_selector else None

        bounding_box = parse_bounding_box(defect.get("bounding_box"))

        finding = VisionFinding(
            finding_id=f"{input_data.run_id}-vlm-{finding_counter:03d}",
            category=category,  # type: ignore[arg-type]
            severity=severity,  # type: ignore[arg-type]
            confidence=confidence,
            description=description,
            selector=selector,
            bounding_box=bounding_box,
            evidence=evidence,
            source="vlm",
        )
        findings.append(finding)
        finding_counter += 1

    return findings


class VLMDetector:
    """Detector class executing Vision-Language Model analysis with optional fallback."""

    def __init__(
        self,
        provider: BaseVLMProvider | None = None,
        *,
        allow_fallback: bool = False,
    ):
        self.provider = provider
        self.allow_fallback = allow_fallback

    def detect(self, input_data: VisionInput) -> list[VisionFinding]:
        """Detect UI defects for given VisionInput using configured VLM provider."""
        return detect_vlm(input_data, provider=self.provider, allow_fallback=self.allow_fallback)
