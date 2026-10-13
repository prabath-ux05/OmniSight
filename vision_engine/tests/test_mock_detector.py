"""Tests for the deterministic mock detector."""

import pytest
from pydantic import ValidationError

from vision_engine.detection.mock_detector import detect_mock
from vision_engine.models import VisionInput
from pathlib import Path

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
