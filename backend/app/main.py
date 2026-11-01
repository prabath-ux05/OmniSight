"""OmniSight Backend Application Entry Point.

This module provides the central FastAPI application instance for OmniSight.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.api.artifacts import router as artifacts_router
from backend.app.api.health import router as health_router
from backend.app.api.runs import router as runs_router
from backend.app.core.logging import logger
from backend.app.db.session import check_db_connection, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler managing startup initialization and shutdown cleanup."""
    logger.info("OmniSight Backend starting up: initializing database connection...")
    try:
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
