"""OmniSight Backend Application Entry Point.

This module provides the central FastAPI application instance for OmniSight.
"""

import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# On Windows, ensure ProactorEventLoop is used so subprocesses (Playwright) function correctly under Uvicorn
if sys.platform == "win32":
    if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from backend.app.api.artifacts import router as artifacts_router
from backend.app.api.auth import router as auth_router
from backend.app.api.health import router as health_router
from backend.app.api.preview import router as preview_router
from backend.app.api.proposals import router as proposals_router
from backend.app.api.runs import router as runs_router

try:
    from backend.app.api.chat import router as chat_router
except ImportError:
    chat_router = None
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.session import check_db_connection, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler managing startup initialization and shutdown cleanup."""
    logger.info("OmniSight Backend starting up: verifying database connection...")
    try:
        # In development/test environments, auto-create tables; in production, schema is managed via Alembic
        if settings.APP_ENV in ("development", "test"):
            init_db()

        if check_db_connection():
            logger.info("Database connection successfully established and verified.")
        else:
            logger.warning("Database connection ping failed on startup. Please verify DATABASE_URL and service status.")
    except Exception as exc:
        logger.error("Database initialization error during startup: %s", str(exc))
    yield
    logger.info("OmniSight Backend shutting down.")


app = FastAPI(
    title="OmniSight Backend API",
    description=(
        "Core orchestration and telemetry API for OmniSight: "
        "Multimodal UI Self-Healing & RPA Agent."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# Allow CORS for trusted origins with credentials
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health_router)
app.include_router(auth_router)
if chat_router is not None:
    app.include_router(chat_router)
app.include_router(runs_router)
app.include_router(preview_router)
app.include_router(artifacts_router)
app.include_router(proposals_router)
