"""Data schemas for OmniSight visual and DOM inspection artifacts."""

from typing import Literal
from pydantic import BaseModel, Field


class ArtifactResponse(BaseModel):
    """Metadata response representing a captured visual, DOM, or telemetry artifact."""

    artifact_id: str = Field(
        ...,
        description="Unique identifier for the artifact",
        examples=["art_run_1234_screenshot"],
    )
    run_id: str = Field(
        ...,
        description="Identifier of the associated inspection run",
        examples=["run_1234abcd"],
    )
    artifact_type: Literal["screenshot", "dom_snapshot", "har_log", "other"] | str = Field(
        ...,
        description="Type of evidence artifact",
        examples=["screenshot", "dom_snapshot"],
    )
    storage_path: str = Field(
        ...,
        description="Relative or accessible filesystem storage path of the artifact",
        examples=["artifacts/run_1234abcd/before.png"],
    )
    file_size_bytes: int | None = Field(
        default=None,
        description="Size of the artifact file in bytes on disk",
        examples=[1048576],
    )
    content_type: str | None = Field(
        default=None,
        description="MIME media type of the artifact",
        examples=["image/png", "text/html"],
    )
    captured_at: str = Field(
        ...,
        description="ISO-8601 UTC timestamp when the artifact was captured",
    )
    download_url: str = Field(
        ...,
        description="HTTP URL endpoint to stream or download this artifact",
        examples=["/api/v1/artifacts/run_1234abcd/before.png"],
    )
