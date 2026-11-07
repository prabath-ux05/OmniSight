"""Error response schemas for OmniSight API."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standardized error response payload."""

    detail: str = Field(
        ...,
        description="Detailed explanation of the error",
        examples=["Run 'run_unknown_999' not found."],
    )
