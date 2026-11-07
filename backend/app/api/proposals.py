"""API endpoints managing self-healing repair proposals and review lifecycles."""

from urllib.parse import unquote
from fastapi import APIRouter, HTTPException, status
from backend.app.core.logging import logger
from backend.app.db.session import DatabaseConnectionError
from backend.app.schemas.errors import ErrorResponse
from backend.app.schemas.proposals import (
    ProposalDecisionRequest,
    ProposalStatusResponse,
    RepairProposalCreateRequest,
    RepairProposalResponse,
)
from backend.app.services.run_store import ProposalConflictError, run_store

router = APIRouter(prefix="/api/v1", tags=["Repair Proposals"])


def _validate_identifier(identifier: str, name: str = "identifier") -> str:
    """Validate identifier format and reject empty, whitespace, or oversized strings."""
    cleaned = unquote(identifier).strip() if identifier else ""
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {name}: must not be empty or whitespace.",
        )
    if len(cleaned) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {name}: identifier exceeds maximum allowed length of 128 characters.",
        )
    return cleaned


@router.post(
    "/runs/{run_id}/proposals",
    response_model=RepairProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a repair proposal for an inspection run",
    description=(
        "Registers a new self-healing repair proposal associated with an inspection run and defect finding. "
        "Initializes the review status to 'pending'."
    ),
    responses={
        201: {"model": RepairProposalResponse, "description": "Proposal created successfully"},
        400: {"model": ErrorResponse, "description": "Invalid run_id format or invalid payload"},
        404: {"model": ErrorResponse, "description": "Run not found"},
        503: {"model": ErrorResponse, "description": "Database connection unavailable"},
    },
)
def create_repair_proposal(
    run_id: str,
    payload: RepairProposalCreateRequest,
) -> RepairProposalResponse:
    """Create a new repair proposal for an existing inspection run."""
    clean_run_id = _validate_identifier(run_id, "run_id")
    try:
        proposal = run_store.create_proposal(clean_run_id, payload)
        return proposal
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        ) from val_err
    except DatabaseConnectionError as exc:
        logger.error("Failed to persist proposal in database: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please check database connection.",
        ) from exc


@router.get(
    "/runs/{run_id}/proposals",
    response_model=list[RepairProposalResponse],
    status_code=status.HTTP_200_OK,
    summary="List repair proposals for an inspection run",
    description=(
        "Retrieves all repair proposals created for a given inspection run, "
        "optionally filtered by a specific finding ID."
    ),
    responses={
        200: {"description": "List of repair proposals"},
        400: {"model": ErrorResponse, "description": "Invalid run_id format"},
        404: {"model": ErrorResponse, "description": "Run not found"},
        503: {"model": ErrorResponse, "description": "Database connection unavailable"},
    },
)
def list_run_proposals(
    run_id: str,
    finding_id: str | None = None,
) -> list[RepairProposalResponse]:
    """Retrieve all repair proposals for a run."""
    clean_run_id = _validate_identifier(run_id, "run_id")
    try:
        proposals = run_store.list_proposals(clean_run_id, finding_id=finding_id)
    except DatabaseConnectionError as exc:
        logger.error("Failed to query proposals from database: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please check database connection.",
        ) from exc

    if proposals is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_run_id}' not found.",
        )
    return proposals


@router.get(
    "/proposals/{proposal_id}",
    response_model=RepairProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a repair proposal by ID",
    description="Fetches full details and current lifecycle status for a specific repair proposal.",
    responses={
        200: {"model": RepairProposalResponse, "description": "Proposal details retrieved"},
        400: {"model": ErrorResponse, "description": "Invalid proposal_id format"},
        404: {"model": ErrorResponse, "description": "Proposal not found"},
        503: {"model": ErrorResponse, "description": "Database connection unavailable"},
    },
)
def get_repair_proposal(proposal_id: str) -> RepairProposalResponse:
    """Retrieve a repair proposal by proposal_id."""
    clean_prop_id = _validate_identifier(proposal_id, "proposal_id")
    try:
        proposal = run_store.get_proposal(clean_prop_id)
    except DatabaseConnectionError as exc:
        logger.error("Failed to query proposal from database: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please check database connection.",
        ) from exc

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{clean_prop_id}' not found.",
        )
    return proposal


@router.post(
    "/proposals/{proposal_id}/approve",
    response_model=RepairProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a repair proposal",
    description=(
        "Records an approval decision for a pending repair proposal. "
        "Guards against duplicate approvals and conflicting state transitions. "
        "Does NOT automatically apply or verify the patch."
    ),
    responses={
        200: {"model": RepairProposalResponse, "description": "Proposal successfully approved"},
        400: {"model": ErrorResponse, "description": "Invalid proposal_id format"},
        404: {"model": ErrorResponse, "description": "Proposal not found"},
        409: {"model": ErrorResponse, "description": "Proposal already decided or in conflicting state"},
        503: {"model": ErrorResponse, "description": "Database connection unavailable"},
    },
)
def approve_repair_proposal(
    proposal_id: str,
    payload: ProposalDecisionRequest = None,
) -> RepairProposalResponse:
    """Approve a repair proposal."""
    clean_prop_id = _validate_identifier(proposal_id, "proposal_id")
    notes = payload.notes if payload else None

    try:
        updated = run_store.update_proposal_approval(clean_prop_id, "approved", notes=notes)
    except ProposalConflictError as conf_err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(conf_err),
        ) from conf_err
    except DatabaseConnectionError as exc:
        logger.error("Failed to update proposal approval: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please check database connection.",
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{clean_prop_id}' not found.",
        )
    return updated


@router.post(
    "/proposals/{proposal_id}/reject",
    response_model=RepairProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a repair proposal",
    description=(
        "Records a rejection decision for a pending repair proposal. "
        "Guards against duplicate rejections and conflicting state transitions."
    ),
    responses={
        200: {"model": RepairProposalResponse, "description": "Proposal successfully rejected"},
        400: {"model": ErrorResponse, "description": "Invalid proposal_id format"},
        404: {"model": ErrorResponse, "description": "Proposal not found"},
        409: {"model": ErrorResponse, "description": "Proposal already decided or in conflicting state"},
        503: {"model": ErrorResponse, "description": "Database connection unavailable"},
    },
)
def reject_repair_proposal(
    proposal_id: str,
    payload: ProposalDecisionRequest = None,
) -> RepairProposalResponse:
    """Reject a repair proposal."""
    clean_prop_id = _validate_identifier(proposal_id, "proposal_id")
    notes = payload.notes if payload else None

    try:
        updated = run_store.update_proposal_approval(clean_prop_id, "rejected", notes=notes)
    except ProposalConflictError as conf_err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(conf_err),
        ) from conf_err
    except DatabaseConnectionError as exc:
        logger.error("Failed to update proposal rejection: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please check database connection.",
        ) from exc

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{clean_prop_id}' not found.",
        )
    return updated


@router.get(
    "/proposals/{proposal_id}/status",
    response_model=ProposalStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get proposal lifecycle and approval status",
    description="Returns a lightweight status summary of approval, execution, and verification states.",
    responses={
        200: {"model": ProposalStatusResponse, "description": "Proposal status retrieved"},
        400: {"model": ErrorResponse, "description": "Invalid proposal_id format"},
        404: {"model": ErrorResponse, "description": "Proposal not found"},
        503: {"model": ErrorResponse, "description": "Database connection unavailable"},
    },
)
def get_proposal_status(proposal_id: str) -> ProposalStatusResponse:
    """Retrieve the current approval and execution status of a repair proposal."""
    clean_prop_id = _validate_identifier(proposal_id, "proposal_id")
    try:
        proposal = run_store.get_proposal(clean_prop_id)
    except DatabaseConnectionError as exc:
        logger.error("Failed to query proposal status: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please check database connection.",
        ) from exc

    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{clean_prop_id}' not found.",
        )

    return ProposalStatusResponse(
        proposal_id=proposal.proposal_id,
        run_id=proposal.run_id,
        approval_status=proposal.approval_status,
        execution_status=proposal.execution_status,
        verification_status=proposal.verification_status,
        github_pr_url=proposal.github_pr_url,
        updated_at=proposal.updated_at,
    )
