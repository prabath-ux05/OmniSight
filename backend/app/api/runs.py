"""API routing for OmniSight inspection runs."""

from fastapi import APIRouter, status
from backend.app.schemas.runs import RunCreateRequest, RunResponse
from backend.app.services.run_store import run_store

router = APIRouter(prefix="/api/v1", tags=["Runs"])


@router.post(
    "/runs",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an inspection run",
    description=(
        "Validates the incoming run configuration, generates a unique run_id, "
        "and registers the run in the initial 'queued' status. "
        "Does not claim that browser execution or vision inspection has started."
    ),
)
def create_run(payload: RunCreateRequest) -> RunResponse:
    """Validate request and create a new inspection run in 'queued' status."""
    return run_store.create(payload)
