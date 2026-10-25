from urllib.parse import unquote
from fastapi import APIRouter, HTTPException, status
from backend.app.core.logging import logger
from backend.app.schemas.errors import ErrorResponse
from backend.app.schemas.findings import FindingResponse
from backend.app.schemas.runs import RunCreateRequest, RunResponse
from backend.app.services.run_store import run_store

router = APIRouter(prefix="/api/v1", tags=["Runs"])


def _validate_run_id(run_id: str) -> str:
    """Validate run_id format and reject empty or whitespace identifiers."""
    cleaned = unquote(run_id).strip() if run_id else ""
    if not cleaned:
        logger.warning("Rejected invalid empty or whitespace run_id: %r", run_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid run_id: identifier must not be empty or whitespace.",
        )
    return cleaned




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
    responses={
        201: {"model": RunResponse, "description": "Run created and queued successfully"},
        422: {"description": "Request payload validation error (e.g. missing or malformed URL)"},
    },
)
def create_run(payload: RunCreateRequest) -> RunResponse:
    """Validate request and create a new inspection run in 'queued' status."""
    logger.info("Received run creation request for URL: %s", payload.url)
    run = run_store.create(payload)
    logger.info("Run created successfully with ID: %s (status=%s)", run.run_id, run.status)
    return run


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    status_code=status.HTTP_200_OK,
    summary="Get run status and metadata",
    description=(
        "Retrieves the current status and relevant metadata for an existing inspection run. "
        "Returns 404 if the run_id does not exist."
    ),
    responses={
        200: {"model": RunResponse, "description": "Run details retrieved successfully"},
        400: {"model": ErrorResponse, "description": "Invalid run_id format"},
        404: {"model": ErrorResponse, "description": "Run not found"},
    },
)
def get_run(run_id: str) -> RunResponse:
    """Retrieve run status and metadata by run_id."""
    clean_id = _validate_run_id(run_id)
    run = run_store.get(clean_id)
    if not run:
        logger.warning("Run lookup failed: run_id '%s' not found.", clean_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_id}' not found.",
        )
    return run


@router.get(
    "/runs/{run_id}/findings",
    response_model=list[FindingResponse],
    status_code=status.HTTP_200_OK,
    summary="Get findings for an inspection run",
    description=(
        "Retrieves structured UI defect findings for an existing inspection run. "
        "Returns an empty list if no defects were detected. "
        "Returns 404 if the run_id does not exist."
    ),
    responses={
        200: {"description": "List of findings (empty array if no defects detected)"},
        400: {"model": ErrorResponse, "description": "Invalid run_id format"},
        404: {"model": ErrorResponse, "description": "Run not found"},
    },
)
def get_run_findings(run_id: str, include_mock: bool = False) -> list[FindingResponse]:
    """Retrieve structured defect findings by run_id."""
    clean_id = _validate_run_id(run_id)
    findings = run_store.get_findings(clean_id)
    if findings is None:
        logger.warning("Findings lookup failed: run_id '%s' not found.", clean_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_id}' not found.",
        )
    if include_mock and not findings:
        from backend.app.services.run_store import create_mock_findings
        return create_mock_findings(clean_id)
    return findings


