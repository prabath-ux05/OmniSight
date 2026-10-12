"""Tests for the deterministic mock detector."""

import pytest
from pydantic import ValidationError

from vision_engine.detection.mock_detector import detect_mock
from vision_engine.models import VisionInput

def test_mock_detector_returns_predictable_findings():
    input_data = VisionInput(
        run_id="test_run",
        url="http://example.com",
        screenshot_path="example.png",
    )

    findings = detect_mock(input_data)

    assert len(findings) == 2
    assert findings[0].finding_id == "test_run-mock-001"
    assert findings[0].category == "layout_overflow"
    assert findings[1].category == "broken_image"
    assert all(finding.source == "mock" for finding in findings)
    assert all(0.0 <= finding.confidence <= 1.0 for finding in findings)


def test_mock_detector_preserves_evidence_paths():
    input_data = VisionInput(
        run_id="test_run",
        url="http://example.com",
        screenshot_path="example.png",
        dom_snapshot_path="example.html",
    )

    findings = detect_mock(input_data)

    assert findings[0].evidence.screenshot_path == "example.png"
    assert findings[0].evidence.dom_snapshot_path == "example.html"

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

def test_mock_detector_is_deterministic():
    input_data = VisionInput(
        run_id="repeat_test",
        url="http://example.com",
        screenshot_path="example.png",
    )

    first_result = detect_mock(input_data)
    second_result = detect_mock(input_data)

    first_dump = [finding.model_dump() for finding in first_result]
    second_dump = [finding.model_dump() for finding in second_result]

    assert first_dump == second_dump

def test_mock_detector_does_not_claim_real_detection():
    input_data = VisionInput(
        run_id="mock_test",
        url="http://example.com",
        screenshot_path="nonexistent-example.png",
    )

    findings = detect_mock(input_data)

    assert len(findings) == 2
    assert all(finding.source == "mock" for finding in findings)
    assert all("Mock finding:" in finding.description for finding in findings)