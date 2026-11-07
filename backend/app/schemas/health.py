"""Health check schemas for the OmniSight Backend API."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response schema for the API health check."""

    status: str = Field(
        default="ok",
        description="Status of the backend API service",
    )
    app: str = Field(
        default="OmniSight Backend",
        description="Application name",
    )
    version: str = Field(
        default="0.1.0",
        description="API semantic version",
    )
