"""Tests for the deterministic mock detector."""

import pytest
from pydantic import ValidationError

from vision_engine.detection.mock_detector import detect_mock
from vision_engine.models import EvidenceReferences, VisionFinding, VisionInput

def test_mock_detector_returns_predictable_findings(tmp_path):
    screenshot = tmp_path / "example.png"
    screenshot.write_bytes(b"fake image data")

    input_data = VisionInput(
        run_id="test_run",
        url="http://example.com",
        screenshot_path=str(screenshot),
    )

    findings = detect_mock(input_data)

    assert len(findings) == 2
    assert findings[0].category == "layout_overflow"
    assert findings[1].category == "broken_image"
    assert all(finding.source == "mock" for finding in findings)


def test_mock_detector_preserves_evidence_paths(tmp_path):
    screenshot = tmp_path / "example.png"
    dom_snapshot = tmp_path / "example.html"

    screenshot.write_bytes(b"fake image data")
    dom_snapshot.write_text("<html></html>", encoding="utf-8")

    input_data = VisionInput(
        run_id="test_run",
        url="http://example.com",
        screenshot_path=str(screenshot),
        dom_snapshot_path=str(dom_snapshot),
    )

    findings = detect_mock(input_data)

    assert len(findings) == 2

    for finding in findings:
        assert finding.evidence.screenshot_path == str(screenshot)
        assert finding.evidence.dom_snapshot_path == str(dom_snapshot)


def test_input_rejects_missing_evidence():
    with pytest.raises(ValidationError):
        VisionInput(
            run_id="test_run",
            url="http://example.com",
        )


def test_input_rejects_empty_run_id():
    with pytest.raises(ValidationError):
        VisionInput(
            run_id="",
            url="http://example.com",
            screenshot_path="example.png",
        )

def test_mock_detector_is_deterministic(tmp_path):
    screenshot = tmp_path / "example.png"
    screenshot.write_bytes(b"fake image data")

    input_data = VisionInput(
        run_id="repeat_test",
        url="http://example.com",
        screenshot_path=str(screenshot),
    )

    first_result = detect_mock(input_data)
    second_result = detect_mock(input_data)

    first_dump = [finding.model_dump() for finding in first_result]
    second_dump = [finding.model_dump() for finding in second_result]

    assert first_dump == second_dump

def test_mock_detector_does_not_claim_real_detection(tmp_path):
    screenshot = tmp_path / "missing.png"

    input_data = VisionInput(
        run_id="test-006",
        url="https://example.com",
        screenshot_path=str(screenshot),
    )

    with pytest.raises(ValueError, match="Evidence validation failed"):
        detect_mock(input_data)

def test_mock_detector_clean_scenario_returns_no_findings(tmp_path):
    screenshot = tmp_path / "clean_page.png"
    screenshot.write_bytes(b"mock screenshot data")

    input_data = VisionInput(
        run_id="clean-test",
        url="https://example.com",
        screenshot_path=str(screenshot),
    )

    findings = detect_mock(input_data, scenario="clean")

    assert findings == []


def test_mock_detector_clean_scenario_still_validates_evidence():
    input_data = VisionInput(
        run_id="invalid-clean-test",
        url="https://example.com",
        screenshot_path="missing_screenshot.png",
    )

    with pytest.raises(ValueError, match="Evidence validation failed"):
        detect_mock(input_data, scenario="clean")

def test_mock_detector_rejects_unsupported_scenario(tmp_path):
    screenshot = tmp_path / "example.png"
    screenshot.write_bytes(b"fake image data")

    input_data = VisionInput(
        run_id="invalid-scenario-test",
        url="https://example.com",
        screenshot_path=str(screenshot),
    )

    with pytest.raises(
        ValueError,
        match="Unsupported mock scenario",
    ):
        detect_mock(input_data, scenario="unknown")

def test_input_rejects_empty_url():
    with pytest.raises(ValidationError):
        VisionInput(
            run_id="test-empty-url",
            url="",
            screenshot_path="example.png",
        )


def test_finding_rejects_unsupported_category():

    with pytest.raises(ValidationError):
        VisionFinding(
            finding_id="test-001",
            category="unknown_category",
            severity="medium",
            confidence=0.9,
            description="Test finding",
            evidence=EvidenceReferences(),
            source="mock",
        )


def test_finding_rejects_confidence_above_one():

    with pytest.raises(ValidationError):
        VisionFinding(
            finding_id="test-002",
            category="layout_overflow",
            severity="medium",
            confidence=1.1,
            description="Test finding",
            evidence=EvidenceReferences(),
            source="mock",
        )


def test_finding_rejects_negative_confidence():

    with pytest.raises(ValidationError):
        VisionFinding(
            finding_id="test-003",
            category="layout_overflow",
            severity="medium",
            confidence=-0.1,
            description="Test finding",
            evidence=EvidenceReferences(),
            source="mock",
        )

def test_finding_rejects_unsupported_severity():

    with pytest.raises(ValidationError):
        VisionFinding(
            finding_id="test-invalid-severity",
            category="layout_overflow",
            severity="urgent",
            confidence=0.9,
            description="Test finding",
            evidence=EvidenceReferences(),
            source="mock",
        )

def test_finding_accepts_null_bounding_box():
    finding = VisionFinding(
        finding_id="test-bbox-null",
        category="layout_overflow",
        severity="medium",
        confidence=0.9,
        description="Test finding",
        bounding_box=None,
        evidence=EvidenceReferences(),
    )

    assert finding.bounding_box is None


def test_finding_accepts_valid_bounding_box():
    finding = VisionFinding(
        finding_id="test-bbox-valid",
        category="layout_overflow",
        severity="medium",
        confidence=0.9,
        description="Test finding",
        bounding_box={
            "x": 120,
            "y": 240,
            "width": 300,
            "height": 150,
        },
        evidence=EvidenceReferences(),
    )

    assert finding.bounding_box.x == 120
    assert finding.bounding_box.y == 240
    assert finding.bounding_box.width == 300
    assert finding.bounding_box.height == 150


def test_evidence_references_allow_missing_paths():
    evidence = EvidenceReferences()

    assert evidence.screenshot_path is None
    assert evidence.dom_snapshot_path is None

def test_finding_rejects_negative_bounding_box_dimensions():
    with pytest.raises(ValidationError):
        VisionFinding(
            finding_id="test-bbox-negative",
            category="layout_overflow",
            severity="medium",
            confidence=0.9,
            description="Test finding",
            bounding_box={
                "x": 10,
                "y": 20,
                "width": -100,
                "height": 50,
            },
            evidence=EvidenceReferences(),
        )
