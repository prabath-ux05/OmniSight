"""OmniSight GitHub Automation & Integration Module."""

from github_integration.branches.branch_manager import (
    BranchManagementError,
    create_github_branch,
    sanitize_branch_name,
)
from github_integration.commits.patch_generator import (
    FORBIDDEN_INTERNAL_DIRS,
    PatchSecurityError,
    generate_locator_patch,
    validate_target_path,
)
from github_integration.pull_requests.pr_manager import (
    ApprovalRequiredError,
    PullRequestError,
    PullRequestResult,
    build_pr_markdown_body,
    create_repair_pull_request,
)
from github_integration.service import (
    GitHubIntegrationService,
    github_service,
)

__all__ = [
    "ApprovalRequiredError",
    "BranchManagementError",
    "FORBIDDEN_INTERNAL_DIRS",
    "GitHubIntegrationService",
    "PatchResult",
    "PatchSecurityError",
    "PullRequestError",
    "PullRequestResult",
    "RepairProposal",
    "build_pr_markdown_body",
    "create_github_branch",
    "create_repair_pull_request",
    "generate_locator_patch",
    "github_service",
    "sanitize_branch_name",
    "validate_target_path",
]
