"""OmniSight Backend Application Entry Point.

This module provides the central FastAPI application instance for OmniSight.
"""

import sys
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# On Windows, ensure ProactorEventLoop is used so subprocesses (Playwright) function correctly under Uvicorn
if sys.platform == "win32":
    if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from backend.app.api.artifacts import router as artifacts_router
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

# Allow CORS for development frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(runs_router)
app.include_router(artifacts_router)

