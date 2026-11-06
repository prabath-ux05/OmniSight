"""Automated Git branch creation and lifecycle management."""

from github_integration.branches.branch_manager import (
    BranchManagementError,
    create_github_branch,
    sanitize_branch_name,
)

__all__ = [
    "BranchManagementError",
    "create_github_branch",
    "sanitize_branch_name",
]
