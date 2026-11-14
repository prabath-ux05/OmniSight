"""Fast, isolated unit and integration tests for OmniSight LLM conversational assistant."""

from unittest.mock import MagicMock, patch
import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.api.chat import chat_completion, get_chat_status
from backend.app.schemas.chat import (
    ChatContext,
    ChatContextFinding,
    ChatContextProposal,
    ChatContextRepair,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatStatusResponse,
)
from backend.app.services.chat_service import chat_service


# =============================================================================
# 1. Status Endpoint Tests
# =============================================================================

def test_chat_status_unconfigured(monkeypatch):
    """When no API key is configured, get_chat_status reports unconfigured with guidance."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    status_resp = get_chat_status()
    assert isinstance(status_resp, ChatStatusResponse)
    assert status_resp.configured is False
    assert status_resp.provider == "gemini"
    assert "GEMINI_API_KEY" in status_resp.message


def test_chat_status_configured_gemini(monkeypatch):
    """When GEMINI_API_KEY is configured, /status reports ready without leaking the key."""
    monkeypatch.setenv("GEMINI_API_KEY", "real-gemini-secret-token-12345")
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    status_resp = get_chat_status()
    assert status_resp.configured is True
    assert status_resp.provider == "gemini"
    assert "real-gemini-secret-token-12345" not in status_resp.message


# =============================================================================
# 2. Credential Verification & Validation Tests
# =============================================================================

def test_chat_post_missing_key_returns_503(monkeypatch):
    """Chat request without API key raises 503 Service Unavailable with actionable message."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")

    req = ChatRequest(message="Why did my Playwright test fail?")
    with pytest.raises(HTTPException) as exc_info:
        chat_completion(req, current_user=None)
    assert exc_info.value.status_code == 503
    assert "GEMINI_API_KEY" in exc_info.value.detail


def test_chat_post_empty_message_validation():
    """Empty message is rejected by Pydantic validation."""
    with pytest.raises(ValidationError):
        ChatRequest(message="")


# =============================================================================
# 3. Mock Provider Inference & Grounding Tests
# =============================================================================

def test_chat_mock_provider_with_context(monkeypatch):
    """Mock provider correctly returns grounded response with active run and finding."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    req = ChatRequest(
        message="Explain why this button could not be located.",
        history=[
            ChatMessage(role="user", content="Hello!"),
            ChatMessage(role="assistant", content="Hi! How can I help you inspect this defect?"),
        ],
        context=ChatContext(
            run_id="run_test_001",
            url="https://example.com/checkout",
            run_status="completed",
            finding=ChatContextFinding(
                finding_id="defect_001",
                category="missing_visible_element",
                severity="high",
                description="Checkout submit button missing from viewport",
                selector="#btn-submit",
                confidence=0.95,
            ),
            repair=ChatContextRepair(
                repaired=True,
                best_locator="button[data-testid='checkout-submit']",
                strategy="data_attribute",
                confidence=0.98,
                reason="Found unique matching element with data-testid",
            ),
            proposal=ChatContextProposal(
                proposal_id="prop_001",
                approval_status="pending",
                proposed_change="Update locator in test_checkout.py",
            ),
        ),
    )

    response = chat_completion(req, current_user=None)
    assert isinstance(response, ChatResponse)
    assert response.provider == "mock"
    assert "run_test_001" in response.message
    assert "defect_001" in response.message


# =============================================================================
# 4. Gemini Provider Tests (Mocked Network)
# =============================================================================

def test_chat_gemini_default_model_resolution(monkeypatch):
    """Verify default Gemini model resolves to gemini-3.5-flash-lite when GEMINI_MODEL is unset."""
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    assert chat_service._get_model("gemini") == "gemini-3.5-flash-lite"


def test_chat_gemini_successful_turn(monkeypatch):
    """Simulate successful multi-turn response from Gemini REST API."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

    mock_gemini_response = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {
                            "text": (
                                "The checkout button failed because the `#btn-submit` ID "
                                "was removed during a recent template update. OmniSight recommends "
                                "using `button[data-testid='checkout-submit']` instead."
                            )
                        }
                    ],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ]
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_gemini_response
        mock_post.return_value = mock_resp

        req = ChatRequest(
            message="Why did my selector fail?",
            history=[
                ChatMessage(role="user", content="I am having an issue with checkout"),
                ChatMessage(role="assistant", content="Let me help examine the DOM."),
            ],
            context=ChatContext(
                run_id="run_gemini_01",
                finding=ChatContextFinding(
                    finding_id="f_01",
                    selector="#btn-submit",
                ),
            ),
        )

        response = chat_completion(req, current_user=None)
        assert response.provider == "gemini"
        assert response.model == "gemini-3.5-flash-lite"
        assert "data-testid" in response.message


def test_chat_gemini_rate_limit_error(monkeypatch):
    """Gemini 429 status code is mapped to HTTP 429 with actionable message."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Quota exceeded"
        mock_post.return_value = mock_resp

        req = ChatRequest(message="Hello")
        with pytest.raises(HTTPException) as exc_info:
            chat_completion(req, current_user=None)
        assert exc_info.value.status_code == 429
        assert "rate limit" in exc_info.value.detail.lower()


def test_chat_gemini_timeout_error(monkeypatch):
    """Gemini timeout is mapped to HTTP 504 Gateway Timeout."""
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Read timed out")):
        req = ChatRequest(message="Hello")
        with pytest.raises(HTTPException) as exc_info:
            chat_completion(req, current_user=None)
        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.detail.lower()


# =============================================================================
# 5. OpenAI Provider Tests (Mocked Network)
# =============================================================================

def test_chat_openai_successful_turn(monkeypatch):
    """Simulate successful OpenAI response."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o-mini")

    mock_openai_response = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "OmniSight detected an overflow defect on the navigation container.",
                }
            }
        ]
    }

    with patch("httpx.Client.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_openai_response
        mock_post.return_value = mock_resp

        req = ChatRequest(message="What defect occurred?")
        response = chat_completion(req, current_user=None)
        assert response.provider == "openai"
        assert response.model == "gpt-4o-mini"
        assert "overflow" in response.message


# =============================================================================
# 6. Direct Function Tests
# =============================================================================

def test_direct_chat_service_methods(monkeypatch):
    """Verify chat_service directly generates responses and handles errors."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")
    req = ChatRequest(
        message="Can you analyze this?",
        history=[ChatMessage(role="user", content="Hi")],
        context=ChatContext(run_id="run_123"),
    )
    resp = chat_service.send_chat_message(req)
    assert resp.provider == "mock"
    assert "run_123" in resp.message
