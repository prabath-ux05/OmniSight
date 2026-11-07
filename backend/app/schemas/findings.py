"""Data schemas for OmniSight UI defect findings."""

from typing import Literal
from pydantic import BaseModel, Field


class EvidenceReferences(BaseModel):
    """References to visual and DOM artifacts supporting a finding."""

    screenshot_path: str | None = Field(
        default=None,
        description="Relative or accessible path to the captured screenshot",
        examples=["artifacts/run_001/before.png"],
    )
    dom_snapshot_path: str | None = Field(
        default=None,
        description="Relative or accessible path to the saved DOM HTML snapshot",
        examples=["artifacts/run_001/dom.html"],
    )


class FindingResponse(BaseModel):
    """A structured UI defect finding coordinated with the Vision Engine contract."""

    finding_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the defect finding",
        examples=["defect_001"],
    )
    category: Literal[
        "layout_overflow",
        "missing_visible_element",
        "broken_image",
    ] = Field(
        ...,
        description="Category of the detected UI defect matching team agreements",
    )
    severity: Literal["low", "medium", "high", "critical"] = Field(
        ...,
        description="Severity level of the defect",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence score between 0.0 and 1.0",
        examples=[0.92],
    )
    description: str = Field(
        ...,
        min_length=1,
        description="Human-readable explanation of the defect",
    )
    selector: str | None = Field(
        default=None,
        description="CSS or DOM selector of the affected element, if identified",
        examples=["#main-content-panel"],
    )
    evidence: EvidenceReferences = Field(
        default_factory=EvidenceReferences,
        description="References to screenshot and DOM evidence",
    )
    source: Literal["mock", "vlm"] = Field(
        default="mock",
        description="Indicates whether the finding was mock-generated or from a real VLM",
    )
