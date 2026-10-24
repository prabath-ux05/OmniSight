from fastapi import APIRouter
from backend.app.core.logging import logger
from backend.app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Backend Health Check",
    description=(
        "Returns backend API service health confirmation. "
        "Does not claim that the browser agent or vision engine are operational."
    ),
)
def get_health() -> HealthResponse:
    """Return a simple confirmation that the backend API is running."""
    logger.debug("Health check requested.")
    return HealthResponse(
        status="ok",
        app="OmniSight Backend",
        version="0.1.0",
    )

