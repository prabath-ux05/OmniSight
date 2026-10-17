"""Data schemas for OmniSight inspection runs."""

from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class RunCreateRequest(BaseModel):
    """Request payload to create a new OmniSight inspection run."""

    url: HttpUrl = Field(
        ...,
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
