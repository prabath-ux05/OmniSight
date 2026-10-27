"""Unit tests for Vision-Language Model detector, providers, and response normalization."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import httpx
import pytest

from vision_engine.detection.providers import (
    GeminiVLMProvider,
    OpenAIVLMProvider,
    VLMConfig,
    VLMConfigurationError,
    VLMProviderError,
    VLMResponseError,
    VLMTimeoutError,
    create_vlm_provider,
)
from vision_engine.detection.vlm_detector import (
    detect_vlm,
    normalize_category,
    normalize_confidence,
    normalize_severity,
    parse_bounding_box,
)
from vision_engine.models import BoundingBox, VisionInput
from vision_engine.prompting.defect_prompts import (
    build_vlm_user_prompt,
    extract_dom_excerpt,
    parse_vlm_json_response,
)


@pytest.fixture
def sample_evidence(tmp_path: Path):
    """Create valid screenshot and DOM snapshot files."""
    screenshot = tmp_path / "before.png"
    screenshot.write_bytes(b"\x89PNG\r\n\x1a\nfake-image-bytes")

    dom = tmp_path / "dom.html"
    dom.write_text("<html><body><button id='login-btn'>Log In</button></body></html>", encoding="utf-8")

    return {
        "screenshot": str(screenshot),
        "dom": str(dom),
    }


# =============================================================================
# 1. Prompting & Response Parsing Tests
# =============================================================================

def test_extract_dom_excerpt_strips_scripts_and_styles():
    html = """
    <html>
      <head>
        <script>var x = 10;</script>
        <style>.btn { color: red; }</style>
      </head>
      <body>
        <main><h1>Hello World</h1></main>
      </body>
    </html>
    """
    excerpt = extract_dom_excerpt(html, max_chars=500)
    assert "var x = 10" not in excerpt
    assert ".btn {" not in excerpt
    assert "Hello World" in excerpt


def test_parse_vlm_json_response_with_markdown_fences():
    raw = "```json\n{\"defects\": [{\"category\": \"layout_overflow\", \"severity\": \"high\"}]}\n```"
    parsed = parse_vlm_json_response(raw)
    assert "defects" in parsed
    assert len(parsed["defects"]) == 1


def test_parse_vlm_json_response_with_surrounding_text():
    raw = "Here is the inspection analysis:\n{\"defects\": []}\nHope this helps!"
    parsed = parse_vlm_json_response(raw)
    assert parsed == {"defects": []}


def test_parse_vlm_json_response_invalid_json():
    with pytest.raises(ValueError, match="Failed to parse VLM response as JSON"):
        parse_vlm_json_response("This is not JSON at all.")


# =============================================================================
# 2. Normalization Function Tests
# =============================================================================

def test_normalize_category_aliases():
    assert normalize_category("overflow") == "layout_overflow"
    assert normalize_category("layout_overflow") == "layout_overflow"
    assert normalize_category("missing_element") == "missing_visible_element"
    assert normalize_category("missing") == "missing_visible_element"
    assert normalize_category("broken_image") == "broken_image"
    assert normalize_category("image-error") == "broken_image"
    assert normalize_category("unsupported_category_xyz") is None
    assert normalize_category(None) is None


def test_normalize_severity():
    assert normalize_severity("low") == "low"
    assert normalize_severity("HIGH") == "high"
    assert normalize_severity("critical") == "critical"
    assert normalize_severity("invalid") == "medium"
    assert normalize_severity(None) == "medium"


def test_normalize_confidence():
    assert normalize_confidence(0.95) == 0.95
    assert normalize_confidence("0.8") == 0.8
    assert normalize_confidence(1.5) == 1.0
    assert normalize_confidence(-0.5) == 0.0
    assert normalize_confidence("not_a_number") == 0.85


def test_parse_bounding_box():
    box = parse_bounding_box({"x": 10.5, "y": 20.0, "width": 100.0, "height": 50.0})
    assert isinstance(box, BoundingBox)
    assert box.x == 10.5
    assert box.width == 100.0

    # Negative width/height clamped to 0
    clamped = parse_bounding_box({"x": 0.0, "y": 0.0, "width": -10.0, "height": -5.0})
    assert clamped.width == 0.0

    # Malformed box returns None
    assert parse_bounding_box("invalid") is None
    assert parse_bounding_box({"x": 10}) is None


# =============================================================================
# 3. Provider Configuration Tests
# =============================================================================

def test_create_vlm_provider_missing_key_raises():
    cfg = VLMConfig(provider="gemini", api_key=None)
    with pytest.raises(VLMConfigurationError, match="Missing API key for provider 'gemini'"):
        create_vlm_provider(cfg)


def test_create_vlm_provider_unsupported():
    cfg = VLMConfig(provider="unsupported_provider", api_key="secret")
    with pytest.raises(VLMConfigurationError, match="Unsupported VLM provider"):
        create_vlm_provider(cfg)


def test_create_vlm_provider_gemini():
    cfg = VLMConfig(provider="gemini", api_key="test-gemini-key")
    provider = create_vlm_provider(cfg)
    assert isinstance(provider, GeminiVLMProvider)


def test_create_vlm_provider_openai():
    cfg = VLMConfig(provider="openai", api_key="test-openai-key")
    provider = create_vlm_provider(cfg)
    assert isinstance(provider, OpenAIVLMProvider)


# =============================================================================
# 4. Gemini Provider Inference Tests (Mocked)
# =============================================================================

def test_gemini_provider_successful_inference(sample_evidence):
    cfg = VLMConfig(provider="gemini", api_key="test-key")
    provider = GeminiVLMProvider(cfg)

    mock_gemini_payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": json.dumps({
                                "defects": [
                                    {
                                        "category": "layout_overflow",
                                        "severity": "high",
                                        "confidence": 0.92,
                                        "description": "Navigation bar overlaps main content",
                                        "selector": "#main-nav",
                                        "bounding_box": {"x": 0.0, "y": 0.0, "width": 800.0, "height": 60.0},
                                    }
                                ]
                            })
                        }
                    ]
                }
            }
        ]
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_gemini_payload

    with patch("httpx.Client.post", return_value=mock_resp):
        inp = VisionInput(
            run_id="run_test_gemini",
            url="http://127.0.0.1:8080/index.html",
            screenshot_path=sample_evidence["screenshot"],
            dom_snapshot_path=sample_evidence["dom"],
        )
        findings = detect_vlm(inp, provider=provider)

    assert len(findings) == 1
    f = findings[0]
    assert f.finding_id == "run_test_gemini-vlm-001"
    assert f.category == "layout_overflow"
    assert f.severity == "high"
    assert f.confidence == 0.92
    assert f.selector == "#main-nav"
    assert f.source == "vlm"
    assert f.bounding_box is not None
    assert f.bounding_box.width == 800.0
    assert f.evidence.screenshot_path == sample_evidence["screenshot"]
    assert f.evidence.dom_snapshot_path == sample_evidence["dom"]


# =============================================================================
# 5. OpenAI Provider Inference Tests (Mocked)
# =============================================================================

def test_openai_provider_successful_inference(sample_evidence):
    cfg = VLMConfig(provider="openai", api_key="test-openai-key")
    provider = OpenAIVLMProvider(cfg)

    mock_openai_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps({
                        "defects": [
                            {
                                "category": "missing_element",  # Alias to test normalization
                                "severity": "critical",
                                "confidence": 0.98,
                                "description": "Payment checkout submit button is missing",
                                "selector": "#checkout-btn",
                            },
                            {
                                "category": "broken_image",
                                "severity": "medium",
                                "confidence": 0.85,
                                "description": "Product hero image failed to render",
                                "selector": "img.hero",
                            },
                        ]
                    })
                }
            }
        ]
    }

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_openai_payload

    with patch("httpx.Client.post", return_value=mock_resp):
        inp = VisionInput(
            run_id="run_test_openai",
            url="http://127.0.0.1:8080/shop.html",
            screenshot_path=sample_evidence["screenshot"],
            dom_snapshot_path=sample_evidence["dom"],
        )
        findings = detect_vlm(inp, provider=provider)

    assert len(findings) == 2
    assert findings[0].category == "missing_visible_element"
    assert findings[0].severity == "critical"
    assert findings[0].source == "vlm"
    assert findings[1].category == "broken_image"
    assert findings[1].source == "vlm"


def test_vlm_clean_page_returns_zero_findings(sample_evidence):
    cfg = VLMConfig(provider="gemini", api_key="test-key")
    provider = GeminiVLMProvider(cfg)

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps({"defects": []})}]}}
        ]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        inp = VisionInput(
            run_id="run_clean",
            url="http://127.0.0.1:8080/clean.html",
            screenshot_path=sample_evidence["screenshot"],
        )
        findings = detect_vlm(inp, provider=provider)

    assert findings == []


# =============================================================================
# 6. Error & Fallback Handling Tests
# =============================================================================

def test_vlm_provider_timeout_error(sample_evidence):
    cfg = VLMConfig(provider="gemini", api_key="test-key")
    provider = GeminiVLMProvider(cfg)

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")):
        inp = VisionInput(
            run_id="run_timeout",
            url="http://127.0.0.1:8080/timeout.html",
            screenshot_path=sample_evidence["screenshot"],
        )
        with pytest.raises(VLMTimeoutError, match="timed out"):
            detect_vlm(inp, provider=provider, allow_fallback=False)


def test_vlm_provider_http_error(sample_evidence):
    cfg = VLMConfig(provider="openai", api_key="test-key")
    provider = OpenAIVLMProvider(cfg)

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 401
    mock_resp.text = "Unauthorized: Invalid API key"

    with patch("httpx.Client.post", return_value=mock_resp):
        inp = VisionInput(
            run_id="run_401",
            url="http://127.0.0.1:8080/auth.html",
            screenshot_path=sample_evidence["screenshot"],
        )
        with pytest.raises(VLMProviderError, match="HTTP 401"):
            detect_vlm(inp, provider=provider, allow_fallback=False)


def test_vlm_malformed_response_error(sample_evidence):
    cfg = VLMConfig(provider="gemini", api_key="test-key")
    provider = GeminiVLMProvider(cfg)

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {"content": {"parts": [{"text": "I could not analyze the image properly."}]}}
        ]
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        inp = VisionInput(
            run_id="run_malformed",
            url="http://127.0.0.1:8080/malformed.html",
            screenshot_path=sample_evidence["screenshot"],
        )
        with pytest.raises(VLMResponseError, match="Failed to parse"):
            detect_vlm(inp, provider=provider, allow_fallback=False)


def test_vlm_invalid_evidence_raises_value_error():
    cfg = VLMConfig(provider="gemini", api_key="test-key")
    provider = GeminiVLMProvider(cfg)

    inp = VisionInput(
        run_id="run_missing_evidence",
        url="http://127.0.0.1:8080",
        screenshot_path="nonexistent_file_123.png",
    )
    with pytest.raises(ValueError, match="Evidence validation failed"):
        detect_vlm(inp, provider=provider)


def test_vlm_allow_fallback_when_credentials_missing(sample_evidence, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("VISION_MODEL_PROVIDER", "gemini")

    inp = VisionInput(
        run_id="run_fallback",
        url="http://127.0.0.1:8080",
        screenshot_path=sample_evidence["screenshot"],
        dom_snapshot_path=sample_evidence["dom"],
    )

    # When fallback is allowed, it falls back to DOM detection without raising
    findings = detect_vlm(inp, provider=None, allow_fallback=True)
    assert isinstance(findings, list)
    # Mock / DOM findings have source="mock", never "vlm"
    for f in findings:
        assert f.source == "mock"


def test_vlm_allow_fallback_when_provider_times_out(sample_evidence):
    cfg = VLMConfig(provider="gemini", api_key="test-key")
    provider = GeminiVLMProvider(cfg)

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Network timeout")):
        inp = VisionInput(
            run_id="run_fallback_timeout",
            url="http://127.0.0.1:8080",
            screenshot_path=sample_evidence["screenshot"],
            dom_snapshot_path=sample_evidence["dom"],
        )
        findings = detect_vlm(inp, provider=provider, allow_fallback=True)
        assert isinstance(findings, list)
        for f in findings:
            assert f.source == "mock"
