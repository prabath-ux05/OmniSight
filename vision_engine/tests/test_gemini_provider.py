from PIL import Image
from vision_engine.models import BoundingBox

import base64
from types import SimpleNamespace

import pytest

from vision_engine.detection.gemini_provider import GeminiVLMDetector
from vision_engine.models import BoundingBox, VisionInput


class FakeInteractions:
    def __init__(self, output_text="[]"):
        self.output_text = output_text
        self.received = None
        self.calls = 0

    def create(self, **kwargs):
        self.received = kwargs
        self.calls += 1
        return SimpleNamespace(output_text=self.output_text)


class FakeClient:
    def __init__(self, output_text="[]"):
        self.interactions = FakeInteractions(output_text)


def make_input(tmp_path, filename="test.html"):
    dom_path = tmp_path / filename
    dom_path.write_text(
        "<html><body><h1>Test page</h1></body></html>",
        encoding="utf-8",
    )

    return VisionInput(
        run_id="test-run",
        url="https://example.com",
        dom_snapshot_path=str(dom_path),
    )


def test_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    monkeypatch.setattr(
        "vision_engine.detection.gemini_provider.load_dotenv",
        lambda: None,
    )

    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        GeminiVLMDetector()


def test_provider_rejects_invalid_timeout():
    with pytest.raises(ValueError):
        GeminiVLMDetector(
            api_key="test-key",
            timeout_seconds=0,
            client=FakeClient(),
        )


def test_provider_reads_dom(tmp_path):
    detector = GeminiVLMDetector(client=FakeClient())
    dom_path = tmp_path / "page.html"
    dom_path.write_text("<html><body>Hello</body></html>", encoding="utf-8")

    result = detector._read_dom(str(dom_path))

    assert "Hello" in result


def test_provider_rejects_empty_dom(tmp_path):
    detector = GeminiVLMDetector(client=FakeClient())
    dom_path = tmp_path / "empty.html"
    dom_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError):
        detector._read_dom(str(dom_path))


def test_provider_rejects_unsupported_screenshot(tmp_path):
    detector = GeminiVLMDetector(client=FakeClient())
    screenshot_path = tmp_path / "image.txt"
    screenshot_path.write_text("not an image", encoding="utf-8")

    with pytest.raises(ValueError):
        detector._read_screenshot(str(screenshot_path))


def test_provider_sends_dom_and_returns_findings(tmp_path):
    client = FakeClient(output_text="[]")
    detector = GeminiVLMDetector(client=client)
    input_data = make_input(tmp_path)

    findings = detector.detect(input_data)

    assert findings == []
    assert client.interactions.received is not None
    assert client.interactions.calls == 1


def test_provider_rejects_invalid_model_response(tmp_path):
    client = FakeClient(output_text="This is not valid JSON")
    detector = GeminiVLMDetector(client=client)
    input_data = make_input(tmp_path)

    with pytest.raises(ValueError):
        detector.detect(input_data)


def test_provider_reads_screenshot(tmp_path):
    detector = GeminiVLMDetector(client=FakeClient())
    screenshot_path = tmp_path / "screenshot.png"
    screenshot_path.write_bytes(b"fake-png-data")

    result = detector._read_screenshot(str(screenshot_path))

    assert result is not None


def test_provider_sends_screenshot_to_gemini(tmp_path):
    client = FakeClient(output_text="[]")
    detector = GeminiVLMDetector(client=client)

    screenshot_path = tmp_path / "screenshot.png"
    screenshot_path.write_bytes(b"fake-png-data")

    input_data = VisionInput(
        run_id="screenshot-test",
        url="https://example.com",
        screenshot_path=str(screenshot_path),
    )

    findings = detector.detect(input_data)

    assert findings == []
    assert client.interactions.received is not None
    assert client.interactions.calls == 1


def test_provider_configures_client_timeout(monkeypatch):
    captured = {}

    class FakeGenAIClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        "vision_engine.detection.gemini_provider.genai.Client",
        FakeGenAIClient,
    )
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    GeminiVLMDetector(timeout_seconds=30)

    assert captured["http_options"] == {"timeout": 30000}


class FakeAPIError(Exception):
    def __init__(self, code):
        super().__init__(f"HTTP {code}")
        self.code = code


class SequenceInteractions:
    def __init__(self, responses):
        self.responses = responses
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        response = self.responses.pop(0)

        if isinstance(response, Exception):
            raise response

        return response


class SequenceClient:
    def __init__(self, responses):
        self.interactions = SequenceInteractions(responses)


def test_provider_retries_after_temporary_server_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "vision_engine.detection.gemini_provider.time.sleep",
        lambda _: None,
    )

    client = SequenceClient([
        FakeAPIError(503),
        SimpleNamespace(output_text="[]"),
    ])

    detector = GeminiVLMDetector(client=client)
    input_data = make_input(tmp_path, "retry.html")

    findings = detector.detect(input_data)

    assert findings == []
    assert client.interactions.calls == 2


def test_provider_stops_after_three_failed_attempts(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "vision_engine.detection.gemini_provider.time.sleep",
        lambda _: None,
    )

    client = SequenceClient([
        FakeAPIError(503),
        FakeAPIError(503),
        FakeAPIError(503),
    ])

    detector = GeminiVLMDetector(client=client)
    input_data = make_input(tmp_path, "retry_failure.html")

    with pytest.raises(RuntimeError, match="HTTP 503"):
        detector.detect(input_data)

    assert client.interactions.calls == 3


def test_provider_does_not_retry_non_retryable_error(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "vision_engine.detection.gemini_provider.time.sleep",
        lambda _: None,
    )

    client = SequenceClient([
        FakeAPIError(400),
    ])

    detector = GeminiVLMDetector(client=client)
    input_data = make_input(tmp_path, "non_retry.html")

    with pytest.raises(RuntimeError, match="HTTP 400"):
        detector.detect(input_data)

    assert client.interactions.calls == 1



def test_provider_sends_cropped_screenshot_to_gemini(tmp_path):
    client = FakeClient(output_text="[]")
    detector = GeminiVLMDetector(client=client)

    screenshot_path = tmp_path / "screenshot.png"
    Image.new("RGB", (200, 150), "white").save(screenshot_path)

    input_data = VisionInput(
        run_id="crop-test",
        url="https://example.com",
        screenshot_path=str(screenshot_path),
        crop_box=BoundingBox(
            x=50,
            y=40,
            width=60,
            height=30,
        ),
    )

    findings = detector.detect(input_data)

    sent_image = client.interactions.received["input"][1]

    assert findings == []
    assert sent_image["type"] == "image"
    assert sent_image["mime_type"] == "image/png"

    decoded_image = base64.b64decode(sent_image["data"])

    from io import BytesIO

    with Image.open(BytesIO(decoded_image)) as image:
        assert image.size == (100, 70)


def test_provider_falls_back_to_original_when_cropping_fails(
    tmp_path,
    monkeypatch,
):
    client = FakeClient(output_text="[]")
    detector = GeminiVLMDetector(client=client)

    screenshot_path = tmp_path / "screenshot.png"
    screenshot_path.write_bytes(b"original-screenshot-data")

    input_data = VisionInput(
        run_id="crop-fallback-test",
        url="https://example.com",
        screenshot_path=str(screenshot_path),
        crop_box=BoundingBox(
            x=50,
            y=40,
            width=60,
            height=30,
        ),
    )

    monkeypatch.setattr(
        "vision_engine.detection.gemini_provider.crop_screenshot_with_origin",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError("Cropping failed")
        ),
    )

    findings = detector.detect(input_data)

    sent_image = client.interactions.received["input"][1]

    assert findings == []
    assert base64.b64decode(sent_image["data"]) == b"original-screenshot-data"


def test_provider_sends_original_screenshot_without_crop_box(tmp_path):
    client = FakeClient(output_text="[]")
    detector = GeminiVLMDetector(client=client)

    screenshot_path = tmp_path / "screenshot.png"
    screenshot_path.write_bytes(b"original-screenshot-data")

    input_data = VisionInput(
        run_id="original-image-test",
        url="https://example.com",
        screenshot_path=str(screenshot_path),
    )

    findings = detector.detect(input_data)

    sent_image = client.interactions.received["input"][1]

    assert findings == []
    assert base64.b64decode(sent_image["data"]) == b"original-screenshot-data"



def test_provider_translates_cropped_bounding_box_to_original_coordinates(
    tmp_path,
):
    response = """
    [
        {
            "finding_id": "crop-defect",
            "category": "layout_overflow",
            "severity": "high",
            "confidence": 0.95,
            "description": "Content overflows its container.",
            "repair_recommendation": null,
            "selector": "#content",
            "bounding_box": {
                "x": 20,
                "y": 30,
                "width": 40,
                "height": 25
            },
            "evidence": {
                "screenshot_path": null,
                "dom_snapshot_path": null
            },
            "source": "vlm"
        }
    ]
    """

    client = FakeClient(output_text=response)
    detector = GeminiVLMDetector(client=client)

    screenshot_path = tmp_path / "coordinate-test.png"
    Image.new("RGB", (200, 150), "white").save(screenshot_path)

    input_data = VisionInput(
        run_id="coordinate-test",
        url="https://example.com",
        screenshot_path=str(screenshot_path),
        crop_box=BoundingBox(
            x=50,
            y=40,
            width=60,
            height=30,
        ),
    )

    findings = detector.detect(input_data)

    assert len(findings) == 1
    assert findings[0].bounding_box == BoundingBox(
        x=50,
        y=50,
        width=40,
        height=25,
    )


def test_provider_keeps_coordinates_unchanged_when_crop_fails(
    tmp_path,
    monkeypatch,
):
    response = """
    [
        {
            "finding_id": "fallback-defect",
            "category": "layout_overflow",
            "severity": "high",
            "confidence": 0.95,
            "description": "Content overflows its container.",
            "repair_recommendation": null,
            "selector": "#content",
            "bounding_box": {
                "x": 20,
                "y": 30,
                "width": 40,
                "height": 25
            },
            "evidence": {
                "screenshot_path": null,
                "dom_snapshot_path": null
            },
            "source": "vlm"
        }
    ]
    """

    client = FakeClient(output_text=response)
    detector = GeminiVLMDetector(client=client)

    screenshot_path = tmp_path / "fallback-coordinate-test.png"
    screenshot_path.write_bytes(b"original-screenshot-data")

    input_data = VisionInput(
        run_id="fallback-coordinate-test",
        url="https://example.com",
        screenshot_path=str(screenshot_path),
        crop_box=BoundingBox(
            x=50,
            y=40,
            width=60,
            height=30,
        ),
    )

    monkeypatch.setattr(
        "vision_engine.detection.gemini_provider.crop_screenshot_with_origin",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            ValueError("Cropping failed")
        ),
    )

    findings = detector.detect(input_data)

    assert len(findings) == 1
    assert findings[0].bounding_box == BoundingBox(
        x=20,
        y=30,
        width=40,
        height=25,
    )



def test_provider_analyzes_multiple_crops_and_translates_coordinates(
    tmp_path,
):
    first_response = """
    [
        {
            "finding_id": "first-crop-defect",
            "category": "layout_overflow",
            "severity": "high",
            "confidence": 0.95,
            "description": "Overflow in first region.",
            "repair_recommendation": null,
            "selector": "#first",
            "bounding_box": {
                "x": 5,
                "y": 6,
                "width": 20,
                "height": 15
            },
            "evidence": {
                "screenshot_path": null,
                "dom_snapshot_path": null
            },
            "source": "vlm"
        }
    ]
    """

    second_response = """
    [
        {
            "finding_id": "second-crop-defect",
            "category": "broken_image",
            "severity": "medium",
            "confidence": 0.90,
            "description": "Broken image in second region.",
            "repair_recommendation": null,
            "selector": "#second",
            "bounding_box": {
                "x": 7,
                "y": 8,
                "width": 30,
                "height": 25
            },
            "evidence": {
                "screenshot_path": null,
                "dom_snapshot_path": null
            },
            "source": "vlm"
        }
    ]
    """

    client = SequenceClient([
        SimpleNamespace(output_text=first_response),
        SimpleNamespace(output_text=second_response),
    ])

    detector = GeminiVLMDetector(client=client)

    screenshot_path = tmp_path / "multiple-crops.png"
    Image.new("RGB", (400, 300), "white").save(screenshot_path)

    input_data = VisionInput(
        run_id="multiple-crops-test",
        url="https://example.com",
        screenshot_path=str(screenshot_path),
        crop_boxes=[
            BoundingBox(x=50, y=40, width=60, height=30),
            BoundingBox(x=200, y=150, width=60, height=30),
        ],
    )

    findings = detector.detect(input_data)

    assert client.interactions.calls == 2
    assert len(findings) == 2

    assert findings[0].bounding_box == BoundingBox(
        x=35,
        y=26,
        width=20,
        height=15,
    )

    assert findings[1].bounding_box == BoundingBox(
        x=187,
        y=138,
        width=30,
        height=25,
    )



def test_provider_falls_back_to_original_if_any_crop_fails(
    tmp_path,
    monkeypatch,
):
    client = FakeClient(output_text="[]")
    detector = GeminiVLMDetector(client=client)

    screenshot_path = tmp_path / "multiple-crop-fallback.png"
    Image.new("RGB", (400, 300), "white").save(screenshot_path)
    original_data = screenshot_path.read_bytes()

    input_data = VisionInput(
        run_id="multiple-crop-fallback",
        url="https://example.com",
        screenshot_path=str(screenshot_path),
        crop_boxes=[
            BoundingBox(x=50, y=40, width=60, height=30),
            BoundingBox(x=200, y=150, width=60, height=30),
        ],
    )

    from vision_engine.detection import gemini_provider

    original_crop_function = (
        gemini_provider.crop_screenshot_with_origin
    )

    calls = {"count": 0}

    def fail_second_crop(path, box):
        calls["count"] += 1

        if calls["count"] == 2:
            raise ValueError("Second crop failed")

        return original_crop_function(path, box)

    monkeypatch.setattr(
        gemini_provider,
        "crop_screenshot_with_origin",
        fail_second_crop,
    )

    findings = detector.detect(input_data)

    assert findings == []
    assert calls["count"] == 2
    assert client.interactions.calls == 1

    sent_image = client.interactions.received["input"][1]

    assert base64.b64decode(sent_image["data"]) == original_data
