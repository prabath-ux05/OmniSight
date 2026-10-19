"""OmniSight Backend Application Entry Point.

This module provides the central FastAPI application instance for OmniSight.
"""

from fastapi import FastAPI
from backend.app.api.health import router as health_router
from backend.app.api.runs import router as runs_router

app = FastAPI(
    title="OmniSight Backend API",
    description=(
        "Core orchestration and telemetry API for OmniSight: "
        "Multimodal UI Self-Healing & RPA Agent."
    ),
    version="0.1.0",
)

# Register routers
app.include_router(health_router)
app.include_router(runs_router)
