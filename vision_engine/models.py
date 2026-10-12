"""Data models for the OmniSight Vision Engine."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class VisionInput(BaseModel):
    """Evidence supplied to the Vision Engine."""

    run_id: str = Field(min_length=1)
    url: str = Field(min_length=1)

    screenshot_path: str | None = None
    dom_snapshot_path: str | None = None

    @model_validator(mode="after")
    def require_some_evidence(self):
        if not self.screenshot_path and not self.dom_snapshot_path:
            raise ValueError(
                "At least a screenshot path or DOM snapshot path is required."
            )
        return self


class EvidenceReferences(BaseModel):
    """References to evidence associated with a finding."""

    screenshot_path: str | None = None
    dom_snapshot_path: str | None = None


class VisionFinding(BaseModel):
    """A structured UI defect finding."""

    finding_id: str = Field(min_length=1)

    category: Literal[
        "layout_overflow",
        "missing_visible_element",
        "broken_image",
    ]

    severity: Literal["low", "medium", "high", "critical"]

    confidence: float = Field(ge=0.0, le=1.0)

    description: str = Field(min_length=1)

    selector: str | None = None

    evidence: EvidenceReferences

    source: Literal["mock", "vlm"] = "mock"