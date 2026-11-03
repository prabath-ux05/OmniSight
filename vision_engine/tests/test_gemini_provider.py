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
        "vision_engine.detection.gemini_provider.crop_screenshot",
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
