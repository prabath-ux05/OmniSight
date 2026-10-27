"""Configurable Vision-Language Model providers for multimodal UI defect detection."""

from __future__ import annotations

import base64
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import httpx

from vision_engine.prompting.defect_prompts import (
    VLM_SYSTEM_PROMPT,
    build_vlm_user_prompt,
    parse_vlm_json_response,
)


class VLMError(Exception):
    """Base exception for Vision-Language Model detection errors."""


class VLMConfigurationError(VLMError):
    """Raised when VLM provider configuration or credentials are missing or invalid."""


class VLMProviderError(VLMError):
    """Raised when a VLM provider fails with an API or network error."""


class VLMTimeoutError(VLMProviderError):
    """Raised when an API request to a VLM provider times out."""


class VLMResponseError(VLMError):
    """Raised when a VLM provider returns an unparseable or invalid response."""


@dataclass
class VLMConfig:
    """Configuration for Vision-Language Model execution."""

    provider: str = "gemini"
    api_key: str | None = None
    model: str = "gemini-1.5-flash"
    timeout_seconds: float = 30.0
    max_dom_chars: int = 15000
    base_url: str | None = None
    temperature: float = 0.1
    extra_headers: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls) -> VLMConfig:
        """Construct configuration from environment variables."""
        provider = (
            os.getenv("VISION_MODEL_PROVIDER")
            or os.getenv("VLM_PROVIDER")
            or "gemini"
        ).strip().lower()

        try:
            timeout = float(os.getenv("VISION_TIMEOUT_SECONDS", "30.0"))
        except ValueError:
            timeout = 30.0

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            model = os.getenv("OPENAI_MODEL", "gpt-4o").strip()
            base_url = os.getenv("OPENAI_BASE_URL")
        elif provider == "mock":
            api_key = "mock-key"
            model = "mock-detector"
            base_url = None
        else:
            # Default to gemini
            provider = "gemini"
            api_key = os.getenv("GEMINI_API_KEY")
            model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()
            base_url = os.getenv("GEMINI_BASE_URL")

        return cls(
            provider=provider,
            api_key=api_key.strip() if api_key else None,
            model=model,
            timeout_seconds=timeout,
            base_url=base_url.strip() if base_url else None,
        )



class BaseVLMProvider(ABC):
    """Abstract interface for vision-language model providers."""

    def __init__(self, config: VLMConfig) -> None:
        self.config = config
        self._validate_credentials()

    def _validate_credentials(self) -> None:
        """Ensure provider has required credentials."""
        if not self.config.api_key or not self.config.api_key.strip():
            env_var = "GEMINI_API_KEY" if self.config.provider == "gemini" else "OPENAI_API_KEY"
            raise VLMConfigurationError(
                f"Missing API key for provider '{self.config.provider}'. "
                f"Please set the '{env_var}' environment variable."
            )

    @abstractmethod
    def analyze_ui(
        self,
        screenshot_bytes: bytes | None,
        dom_text: str | None,
        url: str,
    ) -> dict[str, Any]:
        """Perform multimodal inspection and return parsed JSON result."""


class GeminiVLMProvider(BaseVLMProvider):
    """Google Gemini vision-language provider via REST API."""

    DEFAULT_BASE_URL = "https://generativelanguage.googleapis.com"

    def analyze_ui(
        self,
        screenshot_bytes: bytes | None,
        dom_text: str | None,
        url: str,
    ) -> dict[str, Any]:
        base_url = self.config.base_url or self.DEFAULT_BASE_URL
        endpoint = f"{base_url.rstrip('/')}/v1beta/models/{self.config.model}:generateContent"

        user_prompt = build_vlm_user_prompt(
            url=url,
            dom_html=dom_text,
            max_dom_chars=self.config.max_dom_chars,
        )

        parts: list[dict[str, Any]] = [{"text": user_prompt}]

        if screenshot_bytes:
            encoded_image = base64.b64encode(screenshot_bytes).decode("utf-8")
            parts.append({
                "inlineData": {
                    "mimeType": "image/png",
                    "data": encoded_image,
                }
            })

        request_body = {
            "systemInstruction": {
                "parts": [{"text": VLM_SYSTEM_PROMPT}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": parts,
                }
            ],
            "generationConfig": {
                "temperature": self.config.temperature,
                "responseMimeType": "application/json",
            },
        }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.config.api_key,
        }
        headers.update(self.config.extra_headers)

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(endpoint, json=request_body, headers=headers)
        except httpx.TimeoutException as exc:
            raise VLMTimeoutError(
                f"Gemini API request timed out after {self.config.timeout_seconds}s"
            ) from exc
        except httpx.RequestError as exc:
            raise VLMProviderError(f"Gemini API network request failed: {exc}") from exc

        if response.status_code != 200:
            raise VLMProviderError(
                f"Gemini API returned HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            data = response.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise VLMResponseError("Gemini API returned no candidates in response.")

            content = candidates[0].get("content", {})
            parts_resp = content.get("parts", [])
            if not parts_resp or "text" not in parts_resp[0]:
                raise VLMResponseError("Gemini API candidate has no text part.")

            raw_text = parts_resp[0]["text"]
            return parse_vlm_json_response(raw_text)
        except (KeyError, IndexError, TypeError) as exc:
            raise VLMResponseError(f"Malformed Gemini API response payload: {exc}") from exc
        except ValueError as exc:
            raise VLMResponseError(str(exc)) from exc


class OpenAIVLMProvider(BaseVLMProvider):
    """OpenAI GPT-4o vision-language provider via REST API."""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"

    def analyze_ui(
        self,
        screenshot_bytes: bytes | None,
        dom_text: str | None,
        url: str,
    ) -> dict[str, Any]:
        base_url = self.config.base_url or self.DEFAULT_BASE_URL
        endpoint = f"{base_url.rstrip('/')}/chat/completions"

        user_prompt = build_vlm_user_prompt(
            url=url,
            dom_html=dom_text,
            max_dom_chars=self.config.max_dom_chars,
        )

        user_content: list[dict[str, Any]] = [
            {"type": "text", "text": user_prompt}
        ]

        if screenshot_bytes:
            encoded_image = base64.b64encode(screenshot_bytes).decode("utf-8")
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{encoded_image}",
                    "detail": "high",
                },
            })

        request_body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": VLM_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        headers.update(self.config.extra_headers)

        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                response = client.post(endpoint, json=request_body, headers=headers)
        except httpx.TimeoutException as exc:
            raise VLMTimeoutError(
                f"OpenAI API request timed out after {self.config.timeout_seconds}s"
            ) from exc
        except httpx.RequestError as exc:
            raise VLMProviderError(f"OpenAI API network request failed: {exc}") from exc

        if response.status_code != 200:
            raise VLMProviderError(
                f"OpenAI API returned HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                raise VLMResponseError("OpenAI API returned no choices in response.")

            raw_text = choices[0].get("message", {}).get("content", "")
            return parse_vlm_json_response(raw_text)
        except (KeyError, IndexError, TypeError) as exc:
            raise VLMResponseError(f"Malformed OpenAI API response payload: {exc}") from exc
        except ValueError as exc:
            raise VLMResponseError(str(exc)) from exc


def create_vlm_provider(config: VLMConfig | None = None) -> BaseVLMProvider:
    """Factory creating an authenticated VLM provider instance.

    Raises:
        VLMConfigurationError: If API credentials for the chosen provider are missing.
    """
    cfg = config or VLMConfig.from_env()

    if cfg.provider == "openai":
        return OpenAIVLMProvider(cfg)
    elif cfg.provider == "gemini":
        return GeminiVLMProvider(cfg)
    else:
        raise VLMConfigurationError(
            f"Unsupported VLM provider '{cfg.provider}'. Supported providers: 'gemini', 'openai'."
        )


def check_vlm_configuration(provider_name: str | None = None) -> dict[str, Any]:
    """Inspect and report VLM configuration status without exposing credentials."""
    target_provider = (
        provider_name
        or os.getenv("VISION_MODEL_PROVIDER")
        or os.getenv("VLM_PROVIDER")
        or "gemini"
    ).strip().lower()

    if target_provider == "mock":
        return {
            "provider": "mock",
            "model": "mock-detector",
            "configured": True,
            "is_configured": True,
            "status": "ready",
            "api_key_status": "not_required",
            "timeout_seconds": 0.0,
            "message": "Mock provider active for deterministic testing. Mock findings are strictly labeled as mock.",
            "actionable_message": "Mock provider active for deterministic testing. Mock findings are strictly labeled as mock.",
        }

    cfg = VLMConfig.from_env()
    if target_provider in ("gemini", "openai"):
        cfg.provider = target_provider
        if target_provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            cfg.api_key = api_key.strip() if api_key else None
            cfg.model = os.getenv("OPENAI_MODEL", "gpt-4o").strip()
        elif target_provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            cfg.api_key = api_key.strip() if api_key else None
            cfg.model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

    key_present = bool(cfg.api_key and cfg.api_key.strip())
    masked_key = (
        f"...{cfg.api_key[-4:]}"
        if (key_present and len(cfg.api_key or "") >= 4)
        else ("configured" if key_present else "missing")
    )

    if key_present:
        status = "ready"
        message = (
            f"VLM provider '{cfg.provider}' configured with model '{cfg.model}'. "
            f"Ready for multimodal inspection (timeout: {cfg.timeout_seconds}s)."
        )
    else:
        status = "unconfigured"
        env_var = "GEMINI_API_KEY" if cfg.provider == "gemini" else "OPENAI_API_KEY"
        message = (
            f"API key for VLM provider '{cfg.provider}' is missing. "
            f"Set the '{env_var}' environment variable to enable live vision inference. "
            f"Deterministic fallback detector is active."
        )

    return {
        "provider": cfg.provider,
        "model": cfg.model,
        "configured": key_present,
        "is_configured": key_present,
        "status": status,
        "api_key_status": masked_key,
        "timeout_seconds": cfg.timeout_seconds,
        "message": message,
        "actionable_message": message,
    }
