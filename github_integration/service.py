"""High-level GitHub Integration Service orchestrating repair proposals, patches, and pull requests."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any, Optional
import httpx

from github_integration.branches.branch_manager import (
    create_github_branch,
    sanitize_branch_name,
)
from github_integration.commits.patch_generator import (
    generate_locator_patch,
    validate_target_path,
)
from github_integration.pull_requests.pr_manager import (
    ApprovalRequiredError,
    PullRequestError,
    PullRequestResult,
    create_repair_pull_request,
)
from self_healing.models import (
    PatchResult,
    ProposalStatus,
    RepairProposal,
    RepairResult,
)


class GitHubIntegrationService:
    """Coordinates proposal generation, patch synthesis, branch preparation, and PR submission."""

    def __init__(
        self,
        token: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        base_branch: Optional[str] = None,
    ) -> None:
        self.token = token
        self.owner = owner
        self.repo = repo
        self.base_branch = base_branch or "main"

    @classmethod
    def from_env(cls) -> GitHubIntegrationService:
        """Initialize service using environment variables."""
        token = (
            os.getenv("GITHUB_ACCESS_TOKEN")
            or os.getenv("GITHUB_TOKEN")
            or ""
        ).strip()
        owner = (
            os.getenv("GITHUB_REPO_OWNER")
            or os.getenv("GITHUB_OWNER")
            or ""
        ).strip()
        repo = (
            os.getenv("GITHUB_REPO_NAME")
            or os.getenv("GITHUB_REPO")
            or ""
        ).strip()
        base_branch = os.getenv("GITHUB_BASE_BRANCH", "main").strip() or "main"

        return cls(
            token=token or None,
            owner=owner or None,
            repo=repo or None,
            base_branch=base_branch,
        )

    def is_configured(self) -> bool:
        """Check if all necessary GitHub credentials and target repository are configured."""
        return bool(self.token and self.owner and self.repo)

    def get_configuration_status(self) -> dict[str, Any]:
        """Report GitHub integration status with strict masking of API credentials."""
        has_token = bool(self.token and self.token.strip())
        masked_token = (
            f"...{self.token[-4:]}"
            if (has_token and len(self.token or "") >= 4)
            else ("configured" if has_token else "missing")
        )

        configured = bool(has_token and self.owner and self.repo)
        if configured:
            message = (
                f"GitHub integration ready for repository '{self.owner}/{self.repo}' "
                f"(base branch: '{self.base_branch}'). User approval gate active."
            )
        else:
            missing = []
            if not has_token:
                missing.append("GITHUB_ACCESS_TOKEN")
            if not self.owner:
                missing.append("GITHUB_REPO_OWNER")
            if not self.repo:
                missing.append("GITHUB_REPO_NAME")
            message = (
                f"GitHub integration unconfigured (missing: {', '.join(missing)}). "
                f"Simulated local proposals and safe patch generation remain fully available."
            )

        return {
            "is_configured": configured,
            "owner": self.owner,
            "repo": self.repo,
            "base_branch": self.base_branch,
            "token_status": masked_token,
            "approval_gate_required": True,
            "message": message,
        }

    def create_proposal(
        self,
        repair_result: RepairResult,
        run_id: str,
        target_file: Optional[str] = None,
        workspace_root: Optional[str] = None,
        allow_internal: bool = False,
    ) -> RepairProposal:
        """Convert a verified RepairResult into a structured RepairProposal.

        Args:
            repair_result: The verified repair outcome from the Self-Healing engine.
            run_id: Associated run identifier.
            target_file: Optional explicit target file path.
            workspace_root: Optional workspace boundary directory.
            allow_internal: Whether internal files can be targeted (test fixtures).

        Returns:
            Structured, reviewable RepairProposal.
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        proposal_id = f"prop_{run_id}_{repair_result.finding_id}"

        # Determine initial proposal lifecycle state
        if not repair_result.repaired or not repair_result.best_locator:
            status = ProposalStatus.FAILED
        elif (
            repair_result.live_verification
            and repair_result.live_verification.attempted
            and repair_result.live_verification.is_verified
        ):
            status = ProposalStatus.LOCALLY_VALIDATED
        else:
            status = ProposalStatus.PROPOSED

        patch_res: Optional[PatchResult] = None
        if target_file and repair_result.best_locator:
            patch_res = generate_locator_patch(
                original_selector=repair_result.original_selector,
                proposed_locator=repair_result.best_locator,
                target_file=target_file,
                workspace_root=workspace_root,
                allow_internal=allow_internal,
            )

        return RepairProposal(
            proposal_id=proposal_id,
            run_id=run_id,
            finding_id=repair_result.finding_id,
            original_selector=repair_result.original_selector,
            proposed_locator=repair_result.best_locator or "",
            strategy=repair_result.strategy,
            confidence=repair_result.confidence,
            rationale=repair_result.reason,
            status=status,
            target_file=target_file,
            patch=patch_res,
            snapshot_validation=repair_result.snapshot_validation,
            live_verification=repair_result.live_verification,
            created_at=now_iso,
        )

    def generate_proposal_patch(
        self,
        proposal: RepairProposal,
        target_file: str,
        workspace_root: Optional[str] = None,
        allow_internal: bool = False,
    ) -> PatchResult:
        """Generate and attach a minimal unified diff to an existing proposal."""
        patch_result = generate_locator_patch(
            original_selector=proposal.original_selector,
            proposed_locator=proposal.proposed_locator,
            target_file=target_file,
            workspace_root=workspace_root,
            allow_internal=allow_internal,
        )
        proposal.target_file = target_file
        proposal.patch = patch_result
        return patch_result

    def submit_pull_request(
        self,
        proposal: RepairProposal,
        user_approved: bool = False,
        patched_content: Optional[str] = None,
        client: Optional[httpx.Client] = None,
        simulate: bool = False,
    ) -> PullRequestResult:
        """Submit a Pull Request for an approved proposal.

        Enforces:
        - Strict human approval check: user_approved must be True.
        - Branch name sanitization.
        - Remote PR creation via GitHub REST API.
        """
        if not user_approved:
            raise ApprovalRequiredError(
                "Pull Request creation is strictly gated: user approval is required."
            )

        branch_name = sanitize_branch_name(proposal.finding_id)
        proposal.branch_name = branch_name

        # In offline/simulated mode or unconfigured credentials, perform simulated flow
        is_simulated = simulate or not self.is_configured()

        pr_result = create_repair_pull_request(
            proposal=proposal,
            token=self.token or "simulated-token",
            owner=self.owner or "simulated-owner",
            repo=self.repo or "simulated-repo",
            base_branch=self.base_branch,
            branch_name=branch_name,
            user_approved=True,
            patched_file_content=patched_content,
            client=client,
            simulate=is_simulated,
        )

        if pr_result.status in ("created", "simulated"):
            proposal.status = ProposalStatus.REMOTELY_SUBMITTED
            proposal.pr_url = pr_result.pr_url
            proposal.pr_number = pr_result.pr_number

        return pr_result


github_service = GitHubIntegrationService.from_env()
