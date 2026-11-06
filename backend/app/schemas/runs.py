"""Data schemas for OmniSight inspection runs."""

import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator


def mask_sensitive_strings(text: str) -> str:
    """Mask credentials, tokens, or sensitive parameters in error/diagnostic strings."""
    if not text:
        return text
    masked = re.sub(
        r'((?:api[_-]?key|token|secret|password|access[_-]?token)\s*[:=]\s*["\']?)([^"\'\s&]+)(["\']?)',
        r"\1***MASKED***\3",
        text,
        flags=re.IGNORECASE,
    )
    masked = re.sub(
        r'(bearer\s+)([A-Za-z0-9_\-\.]{8,})',
        r"\1***MASKED***",
        masked,
        flags=re.IGNORECASE,
    )
    return masked


class RunCreateRequest(BaseModel):
    """Request payload to create a new OmniSight inspection run."""

    model_config = ConfigDict(str_strip_whitespace=True)

    url: HttpUrl = Field(
        ...,
        max_length=2048,
        description="Target web page URL to inspect",
        examples=["http://127.0.0.1:8000/"],
    )



class RunResponse(BaseModel):
    """Response payload representing an inspection run."""

    run_id: str = Field(
        ...,
        description="Unique identifier for the run",
        examples=["run_a1b2c3d4"],
    )
    url: str = Field(
        ...,
        description="Target web page URL being inspected",
        examples=["http://127.0.0.1:8000/"],
    )
    status: Literal[
        "queued",
        "capturing",
        "analyzing",
        "repair_pending",
        "repairing",
        "verifying",
        "completed",
        "failed",
        "cancelled",
    ] = Field(
        default="queued",
        description="Current lifecycle state of the run",
    )
    created_at: str = Field(
        ...,
        description="ISO-8601 UTC timestamp of run creation",
    )
    message: str = Field(
        default="Run created successfully and queued for inspection.",
        description="Descriptive status message",
    )
    error: str | None = Field(
        default=None,
        description="Error message if run failed or encountered an issue",
    )

    @model_validator(mode="after")
    def validate_failed_run_and_mask_secrets(self) -> "RunResponse":
        """Ensure failed runs always have non-empty error and message, and mask secrets."""
        if self.error:
            self.error = mask_sensitive_strings(self.error)
        if self.message:
            self.message = mask_sensitive_strings(self.message)

        if self.status == "failed":
            if not self.error or not self.error.strip():
                self.error = (
                    self.message.strip()
                    if (self.message and self.message.strip())
                    else "Inspection run failed."
                )
            if not self.message or not self.message.strip():
                self.message = self.error
        elif self.error is not None and not self.error.strip():
            self.error = None

        return self
