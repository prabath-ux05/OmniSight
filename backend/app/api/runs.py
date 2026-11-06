from typing import Any, Optional
from urllib.parse import unquote
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from backend.app.core.logging import logger
from backend.app.schemas.errors import ErrorResponse
from backend.app.schemas.findings import FindingResponse
from backend.app.schemas.repairs import (
    PatchGenerateRequest,
    PatchResult,
    ProposalCreateRequest,
    PullRequestResult,
    PullRequestSubmitRequest,
    RepairProposal,
    RepairRequest,
    RepairResult,
)
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
        "Optionally schedules real browser capture and vision analysis."
    ),
    responses={
        201: {"model": RunResponse, "description": "Run created and queued successfully"},
        422: {"description": "Request payload validation error (e.g. missing or malformed URL)"},
    },
)
def create_run(
    payload: RunCreateRequest,
    background_tasks: BackgroundTasks = None,
    auto_execute: bool = False,
) -> RunResponse:
    """Validate request and create a new inspection run in 'queued' status."""
    logger.info("Received run creation request for URL: %s", payload.url)
    run = run_store.create(payload)
    logger.info("Run created successfully with ID: %s (status=%s)", run.run_id, run.status)

    if auto_execute and background_tasks is not None:
        from backend.app.services.orchestrator import run_orchestrator
        background_tasks.add_task(run_orchestrator.execute_run, run.run_id, str(payload.url))

    return run


@router.post(
    "/runs/{run_id}/execute",
    response_model=RunResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute inspection pipeline for a run",
    description=(
        "Triggers the integrated Browser Agent capture and Vision Engine analysis "
        "pipeline for an existing run."
    ),
    responses={
        200: {"model": RunResponse, "description": "Run execution started"},
        400: {"model": ErrorResponse, "description": "Invalid run_id format"},
        404: {"model": ErrorResponse, "description": "Run not found"},
    },
)
def execute_run_pipeline(
    run_id: str,
    background_tasks: BackgroundTasks = None,
) -> RunResponse:
    """Execute browser capture and vision engine analysis for an existing run."""
    clean_id = _validate_run_id(run_id)
    run = run_store.get(clean_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_id}' not found.",
        )

    from backend.app.services.orchestrator import run_orchestrator

    if background_tasks is not None:
        background_tasks.add_task(run_orchestrator.execute_run, run.run_id, run.url)
    else:
        run_orchestrator.execute_run(run.run_id, run.url)

    return run_store.get(run.run_id) or run


@router.get(

    "/runs/vlm/config",
    status_code=status.HTTP_200_OK,
    summary="Check VLM provider configuration status",
    description="Inspects active VLM provider readiness without exposing secrets or credentials.",
)
def get_vlm_configuration(provider: Optional[str] = None) -> dict[str, Any]:
    """Inspect and report VLM provider configuration status."""
    from vision_engine.detection.providers import check_vlm_configuration
    return check_vlm_configuration(provider_name=provider)


@router.get(
    "/runs/github/config",
    status_code=status.HTTP_200_OK,
    summary="Check GitHub integration configuration status",
    description="Inspects GitHub integration readiness without exposing secrets or credentials.",
)
@router.get(
    "/github/config",
    status_code=status.HTTP_200_OK,
    summary="Check GitHub integration configuration status",
    description="Inspects GitHub integration readiness without exposing secrets or credentials.",
)
def get_github_configuration() -> dict[str, Any]:
    """Inspect and report GitHub integration configuration status."""
    from github_integration.service import GitHubIntegrationService
    return GitHubIntegrationService.from_env().get_configuration_status()




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


@router.post(
    "/runs/{run_id}/repair",
    response_model=list[RepairResult],
    status_code=status.HTTP_200_OK,
    summary="Suggest and validate locator repairs for run findings",
    description=(
        "Consumes verified findings and captured DOM snapshot evidence to suggest, "
        "rank, and validate candidate locators using deterministic heuristics. "
        "Does NOT claim that any locator was applied to application code."
    ),
    responses={
        200: {"description": "List of repair results for eligible findings"},
        400: {"model": ErrorResponse, "description": "Invalid run_id format"},
        404: {"model": ErrorResponse, "description": "Run or finding not found"},
    },
)
def repair_run_findings(
    run_id: str,
    finding_id: Optional[str] = None,
    verify_live: bool = False,
    payload: Optional[RepairRequest] = None,
) -> list[RepairResult]:
    """Execute autonomous locator repair for findings associated with run_id."""
    clean_id = _validate_run_id(run_id)
    run = run_store.get(clean_id)
    if not run:
        logger.warning("Repair requested for unknown run: '%s'", clean_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_id}' not found.",
        )

    findings = run_store.get_findings(clean_id) or []

    # Check for specific finding ID request (via body or query parameter)
    target_fid: Optional[str] = None
    should_verify_live: bool = verify_live
    if payload:
        if payload.finding_id:
            target_fid = payload.finding_id.strip()
        if payload.verify_live:
            should_verify_live = True
    elif finding_id:
        target_fid = finding_id.strip()

    if target_fid:
        matched = [f for f in findings if f.finding_id == target_fid]
        if not matched:
            logger.warning("Repair requested for unknown finding '%s' in run '%s'", target_fid, clean_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Finding '{target_fid}' not found in run '{clean_id}'.",
            )
        eligible_findings = matched
    else:
        # Repair all findings recorded for this run
        eligible_findings = findings

    from self_healing import self_healing_engine

    results: list[RepairResult] = []
    for f in eligible_findings:
        repair_res = self_healing_engine.repair_finding(
            f,
            verify_live=should_verify_live,
            target_url=run.url,
        )
        results.append(repair_res)

    run_store.set_repairs(clean_id, results)
    logger.info("Processed %d repair candidate(s) for run %s", len(results), clean_id)
    return results



@router.get(
    "/runs/{run_id}/repair",
    response_model=list[RepairResult],
    status_code=status.HTTP_200_OK,
    summary="Get repair suggestions for run findings",
    description="Retrieves existing or newly analyzed repair suggestions for a run.",
    responses={
        200: {"description": "List of repair results for eligible findings"},
        400: {"model": ErrorResponse, "description": "Invalid run_id format"},
        404: {"model": ErrorResponse, "description": "Run or finding not found"},
    },
)
def get_run_repairs(
    run_id: str,
    finding_id: Optional[str] = None,
) -> list[RepairResult]:
    """Retrieve repair results for run_id."""
    return repair_run_findings(run_id=run_id, finding_id=finding_id, payload=None)


# =============================================================================
# Self-Healing Proposals & GitHub Pull Request Workflows
# =============================================================================

@router.post(
    "/runs/{run_id}/proposals",
    response_model=list[RepairProposal],
    status_code=status.HTTP_200_OK,
    summary="Generate reviewable repair proposals from verified repairs",
    description="Converts verified locator candidates into structured, reviewable repair proposals.",
)
def generate_run_proposals(
    run_id: str,
    payload: Optional[ProposalCreateRequest] = None,
) -> list[RepairProposal]:
    """Convert verified locator repairs into structured, reviewable RepairProposals."""
    clean_id = _validate_run_id(run_id)
    run = run_store.get(clean_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_id}' not found.",
        )

    # Fetch existing repairs or execute repair analysis if not cached
    repairs = run_store.get_repairs(clean_id)
    if not repairs:
        repairs = repair_run_findings(run_id=clean_id, payload=None)


    target_fid = payload.finding_id.strip() if payload and payload.finding_id else None
    target_file = payload.target_file.strip() if payload and payload.target_file else None
    workspace_root = payload.workspace_root.strip() if payload and payload.workspace_root else None

    from github_integration import github_service

    proposals: list[RepairProposal] = []
    for r in repairs:
        if target_fid and r.finding_id != target_fid:
            continue
        prop = github_service.create_proposal(
            repair_result=r,
            run_id=clean_id,
            target_file=target_file,
            workspace_root=workspace_root,
        )
        proposals.append(prop)

    run_store.set_proposals(clean_id, proposals)
    logger.info("Generated %d repair proposal(s) for run %s", len(proposals), clean_id)
    return proposals


@router.get(
    "/runs/{run_id}/proposals",
    response_model=list[RepairProposal],
    status_code=status.HTTP_200_OK,
    summary="Get cached repair proposals for a run",
    description="Retrieves existing repair proposals generated for this run.",
)
def get_run_proposals(run_id: str) -> list[RepairProposal]:
    """Retrieve existing repair proposals for a run."""
    clean_id = _validate_run_id(run_id)
    run = run_store.get(clean_id)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_id}' not found.",
        )

    existing = run_store.get_proposals(clean_id)
    if existing is not None:
        return existing
    return generate_run_proposals(clean_id, payload=None)


@router.post(
    "/runs/{run_id}/proposals/{proposal_id}/patch",
    response_model=PatchResult,
    status_code=status.HTTP_200_OK,
    summary="Synthesize a safe minimal patch for a proposal",
    description="Generates a minimal unified diff without modifying files on disk.",
)
def generate_proposal_patch_endpoint(
    run_id: str,
    proposal_id: str,
    payload: PatchGenerateRequest,
) -> PatchResult:
    """Generate a safe minimal diff for an approved proposal against a target file."""
    clean_id = _validate_run_id(run_id)
    proposal = run_store.get_proposal(clean_id, proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal '{proposal_id}' not found for run '{clean_id}'.",
        )

    from github_integration import github_service

    patch_res = github_service.generate_proposal_patch(
        proposal=proposal,
        target_file=payload.target_file,
        workspace_root=payload.workspace_root,
    )
    if not patch_res.success:
        err_lower = (patch_res.error or "").lower()
        if "traversal" in err_lower or "internal" in err_lower or "outside" in err_lower:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=patch_res.error,
            )

    return patch_res



@router.post(
    "/runs/{run_id}/proposals/{proposal_id}/pull-request",
    response_model=PullRequestResult,
    status_code=status.HTTP_200_OK,
    summary="Submit an approved repair proposal as a GitHub Pull Request",
    description="Prepares branch and creates Pull Request. Strictly requires user_approved=True.",
)
def submit_proposal_pr_endpoint(
    run_id: str,
    proposal_id: str,
    payload: PullRequestSubmitRequest,
) -> PullRequestResult:
    """Submit an approved proposal to GitHub with an explicit human approval gate."""
    clean_id = _validate_run_id(run_id)
    proposal = run_store.get_proposal(clean_id, proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal '{proposal_id}' not found for run '{clean_id}'.",
        )

    # 1. Human Approval Gate
    if not payload.user_approved:
        logger.warning(
            "Rejected PR submission for proposal %s: user_approved is False", proposal_id
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pull request submission requires explicit user approval (user_approved must be True).",
        )

    from github_integration.service import GitHubIntegrationService
    from github_integration.pull_requests.pr_manager import (
        ApprovalRequiredError,
        PullRequestError,
    )

    try:
        service = GitHubIntegrationService.from_env()
        pr_result = service.submit_pull_request(
            proposal=proposal,
            user_approved=True,
            simulate=payload.simulate,
        )

    except ApprovalRequiredError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    except PullRequestError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))

    return pr_result

