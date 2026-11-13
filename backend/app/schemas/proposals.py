"""Data schemas for OmniSight self-healing repair proposals."""

from typing import Literal
from pydantic import BaseModel, Field


class RepairProposalCreateRequest(BaseModel):
    """Payload to create a new self-healing repair proposal for an inspection run."""

    finding_id: str | None = Field(
        default=None,
        description="Identifier of the specific defect finding addressed by this proposal",
        examples=["defect_run_1234_001"],
    )
    proposed_change: str = Field(
        ...,
        min_length=1,
        description="Detailed description or patch content (e.g. CSS diff, DOM patch) of the proposed fix",
        examples=["Update #main-container style with overflow-x: hidden to prevent viewport scroll."],
    )
    github_pr_url: str | None = Field(
        default=None,
        description="URL of an actual upstream GitHub pull request, if one has been generated",
        examples=["https://github.com/prabath-ux05/OmniSight/pull/42"],
    )
    github_pr_number: int | None = Field(
        default=None,
        description="Upstream pull request number if available",
        examples=[42],
    )


class ProposalDecisionRequest(BaseModel):
    """Reviewer decision payload for approving or rejecting a proposal."""

    notes: str | None = Field(
        default=None,
        description="Optional reviewer notes or rationale for the approval/rejection decision",
        examples=["Approved after reviewing affected layout responsiveness."],
    )
    revisit: bool = Field(
        default=False,
        description="Explicit flag allowing an already approved proposal decision to be revisited",
    )


class RepairProposalResponse(BaseModel):
    """Complete representation of a repair proposal and its distinct lifecycle stages."""

    proposal_id: str = Field(
        ...,
        description="Unique identifier for the repair proposal",
        examples=["prop_run_1234_001"],
    )
    run_id: str = Field(
        ...,
        description="Identifier of the associated inspection run",
        examples=["run_1234abcd"],
    )
    finding_id: str | None = Field(
        default=None,
        description="Identifier of the associated defect finding, if linked",
        examples=["defect_run_1234_001"],
    )
    proposed_change: str = Field(
        ...,
        description="Proposed code or style modification to heal the defect",
    )
    approval_status: Literal["pending", "approved", "rejected"] = Field(
        default="pending",
        description="Current human or automated review approval status",
    )
    execution_status: Literal["unapplied", "applying", "applied", "failed"] = Field(
        default="unapplied",
        description="Execution state of applying the repair patch",
    )
    verification_status: Literal[
        "unverified",
        "verified_success",
        "verified_failure",
        "inconclusive",
    ] = Field(
        default="unverified",
        description="Outcome of post-repair visual and DOM verification re-inspection",
    )
    github_pr_url: str | None = Field(
        default=None,
        description="Direct link to the actual GitHub pull request, if created",
    )
    github_pr_number: int | None = Field(
        default=None,
        description="GitHub PR number if created",
    )
    created_at: str = Field(
        ...,
        description="ISO-8601 UTC timestamp of proposal creation",
    )
    updated_at: str | None = Field(
        default=None,
        description="ISO-8601 UTC timestamp of last status change or review decision",
    )
    reviewer_notes: str | None = Field(
        default=None,
        description="Reviewer notes or rationale recorded with approval or rejection decision",
    )
    can_revisit: bool = Field(
        default=False,
        description="Whether this decision can be revisited (approved proposals can be revisited; rejected cannot)",
    )


class ProposalStatusResponse(BaseModel):
    """Lightweight summary of a proposal's current review, execution, and verification states."""

    proposal_id: str = Field(..., description="Unique proposal identifier")
    run_id: str = Field(..., description="Associated run identifier")
    approval_status: str = Field(..., description="Current review decision ('pending', 'approved', 'rejected')")
    execution_status: str = Field(..., description="Patch application status ('unapplied', 'applying', 'applied', 'failed')")
    verification_status: str = Field(..., description="Verification status ('unverified', 'verified_success', 'verified_failure', 'inconclusive')")
    github_pr_url: str | None = Field(default=None, description="GitHub pull request URL if created")
    updated_at: str | None = Field(default=None, description="ISO-8601 UTC timestamp of last update")


class VisualComparisonResponse(BaseModel):
    """Structured before-and-after visual comparison and repair audit details."""

    run_id: str = Field(..., description="Inspection run identifier")
    proposal_id: str = Field(..., description="Associated repair proposal identifier")
    finding_id: str | None = Field(default=None, description="Linked defect finding identifier")
    viewport: str = Field(default="desktop", description="Active comparison viewport ('desktop', 'tablet', 'mobile')")
    before_screenshot_url: str = Field(..., description="Accessible URL for the original immutable defect screenshot")
    after_screenshot_url: str | None = Field(default=None, description="Accessible URL for the repaired screenshot in controlled sandbox")
    before_exists: bool = Field(default=True, description="Whether original before screenshot exists on disk")
    after_exists: bool = Field(default=False, description="Whether simulated after screenshot exists on disk")
    controlled_environment: str = Field(
        default="Isolated Headless Sandbox (Local DOM Replay, Network Blocked)",
        description="Description of the controlled sandbox environment",
    )
    target_live_website_modified: bool = Field(
        default=False,
        description="Explicit guarantee that the live external target website was NOT modified",
    )
    approval_status: str = Field(default="pending", description="Current review status ('pending', 'approved', 'rejected')")
    execution_status: str = Field(default="unapplied", description="Patch execution status")
    verification_status: str = Field(default="unverified", description="Post-repair verification status")
    decision_timestamp: str | None = Field(default=None, description="Timestamp of reviewer decision")
    reviewer_notes: str | None = Field(default=None, description="Reviewer justification or notes")
    proposed_change: str = Field(..., description="Proposed CSS diff, DOM patch, or locator fix")
    finding_summary: dict | None = Field(default=None, description="Associated defect finding details (category, severity, selector)")
    diff_summary: str | None = Field(default=None, description="Summary of visual and structural differences")
    can_revisit: bool = Field(default=False, description="Whether the decision can be revisited")


class SimulateRepairRequest(BaseModel):
    """Payload to simulate applying a repair in a controlled environment."""

    viewport: str = Field(default="desktop", description="Target viewport to render ('desktop', 'tablet', 'mobile')")
