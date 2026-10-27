"""Pydantic schemas for self-healing locator repair and GitHub pull request API endpoints."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field

from github_integration.pull_requests.pr_manager import PullRequestResult
from self_healing.models import (
    CandidateLocator,
    LiveVerificationResult,
    PatchResult,
    ProposalStatus,
    RepairProposal,
    RepairResult,
    RepairStrategy,
    RepairValidationResult,
)


class RepairRequest(BaseModel):
    """Optional request payload for initiating locator repair."""

    finding_id: Optional[str] = Field(
        default=None,
        description="Optional finding ID to repair a specific defect. If omitted, all eligible findings are repaired.",
        examples=["defect_001"],
    )
    verify_live: bool = Field(
        default=False,
        description="Whether to navigate to the target page and verify the candidate locator against the live DOM.",
    )


class ProposalCreateRequest(BaseModel):
    """Request payload for creating repair proposals from verified repairs."""

    finding_id: Optional[str] = Field(
        default=None,
        description="Optional specific finding ID to generate a proposal for.",
    )
    target_file: Optional[str] = Field(
        default=None,
        description="Explicit test or code file in target repository containing the broken locator.",
    )
    workspace_root: Optional[str] = Field(
        default=None,
        description="Optional workspace boundary directory for path resolution.",
    )


class PatchGenerateRequest(BaseModel):
    """Request payload for synthesizing a minimal safe patch for a proposal."""

    target_file: str = Field(
        ...,
        description="Explicit test or code file relative to target workspace.",
    )
    workspace_root: Optional[str] = Field(
        default=None,
        description="Optional workspace boundary directory.",
    )


class PullRequestSubmitRequest(BaseModel):
    """Request payload for submitting an approved repair proposal as a GitHub Pull Request."""

    user_approved: bool = Field(
        default=False,
        description="Explicit user approval gate. Must be True to submit remote PR.",
    )
    target_file: Optional[str] = Field(
        default=None,
        description="Optional target file path to commit on branch before PR creation.",
    )
    base_branch: Optional[str] = Field(
        default=None,
        description="Optional target base branch (defaults to main or configured base branch).",
    )
    simulate: bool = Field(
        default=False,
        description="Simulate Pull Request creation without making real remote API calls.",
    )


__all__ = [
    "CandidateLocator",
    "LiveVerificationResult",
    "PatchGenerateRequest",
    "PatchResult",
    "ProposalCreateRequest",
    "ProposalStatus",
    "PullRequestResult",
    "PullRequestSubmitRequest",
    "RepairProposal",
    "RepairRequest",
    "RepairResult",
    "RepairStrategy",
    "RepairValidationResult",
]
