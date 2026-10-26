"""Tests for the future VLM detector interface."""

from vision_engine.detection.vlm_interface import VLMDetector
from vision_engine.models import VisionFinding, VisionInput


class StubVLMDetector:
    """Test double demonstrating the expected VLM interface."""

    def detect(self, input_data: VisionInput) -> list[VisionFinding]:
        return []


def test_detector_implementing_required_method_matches_interface():
    detector = StubVLMDetector()

    assert isinstance(detector, VLMDetector)


def test_detector_contract_accepts_existing_input_model():
    detector = StubVLMDetector()
    input_data = VisionInput(
        run_id="vlm-interface-test",
        url="https://example.com",
        screenshot_path="example.png",
    )

    findings = detector.detect(input_data)

    assert findings == []
    assert isinstance(findings, list)
