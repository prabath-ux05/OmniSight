"""OmniSight Conversational LLM Service.

Integrates real multimodal LLM providers (Google Gemini, OpenAI) to provide
an open-ended, domain-aware, multi-turn conversational assistant for OmniSight.
Credentials remain strictly on the backend and are never exposed to the client.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from fastapi import HTTPException, status

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schemas.chat import (
    ChatContext,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatStatusResponse,
)

SYSTEM_PROMPT = """You are the OmniSight Assistant, an expert AI engineer embedded in OmniSight — the Multimodal UI Self-Healing & RPA platform.

### OmniSight Architecture & Core Capabilities:
1. **Browser Agent**: Built with Playwright Chromium. Navigates target web URLs, monitors browser console errors and JS exceptions, and captures comprehensive evidence (full-viewport PNG screenshots and complete DOM snapshots).
2. **Vision & Intelligence Engine**: Analyzes captured visual and DOM evidence using Vision-Language Models (Google Gemini, OpenAI GPT-4o) and static DOM heuristics. Detects defect categories:
   - `layout_overflow`: Visual overflow beyond viewport or container boundaries.
   - `missing_visible_element`: Elements queried by automation/tests that are missing or hidden in layout.
   - `broken_image`: Images that failed to load (HTTP 404, broken src) or rendered with zero natural width/height.
   Severities: `critical`, `high`, `medium`, `low`.
3. **Autonomous Self-Healing & Locator Synthesis Engine**:
   - Analyzes DOM snapshots to synthesize resilient replacement locators when target selectors break.
   - Prioritizes robust locator strategies:
     1. Data Attributes (`data-testid`, `data-cy`, `data-qa`)
     2. Stable Semantic IDs
     3. Accessible Role & Name (`role="button"`, aria labels)
     4. Unique Text Content
     5. Semantic Tag + Class hierarchy
   - Enforces empirical validation: checks candidate uniqueness in the DOM snapshot and verifies candidates on the live target page before proposing.
4. **Human-in-the-Loop Governance & PR Generation**:
   - Generates minimal, unified test code diffs targeting test files (e.g. `tests/e2e/test_checkout.py`).
   - Requires explicit user authorization gate before creating pull requests (Simulation Mode or live GitHub PR).
5. **Inspection Lifecycle States**: `queued` -> `capturing` -> `analyzing` -> `completed` (or `failed`).

### Behavioral Guidelines:
- **Open-Ended Assistance**: Answer both specific OmniSight questions and broad technical questions (e.g., CSS selectors, XPath, Playwright, web test flakiness, responsive design, browser automation).
- **Grounded in Active Context**: When active inspection context (target URL, run status, finding details, repair candidate, proposal) is provided in the prompt, reference those exact facts accurately.
- **Empirical Honesty**: If a detail is not provided or uncertain, communicate that clearly. Never hallucinate run IDs, locator scores, or defect details that were not provided.
- **Tone & Formatting**: Professional, helpful, concise, and technically precise. Format responses with markdown, code spans (`like_this`), bullet points, and code blocks where helpful.
"""


class ChatService:
    """Manages conversational interactions with LLM providers."""

    GEMINI_API_URL = "https://generativelanguage.googleapis.com"
    OPENAI_API_URL = "https://api.openai.com"

    def _get_provider(self) -> str:
        """Resolve the active LLM provider name."""
        return (
            os.getenv("LLM_PROVIDER")
            or os.getenv("CHAT_PROVIDER")
            or os.getenv("VISION_MODEL_PROVIDER")
            or "gemini"
        ).strip().lower()

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Resolve backend API key for the requested provider."""
        if provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            return key.strip() if key else None
        elif provider == "mock":
            return "mock-key"
        else:
            # Default to gemini
            key = os.getenv("GEMINI_API_KEY")
            return key.strip() if key else None

    def _get_model(self, provider: str) -> str:
        """Resolve model name for the provider."""
        if provider == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        elif provider == "mock":
            return "mock-chat-model"
        else:
            return os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite").strip()

    def _get_timeout(self) -> float:
        """Resolve request timeout in seconds."""
        try:
            return float(os.getenv("CHAT_TIMEOUT_SECONDS", "30.0"))
        except ValueError:
            return 30.0

    def get_status(self) -> ChatStatusResponse:
        """Check LLM configuration and readiness without exposing secret keys."""
        provider = self._get_provider()
        api_key = self._get_api_key(provider)
        model = self._get_model(provider)
        is_configured = bool(api_key and api_key != "your_gemini_api_key_here")

        if is_configured:
            message = f"LLM Assistant ready using provider '{provider}' and model '{model}'."
        else:
            key_name = "OPENAI_API_KEY" if provider == "openai" else "GEMINI_API_KEY"
            message = (
                f"LLM Assistant is not configured. Please set the '{key_name}' "
                f"environment variable in the backend to enable conversational AI."
            )

        return ChatStatusResponse(
            configured=is_configured,
            provider=provider,
            model=model,
            message=message,
        )

    def _format_context_block(self, ctx: Optional[ChatContext]) -> str:
        """Format active run/finding/repair context into a grounding prompt block."""
        if not ctx:
            return ""

        lines = ["[ACTIVE INSPECTION CONTEXT]"]
        if ctx.run_id:
            lines.append(f"• Run ID: {ctx.run_id}")
        if ctx.url:
            lines.append(f"• Target URL: {ctx.url}")
        if ctx.run_status:
            lines.append(f"• Run Status: {ctx.run_status}")

        if ctx.finding:
            f = ctx.finding
            lines.append(f"• Active Finding: #{f.finding_id or 'N/A'}")
            if f.category:
                lines.append(f"  - Category: {f.category}")
            if f.severity:
                lines.append(f"  - Severity: {f.severity.upper()}")
            if f.description:
                lines.append(f"  - Description: {f.description}")
            if f.selector:
                lines.append(f"  - Target Selector: `{f.selector}`")
            if f.confidence is not None:
                lines.append(f"  - Detection Confidence: {round(f.confidence * 100)}%")

        if ctx.repair:
            r = ctx.repair
            lines.append(f"• Synthesized Repair Candidate:")
            if r.best_locator:
                lines.append(f"  - Best Locator: `{r.best_locator}`")
            if r.strategy:
                lines.append(f"  - Strategy: {r.strategy}")
            if r.confidence is not None:
                lines.append(f"  - Resilience Score: {round(r.confidence * 100)}%")
            if r.reason:
                lines.append(f"  - Engine Note: {r.reason}")

        if ctx.proposal:
            p = ctx.proposal
            lines.append(f"• Active Proposal: #{p.proposal_id or 'N/A'}")
            if p.approval_status:
                lines.append(f"  - Approval Status: {p.approval_status}")
            if p.proposed_change:
                lines.append(f"  - Proposed Change: {p.proposed_change}")

        return "\n".join(lines)

    def send_chat_message(self, request: ChatRequest) -> ChatResponse:
        """Process a conversational query using the configured LLM provider."""
        provider = self._get_provider()
        api_key = self._get_api_key(provider)
        model = self._get_model(provider)

        if not api_key or api_key == "your_gemini_api_key_here":
            key_name = "OPENAI_API_KEY" if provider == "openai" else "GEMINI_API_KEY"
            logger.warning("Chat request rejected: '%s' is not configured.", key_name)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    f"LLM Chat is not configured. Please set the '{key_name}' "
                    f"environment variable in the backend to enable conversational AI."
                ),
            )

        if provider == "mock":
            return self._call_mock(request, model)
        elif provider == "openai":
            return self._call_openai(request, api_key, model)
        else:
            return self._call_gemini(request, api_key, model)

    def _call_gemini(
        self,
        request: ChatRequest,
        api_key: str,
        model: str,
    ) -> ChatResponse:
        """Execute chat completion via Google Gemini REST API."""
        base_url = os.getenv("GEMINI_BASE_URL") or self.GEMINI_API_URL
        endpoint = f"{base_url.rstrip('/')}/v1beta/models/{model}:generateContent"

        # Build contents from history + current turn
        contents: list[dict[str, Any]] = []

        # Map history turns ensuring alternating user/model roles
        for turn in request.history[-10:]:  # Keep up to last 10 turns for context
            role = "model" if turn.role.lower() in ("assistant", "model") else "user"
            content_text = turn.content.strip()
            if not content_text:
                continue

            # Prevent consecutive turns with same role in Gemini
            if contents and contents[-1]["role"] == role:
                contents[-1]["parts"][0]["text"] += f"\n\n{content_text}"
            else:
                contents.append({
                    "role": role,
                    "parts": [{"text": content_text}],
                })

        # Inject active inspection context into user message if present
        context_block = self._format_context_block(request.context)
        final_user_text = request.message.strip()
        if context_block:
            final_user_text = f"{context_block}\n\n[USER QUESTION]\n{final_user_text}"

        # If last turn in contents is 'user', append or start new
        if contents and contents[-1]["role"] == "user":
            contents[-1]["parts"][0]["text"] += f"\n\n{final_user_text}"
        else:
            contents.append({
                "role": "user",
                "parts": [{"text": final_user_text}],
            })

        request_body = {
            "systemInstruction": {
                "parts": [{"text": SYSTEM_PROMPT}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 2048,
            },
        }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        }

        timeout = self._get_timeout()
        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(endpoint, json=request_body, headers=headers)
        except httpx.TimeoutException as exc:
            logger.error("Gemini chat API request timed out after %.1fs", timeout)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Gemini API request timed out after {timeout}s. Please try again.",
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Gemini chat API network error: %s", str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Network error communicating with Gemini API: {str(exc)}",
            ) from exc

        if res.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Gemini API rate limit reached. Please wait a few moments before trying again.",
            )
        if res.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Authentication with Gemini API failed. Please verify your GEMINI_API_KEY.",
            )
        if res.status_code != 200:
            error_text = res.text[:300]
            logger.error("Gemini API error (HTTP %d): %s", res.status_code, error_text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Gemini API error (HTTP {res.status_code}): {error_text}",
            )

        try:
            data = res.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No candidates returned in Gemini response.")

            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts or "text" not in parts[0]:
                raise ValueError("No text content part in Gemini candidate.")

            reply_text = parts[0]["text"].strip()
            return ChatResponse(
                message=reply_text,
                provider="gemini",
                model=model,
            )
        except Exception as exc:
            logger.error("Failed to parse Gemini response payload: %s", str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to parse Gemini response: {str(exc)}",
            ) from exc

    def _call_openai(
        self,
        request: ChatRequest,
        api_key: str,
        model: str,
    ) -> ChatResponse:
        """Execute chat completion via OpenAI REST API."""
        base_url = os.getenv("OPENAI_BASE_URL") or self.OPENAI_API_URL
        endpoint = f"{base_url.rstrip('/')}/v1/chat/completions"

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

        for turn in request.history[-10:]:
            role = "assistant" if turn.role.lower() in ("assistant", "model") else "user"
            content = turn.content.strip()
            if content:
                messages.append({"role": role, "content": content})

        context_block = self._format_context_block(request.context)
        final_user_text = request.message.strip()
        if context_block:
            final_user_text = f"{context_block}\n\n[USER QUESTION]\n{final_user_text}"

        messages.append({"role": "user", "content": final_user_text})

        request_body = {
            "model": model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 2048,
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

        timeout = self._get_timeout()
        try:
            with httpx.Client(timeout=timeout) as client:
                res = client.post(endpoint, json=request_body, headers=headers)
        except httpx.TimeoutException as exc:
            logger.error("OpenAI chat API request timed out after %.1fs", timeout)
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"OpenAI API request timed out after {timeout}s. Please try again.",
            ) from exc
        except httpx.RequestError as exc:
            logger.error("OpenAI chat API network error: %s", str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Network error communicating with OpenAI API: {str(exc)}",
            ) from exc

        if res.status_code == 429:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="OpenAI API rate limit reached. Please wait a few moments before trying again.",
            )
        if res.status_code in (401, 403):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Authentication with OpenAI API failed. Please verify your OPENAI_API_KEY.",
            )
        if res.status_code != 200:
            error_text = res.text[:300]
            logger.error("OpenAI API error (HTTP %d): %s", res.status_code, error_text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"OpenAI API error (HTTP {res.status_code}): {error_text}",
            )

        try:
            data = res.json()
            choices = data.get("choices", [])
            if not choices:
                raise ValueError("No choices returned in OpenAI response.")

            reply_text = choices[0].get("message", {}).get("content", "").strip()
            return ChatResponse(
                message=reply_text,
                provider="openai",
                model=model,
            )
        except Exception as exc:
            logger.error("Failed to parse OpenAI response: %s", str(exc))
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to parse OpenAI response: {str(exc)}",
            ) from exc

    def _call_mock(self, request: ChatRequest, model: str) -> ChatResponse:
        """Deterministic mock provider for unit testing without external network calls."""
        ctx_info = ""
        if request.context:
            if request.context.run_id:
                ctx_info += f" for run {request.context.run_id}"
            if request.context.finding and request.context.finding.finding_id:
                ctx_info += f", finding #{request.context.finding.finding_id}"

        reply = (
            f"OmniSight Mock Assistant: I received your question '{request.message}'{ctx_info}. "
            f"The architecture uses Playwright browser capture and Vision-Language models to inspect and heal UI regressions."
        )
        return ChatResponse(
            message=reply,
            provider="mock",
            model=model,
        )


chat_service = ChatService()
