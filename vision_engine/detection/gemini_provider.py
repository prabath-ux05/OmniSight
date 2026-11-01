
"""Gemini-backed Vision-Language Model detector for OmniSight."""

import base64
import mimetypes
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from google import genai

from vision_engine.detection.vlm_response_parser import parse_vlm_response
from vision_engine.models import VisionFinding, VisionInput
from vision_engine.prompting.vlm_prompt import build_vlm_prompt


class GeminiVLMDetector:
    """Analyze screenshot and DOM evidence using Google's Gemini API."""

    MAX_ATTEMPTS = 3
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gemini-3.8-flash",
        timeout_seconds: float = 30.0,
        client: Any | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")

        load_dotenv()

        resolved_key = api_key or os.getenv("GEMINI_API_KEY")

        if client is None and not resolved_key:
            raise ValueError(
                "GEMINI_API_KEY is missing. Add it to your root .env file."
            )

        self.model = model
        self.timeout_seconds = timeout_seconds
        self.client = (
            client
            if client is not None
            else genai.Client(
                api_key=resolved_key,
                http_options={
                    "timeout": int(timeout_seconds * 1000)
                },
            )
        )

    @staticmethod
    def _read_screenshot(path: str) -> dict:
        """Read screenshot bytes and prepare an image input for Gemini."""
        screenshot = Path(path)

        if not screenshot.is_file():
            raise ValueError(f"Screenshot file does not exist: {path}")

        mime_type, _ = mimetypes.guess_type(screenshot.name)

        if mime_type not in {"image/png", "image/jpeg", "image/webp"}:
            raise ValueError(
                "Screenshot must be a PNG, JPEG, or WebP image."
            )

        image_data = screenshot.read_bytes()

        if not image_data:
            raise ValueError("Screenshot file is empty.")

        return {
            "type": "image",
            "data": base64.b64encode(image_data).decode("ascii"),
            "mime_type": mime_type,
        }

    @staticmethod
    def _read_dom(path: str) -> str:
        """Read DOM snapshot text without sending only its file path."""
        dom_file = Path(path)

        if not dom_file.is_file():
            raise ValueError(f"DOM snapshot file does not exist: {path}")

        dom_text = dom_file.read_text(encoding="utf-8")

        if not dom_text.strip():
            raise ValueError("DOM snapshot file is empty.")

        return dom_text[:100_000]

    @staticmethod
    def _get_status_code(exc: Exception) -> int | None:
        """Extract an HTTP status code from a Gemini SDK exception."""
        code = getattr(exc, "code", None)

        if code is None:
            response = getattr(exc, "response", None)
            code = getattr(response, "status_code", None)

        try:
            return int(code) if code is not None else None
        except (TypeError, ValueError):
            return None

    def detect(self, input_data: VisionInput) -> list[VisionFinding]:
        """Analyze supplied evidence and return validated VLM findings."""
        prompt = build_vlm_prompt(input_data)

        request_input = [
            {"type": "text", "text": prompt},
        ]

        if input_data.screenshot_path:
            request_input.append(
                self._read_screenshot(input_data.screenshot_path)
            )

        if input_data.dom_snapshot_path:
            dom_text = self._read_dom(input_data.dom_snapshot_path)
            request_input.append(
                {
                    "type": "text",
                    "text": "DOM snapshot contents:\n" + dom_text,
                }
            )

        interaction = None

        for attempt in range(self.MAX_ATTEMPTS):
            try:
                interaction = self.client.interactions.create(
                    model=self.model,
                    input=request_input,
                )
                break

            except Exception as exc:
                status_code = self._get_status_code(exc)

                should_retry = (
                    status_code in self.RETRYABLE_STATUS_CODES
                    and attempt < self.MAX_ATTEMPTS - 1
                )

                if should_retry:
                    delay = 2 ** attempt
                    time.sleep(delay)
                    continue

                if status_code is not None:
                    message = (
                        f"Gemini analysis failed with HTTP {status_code} "
                        f"after {attempt + 1} attempt(s)."
                    )
                else:
                    message = (
                        "Gemini analysis request failed: "
                        f"{type(exc).__name__}"
                    )

                raise RuntimeError(message) from exc

        response_text = getattr(interaction, "output_text", None)

        if not isinstance(response_text, str) or not response_text.strip():
            raise ValueError("Gemini returned an empty text response.")

        return parse_vlm_response(response_text)
