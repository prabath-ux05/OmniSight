"""Tests for backend RunOrchestrator and integration pipeline connectivity.

Verifies:
- Explicit category mapping (overflow -> layout_overflow, missing_element -> missing_visible_element, etc.)
- Explicit handling of 'other' (never silently passed to backend schema)
- Severity validation against FindingResponse schema (rejecting 'info')
- Confidence preservation without fabrication
- Evidence path propagation to FindingResponse
- Pipeline evidence validation failure handling
- Full orchestrator run lifecycle and status transitions
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from backend.app.schemas.findings import EvidenceReferences, FindingResponse
from backend.app.schemas.runs import RunCreateRequest
from backend.app.services.orchestrator import (
    map_defect_category,
    map_inspection_finding_to_response,
    map_severity,
    run_orchestrator,
    RunOrchestrator,
)
from backend.app.services.run_store import run_store
from integration.contracts import DefectCategory, InspectionFinding, Severity
from navigation.navigator import NavigationResult
from vision_engine.models import (
    BoundingBox,
    EvidenceReferences as VisionEvidenceReferences,
    VisionFinding,
)


@pytest.fixture(autouse=True)
def clean_run_store():
    """Ensure in-memory repository is reset before each test."""
    run_store.clear()
    yield
    run_store.clear()


@pytest.fixture(scope="module", autouse=True)
def sample_test_artifacts():
    """Ensure sample artifact fixture files exist for testing."""
    sample_dir = Path("artifacts") / "test_sample_run"
    sample_dir.mkdir(parents=True, exist_ok=True)
    png_file = sample_dir / "before.png"
    dom_file = sample_dir / "dom.html"

    if not png_file.exists():
        png_file.write_bytes(b"\x89PNG\r\n\x1a\nfake_image_bytes")
    if not dom_file.exists():
        dom_file.write_text("<!DOCTYPE html><html><body><h1>OmniSight Test</h1></body></html>", encoding="utf-8")

    yield


# =============================================================================
# Task 5: Category Mapping Tests
# =============================================================================

def test_map_defect_category_overflow():
    """Verify 'overflow' maps to 'layout_overflow'."""
    assert map_defect_category(DefectCategory.OVERFLOW) == "layout_overflow"
    assert map_defect_category("overflow") == "layout_overflow"
    assert map_defect_category("layout_overflow") == "layout_overflow"


def test_map_defect_category_missing_element():
    """Verify 'missing_element' maps to 'missing_visible_element'."""
    assert map_defect_category(DefectCategory.MISSING_ELEMENT) == "missing_visible_element"
    assert map_defect_category("missing_element") == "missing_visible_element"
    assert map_defect_category("missing_visible_element") == "missing_visible_element"


def test_map_defect_category_broken_image():
    """Verify 'broken_image' maps to 'broken_image'."""
    assert map_defect_category(DefectCategory.BROKEN_IMAGE) == "broken_image"
    assert map_defect_category("broken_image") == "broken_image"
    assert map_defect_category("image") == "broken_image"


def test_map_defect_category_other_raises_error():
    """Verify 'other' is explicitly rejected and never passed silently to backend schema."""
    with pytest.raises(ValueError, match="category 'other' cannot be mapped"):
        map_defect_category(DefectCategory.OTHER)

    with pytest.raises(ValueError, match="category 'other' cannot be mapped"):
        map_defect_category("other")


def test_map_defect_category_unsupported_raises_error():
    """Verify unsupported categories raise descriptive ValueError."""
    with pytest.raises(ValueError, match="Unsupported defect category"):
        map_defect_category("invalid_defect_type")


def test_map_defect_category_invalid_type_raises_error():
    """Verify non-string and non-enum input raises TypeError."""
    with pytest.raises(TypeError, match="category must be a DefectCategory or str"):
        map_defect_category(123)


# =============================================================================
# Severity Validation Tests
# =============================================================================

@pytest.mark.parametrize("valid_severity", ["low", "medium", "high", "critical"])
def test_map_severity_valid_strings(valid_severity):
    """Verify all valid backend severities are accepted."""
    assert map_severity(valid_severity) == valid_severity


def test_map_severity_valid_enums():
    """Verify valid Severity enums map correctly."""
    assert map_severity(Severity.LOW) == "low"
    assert map_severity(Severity.MEDIUM) == "medium"
    assert map_severity(Severity.HIGH) == "high"
    assert map_severity(Severity.CRITICAL) == "critical"


def test_map_severity_info_rejected():
    """Verify 'info' severity is rejected because FindingResponse does not allow it."""
    with pytest.raises(ValueError, match="Severity 'info' is not permitted"):
        map_severity("info")

    with pytest.raises(ValueError, match="not permitted"):
        map_severity(Severity.INFO)


def test_map_severity_invalid_raises_error():
    """Verify unsupported severities raise descriptive ValueError."""
    with pytest.raises(ValueError, match="not permitted"):
        map_severity("catastrophic")

    with pytest.raises(TypeError, match="severity must be a Severity or str"):
        map_severity(None)


# =============================================================================
# Task 6: InspectionFinding to FindingResponse Mapping Tests
# =============================================================================

def test_map_inspection_finding_complete():
    """Verify complete InspectionFinding maps accurately to FindingResponse."""
    finding = InspectionFinding(
        defect_category=DefectCategory.OVERFLOW,
        severity=Severity.HIGH,
        description="Layout panel extends past viewport boundary.",
        selector="#metrics-panel",
        confidence=0.94,
        metadata={
            "finding_id": "defect_custom_001",
            "source": "vlm",
            "evidence": {
                "screenshot_path": "artifacts/run_100/before.png",
                "dom_snapshot_path": "artifacts/run_100/dom.html",
            },
        },
    )

    response = map_inspection_finding_to_response(finding, run_id="run_100")

    assert isinstance(response, FindingResponse)
    assert response.finding_id == "defect_custom_001"
    assert response.category == "layout_overflow"
    assert response.severity == "high"
    assert response.confidence == 0.94
    assert response.description == "Layout panel extends past viewport boundary."
    assert response.selector == "#metrics-panel"
    assert response.source == "vlm"
    assert response.evidence.screenshot_path == "artifacts/run_100/before.png"
    assert response.evidence.dom_snapshot_path == "artifacts/run_100/dom.html"


def test_map_inspection_finding_default_evidence_fallback():
    """Verify finding falls back to default evidence references when metadata omits them."""
    finding = InspectionFinding(
        defect_category=DefectCategory.BROKEN_IMAGE,
        severity=Severity.MEDIUM,
        description="Logo image failed to load.",
        selector="#app-logo",
        confidence=0.88,
        metadata={"finding_id": "defect_002"},
    )

    defaults = EvidenceReferences(
        screenshot_path="artifacts/run_default/before.png",
        dom_snapshot_path="artifacts/run_default/dom.html",
    )

    response = map_inspection_finding_to_response(finding, run_id="run_default", default_evidence=defaults)

    assert response.evidence.screenshot_path == "artifacts/run_default/before.png"
    assert response.evidence.dom_snapshot_path == "artifacts/run_default/dom.html"
    assert response.source == "mock"  # defaults to mock when not vlm


def test_map_inspection_finding_missing_confidence_raises_error():
    """Verify confidence is never fabricated; missing confidence raises ValueError."""
    finding = InspectionFinding(
        defect_category=DefectCategory.BROKEN_IMAGE,
        severity=Severity.LOW,
        description="Broken image without confidence.",
        confidence=None,
    )

    with pytest.raises(ValueError, match="missing a required confidence score"):
        map_inspection_finding_to_response(finding, run_id="run_test")


def test_map_inspection_finding_empty_description_raises_error():
    """Verify empty description raises ValueError."""
    finding = InspectionFinding(
        defect_category=DefectCategory.BROKEN_IMAGE,
        severity=Severity.LOW,
        description="Valid description",
        confidence=0.85,
    )
    finding.description = "   "

    with pytest.raises(ValueError, match="empty description"):
        map_inspection_finding_to_response(finding, run_id="run_test")


def test_map_inspection_finding_unsupported_category_raises_error():
    """Verify finding with 'other' category raises ValueError during mapping."""
    finding = InspectionFinding(
        defect_category=DefectCategory.OTHER,
        severity=Severity.LOW,
        description="Unclassified defect",
        confidence=0.8,
    )

    with pytest.raises(ValueError, match="category 'other' cannot be mapped"):
        map_inspection_finding_to_response(finding, run_id="run_test")


# =============================================================================
# Task 3 & 4: Pipeline Evidence Validation & Run ID Propagation
# =============================================================================

def test_orchestrator_handles_missing_evidence_validation_failure():
    """Verify orchestrator fails the run if evidence validation detects missing files."""
    run = run_store.create(RunCreateRequest(url="http://127.0.0.1:8000/"))

    # Navigator reports success but points to non-existent files
    mock_nav_result = NavigationResult(
        run_id=run.run_id,
        url=run.url,
        page_title="Dummy Page",
        captured_at="2026-10-25T00:00:00Z",
        viewport={"width": 1280, "height": 800},
        screenshot_path="artifacts/ghost_dir/non_existent.png",
        dom_snapshot_path="artifacts/ghost_dir/non_existent.html",
        status="success",
        error=None,
    )

    with patch("navigation.navigator.BrowserNavigator.navigate", return_value=mock_nav_result):
        run_orchestrator.execute_run(run.run_id, run.url)

    updated = run_store.get(run.run_id)
    assert updated is not None
    assert updated.status == "failed"
    assert "Evidence validation failed" in updated.error


def test_orchestrator_propagates_run_id_through_pipeline():
    """Verify the original run_id is passed through pipeline and captured in findings."""
    run = run_store.create(RunCreateRequest(url="http://127.0.0.1:8000/"))
    expected_run_id = run.run_id

    mock_nav_result = NavigationResult(
        run_id=expected_run_id,
        url=run.url,
        page_title="OmniSight",
        captured_at="2026-10-25T00:00:00Z",
        viewport={"width": 1280, "height": 800},
        screenshot_path="artifacts/test_sample_run/before.png",
        dom_snapshot_path="artifacts/test_sample_run/dom.html",
        status="success",
    )

    custom_vision_finding = VisionFinding(
        finding_id=f"custom_{expected_run_id}_01",
        category="broken_image",
        severity="medium",
        confidence=0.88,
        description="Missing topology diagram",
        selector="#diagram",
        evidence=VisionEvidenceReferences(
            screenshot_path="artifacts/test_sample_run/before.png",
            dom_snapshot_path="artifacts/test_sample_run/dom.html",
        ),
        source="mock",
    )

    def mock_detector(v_input):
        assert v_input.run_id == expected_run_id
        return [custom_vision_finding]

    with patch("navigation.navigator.BrowserNavigator.navigate", return_value=mock_nav_result):
        run_orchestrator.execute_run(expected_run_id, run.url, detector=mock_detector)

    updated = run_store.get(expected_run_id)
    assert updated is not None
    assert updated.status == "completed"

    findings = run_store.get_findings(expected_run_id)
    assert len(findings) == 1
    assert findings[0].finding_id == f"custom_{expected_run_id}_01"
    assert findings[0].category == "broken_image"
    assert findings[0].confidence == 0.88


def test_orchestrator_handles_unsupported_finding_category_in_pipeline():
    """Verify orchestrator fails gracefully if a detector returns a finding with unmappable category."""
    run = run_store.create(RunCreateRequest(url="http://127.0.0.1:8000/"))

    mock_nav_result = NavigationResult(
        run_id=run.run_id,
        url=run.url,
        page_title="OmniSight",
        captured_at="2026-10-25T00:00:00Z",
        viewport={"width": 1280, "height": 800},
        screenshot_path="artifacts/test_sample_run/before.png",
        dom_snapshot_path="artifacts/test_sample_run/dom.html",
        status="success",
    )

    def mock_bad_category_detector(v_input):
        return [
            {
                "category": "other",
                "severity": "low",
                "confidence": 0.75,
                "description": "Other issue",
                "evidence": {"screenshot_path": "artifacts/test_sample_run/before.png"},
            }
        ]

    with patch("navigation.navigator.BrowserNavigator.navigate", return_value=mock_nav_result):
        run_orchestrator.execute_run(run.run_id, run.url, detector=mock_bad_category_detector)

    updated = run_store.get(run.run_id)
    assert updated is not None
    assert updated.status == "failed"
    assert "cannot be mapped" in updated.error
