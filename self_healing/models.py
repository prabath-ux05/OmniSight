"""Data contracts and schemas for the Self-Healing Locator Repair Engine."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, model_validator


class RepairStrategy(str, Enum):
    """Supported locator generation strategies ranked by structural resilience."""

    DATA_ATTRIBUTE = "data_attribute"      # e.g. [data-testid="..."], [data-cy="..."]
    STABLE_ID = "stable_id"                # e.g. #primary-button (excluding volatile IDs)
    ACCESSIBLE_ROLE_NAME = "accessible_role_name"  # e.g. button[aria-label="..."], [role="..."]
    UNIQUE_TEXT = "unique_text"            # e.g. button:has-text("...") or text-based locator
    SEMANTIC_CSS = "semantic_css"          # e.g. button.btn-primary.cta-action-btn
    HIERARCHICAL = "hierarchical"          # e.g. #hero-container > button.btn-primary
    FALLBACK = "fallback"


class CandidateLocator(BaseModel):
    """An alternative locator candidate generated from DOM analysis."""

    selector: str = Field(..., description="The alternative CSS, data, or role selector string")
    strategy: RepairStrategy = Field(..., description="The heuristic strategy used to synthesize this locator")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Heuristic resilience and stability score")
    score: Optional[float] = Field(default=None, description="Score alias for confidence")
    is_unique: bool = Field(..., description="Whether this locator resolves to exactly one element in the DOM")
    match_count: int = Field(..., ge=0, description="Number of elements matching this selector in the DOM snapshot")
    description: str = Field(..., description="Explainable rationale for this locator candidate")

    @model_validator(mode="after")
    def sync_score(self):
        if self.score is None:
            self.score = self.confidence
        return self



class RepairValidationResult(BaseModel):
    """Detailed verification outcome of resolving a candidate locator in the DOM snapshot."""

    is_valid: bool = Field(..., description="True only if candidate resolves to exactly 1 intended element")
    matches: int = Field(..., ge=0, description="Count of elements resolved in the DOM snapshot")
    resolved_tag: Optional[str] = Field(default=None, description="HTML tag of the resolved element, if any")
    resolved_html_snippet: Optional[str] = Field(
        default=None, description="Short HTML snippet of the resolved element"
    )
    validation_message: str = Field(..., description="Human-readable validation status message")


class LiveVerificationResult(BaseModel):
    """Detailed outcome of testing a candidate locator against a fresh live webpage."""

    attempted: bool = Field(default=False, description="Whether live browser verification was executed")
    is_verified: bool = Field(default=False, description="True only if candidate uniquely resolved in live page DOM")
    matches: int = Field(default=0, ge=0, description="Count of elements matching locator on live page")
    target_url: Optional[str] = Field(default=None, description="Live URL where verification was conducted")
    resolved_tag: Optional[str] = Field(default=None, description="HTML tag resolved on live page")
    validation_message: str = Field(default="Live verification not attempted", description="Status or error message")


class RepairResult(BaseModel):
    """Structured repair outcome returned by the Self-Healing Locator Repair Engine."""

    finding_id: str = Field(..., description="Identifier of the origin UI defect finding")
    original_selector: str = Field(..., description="The failed or missing locator targeted for repair")
    repaired: bool = Field(
        default=False,
        description="True only if a valid, uniquely resolvable replacement candidate was verified in the DOM",
    )
    best_locator: Optional[str] = Field(
        default=None,
        description="Highest-scoring verified locator candidate, or None if repair was not possible",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of the best repaired locator",
    )
    strategy: Optional[RepairStrategy] = Field(
        default=None,
        description="Strategy used for the best locator",
    )
    score: Optional[float] = Field(default=None, description="Score alias for confidence")
    candidate_locators: list[CandidateLocator] = Field(
        default_factory=list,
        description="All generated alternative locator candidates, ordered by score descending",
    )
    candidates: list[CandidateLocator] = Field(
        default_factory=list,
        description="All generated alternative locator candidates (alias for candidate_locators)",
    )

    @model_validator(mode="after")
    def sync_candidate_lists(self):
        if self.score is None:
            self.score = self.confidence
        if self.candidate_locators and not self.candidates:
            self.candidates = self.candidate_locators
        elif self.candidates and not self.candidate_locators:
            self.candidate_locators = self.candidates
        return self


    validation: Optional[RepairValidationResult] = Field(
        default=None,
        description="Validation result for the best locator candidate in the DOM snapshot",
    )
    snapshot_validation: Optional[RepairValidationResult] = Field(
        default=None,
        description="Explicit validation result tested against captured DOM snapshot",
    )
    live_verification: Optional[LiveVerificationResult] = Field(
        default=None,
        description="Fresh verification result tested against the live target page",
    )
    reason: str = Field(
        ...,
        description="Explainable description of the self-healing outcome, decisions, or failure cause",
    )


class ProposalStatus(str, Enum):
    """Lifecycle status of a self-healing repair proposal."""

    PROPOSED = "proposed"
    LOCALLY_VALIDATED = "locally_validated"
    REMOTELY_SUBMITTED = "remotely_submitted"
    REJECTED = "rejected"
    FAILED = "failed"


class PatchResult(BaseModel):
    """Result of generating a minimal, safe diff patch for an approved locator change."""

    success: bool = Field(..., description="Whether diff patch generation succeeded")
    target_file: str = Field(..., description="Target file path relative to repository workspace")
    diff: Optional[str] = Field(default=None, description="Unified diff patch string")
    original_selector: str = Field(..., description="Original selector targeted for replacement")
    proposed_locator: str = Field(..., description="Proposed replacement locator")
    replaced_count: int = Field(default=0, ge=0, description="Number of occurrences replaced in target file")
    error: Optional[str] = Field(default=None, description="Error explanation if patch generation failed")


class RepairProposal(BaseModel):
    """Reviewable repair proposal converting verified candidates into an actionable change proposal."""

    proposal_id: str = Field(..., description="Unique proposal identifier")
    run_id: str = Field(..., description="Associated OmniSight run identifier")
    finding_id: str = Field(..., description="Associated finding identifier")
    original_selector: str = Field(..., description="Original failed or missing selector")
    proposed_locator: str = Field(..., description="Highest-scoring verified replacement locator")
    strategy: Optional[RepairStrategy] = Field(default=None, description="Strategy used to synthesize the locator")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Locator resilience score")
    rationale: str = Field(..., description="Explainable rationale and decision notes")
    status: ProposalStatus = Field(default=ProposalStatus.PROPOSED, description="Current lifecycle status")
    target_file: Optional[str] = Field(default=None, description="Explicit target test/code file when provided")
    patch: Optional[PatchResult] = Field(default=None, description="Generated diff patch when target file is known")
    snapshot_validation: Optional[RepairValidationResult] = Field(
        default=None, description="Snapshot DOM validation outcome"
    )
    live_verification: Optional[LiveVerificationResult] = Field(
        default=None, description="Fresh live-page verification outcome"
    )
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    branch_name: Optional[str] = Field(default=None, description="Git branch name if created")
    pr_url: Optional[str] = Field(default=None, description="GitHub Pull Request URL if submitted")
    pr_number: Optional[int] = Field(default=None, description="GitHub Pull Request number if submitted")
