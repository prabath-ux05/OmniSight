"""API endpoints managing self-healing repair proposals and review lifecycles."""

from typing import Optional
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, status
from backend.app.api.deps import check_run_access, get_current_user_optional
from backend.app.core.logging import logger
from backend.app.db.session import DatabaseConnectionError
from backend.app.models.user import UserModel
from backend.app.schemas.errors import ErrorResponse
from backend.app.schemas.proposals import (
    ProposalDecisionRequest,
    ProposalStatusResponse,
    RepairProposalCreateRequest,
    RepairProposalResponse,
    SimulateRepairRequest,
    VisualComparisonResponse,
)
from backend.app.services.run_store import ProposalConflictError, run_store
from backend.app.services.visual_repair_simulator import visual_repair_simulator

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
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> RepairProposalResponse:
    """Create a new repair proposal for an existing inspection run."""
    clean_run_id = _validate_identifier(run_id, "run_id")
    run = run_store.get(clean_run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_run_id}' not found.",
        )
    check_run_access(run, current_user)
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
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> list[RepairProposalResponse]:
    """Retrieve all repair proposals for a run."""
    clean_run_id = _validate_identifier(run_id, "run_id")
    run = run_store.get(clean_run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_run_id}' not found.",
        )
    check_run_access(run, current_user)
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
def get_repair_proposal(
    proposal_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> RepairProposalResponse:
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
    run = run_store.get(proposal.run_id)
    if run:
        check_run_access(run, current_user)
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
    revisit: bool = False,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> RepairProposalResponse:
    """Approve a repair proposal. Supports revisiting an already approved proposal when revisit=True."""
    clean_prop_id = _validate_identifier(proposal_id, "proposal_id")
    notes = payload.notes if payload else None
    is_revisit = (payload.revisit if payload else False) or revisit

    proposal = run_store.get_proposal(clean_prop_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{clean_prop_id}' not found.",
        )
    run = run_store.get(proposal.run_id)
    if run:
        check_run_access(run, current_user)

    try:
        updated = run_store.update_proposal_approval(
            clean_prop_id, "approved", notes=notes, revisit=is_revisit
        )
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
        "Allows revisiting an approved proposal and revoking/rejecting it when revisit=True. "
        "Ensures rejected proposals strictly remain rejected."
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
    revisit: bool = False,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> RepairProposalResponse:
    """Reject a repair proposal. Supports revisiting an approved proposal when revisit=True."""
    clean_prop_id = _validate_identifier(proposal_id, "proposal_id")
    notes = payload.notes if payload else None
    is_revisit = (payload.revisit if payload else False) or revisit

    proposal = run_store.get_proposal(clean_prop_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repair proposal '{clean_prop_id}' not found.",
        )
    run = run_store.get(proposal.run_id)
    if run:
        check_run_access(run, current_user)

    try:
        updated = run_store.update_proposal_approval(
            clean_prop_id, "rejected", notes=notes, revisit=is_revisit
        )
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
def get_proposal_status(
    proposal_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> ProposalStatusResponse:
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
    run = run_store.get(proposal.run_id)
    if run:
        check_run_access(run, current_user)

    return ProposalStatusResponse(
        proposal_id=proposal.proposal_id,
        run_id=proposal.run_id,
        approval_status=proposal.approval_status,
        execution_status=proposal.execution_status,
        verification_status=proposal.verification_status,
        github_pr_url=proposal.github_pr_url,
        updated_at=proposal.updated_at,
    )


@router.get(
    "/runs/{run_id}/proposals/{proposal_id}/comparison",
    response_model=VisualComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Before/After visual comparison details for a proposal",
    description=(
        "Retrieves the original defect screenshot ('before') and proposed repaired screenshot ('after') "
        "along with linked finding evidence, proposal metadata, and governance decision status."
    ),
    responses={
        200: {"model": VisualComparisonResponse, "description": "Comparison details retrieved"},
        400: {"model": ErrorResponse, "description": "Invalid run_id or proposal_id"},
        404: {"model": ErrorResponse, "description": "Run or proposal not found"},
    },
)
def get_visual_comparison(
    run_id: str,
    proposal_id: str,
    viewport: str = "desktop",
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> VisualComparisonResponse:
    """Retrieve before/after visual comparison details for a run finding and repair proposal."""
    clean_run_id = _validate_identifier(run_id, "run_id")
    clean_prop_id = _validate_identifier(proposal_id, "proposal_id")

    run = run_store.get(clean_run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_run_id}' not found.",
        )
    check_run_access(run, current_user)

    try:
        comparison = visual_repair_simulator.get_comparison(
            clean_run_id, clean_prop_id, viewport=viewport
        )
        return comparison
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.error("Failed to fetch visual comparison: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate visual comparison: {str(exc)}",
        ) from exc


@router.get(
    "/proposals/{proposal_id}/comparison",
    response_model=VisualComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Before/After visual comparison by proposal ID",
    description="Retrieves visual comparison details directly using proposal_id.",
)
def get_proposal_visual_comparison(
    proposal_id: str,
    viewport: str = "desktop",
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> VisualComparisonResponse:
    """Retrieve visual comparison details directly by proposal ID."""
    clean_prop_id = _validate_identifier(proposal_id, "proposal_id")
    proposal = run_store.get_proposal(clean_prop_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal '{clean_prop_id}' not found.",
        )
    run = run_store.get(proposal.run_id)
    if run:
        check_run_access(run, current_user)
    return get_visual_comparison(proposal.run_id, clean_prop_id, viewport=viewport, current_user=current_user)


@router.post(
    "/runs/{run_id}/proposals/{proposal_id}/simulate-repair",
    response_model=VisualComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Simulate repair patch in a controlled sandbox",
    description=(
        "Applies the proposed repair patch exclusively in a controlled local sandbox. "
        "Strictly guarantees the external target website is NEVER modified. "
        "Preserves original before.png evidence immutably and captures after_{viewport}.png."
    ),
    responses={
        200: {"model": VisualComparisonResponse, "description": "Repair simulated successfully"},
        400: {"model": ErrorResponse, "description": "Invalid run_id or proposal_id"},
        404: {"model": ErrorResponse, "description": "Run or proposal not found"},
    },
)
def simulate_repair(
    run_id: str,
    proposal_id: str,
    payload: SimulateRepairRequest = None,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> VisualComparisonResponse:
    """Simulate applying proposed repair within a controlled, network-isolated sandbox."""
    clean_run_id = _validate_identifier(run_id, "run_id")
    clean_prop_id = _validate_identifier(proposal_id, "proposal_id")
    viewport = payload.viewport if payload else "desktop"

    run = run_store.get(clean_run_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_run_id}' not found.",
        )
    check_run_access(run, current_user)

    try:
        comparison = visual_repair_simulator.simulate_controlled_repair(
            clean_run_id, clean_prop_id, viewport=viewport
        )
        return comparison
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err),
        ) from val_err
    except Exception as exc:
        logger.error("Failed to simulate controlled repair: %s", str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Controlled repair simulation failed: {str(exc)}",
        ) from exc
