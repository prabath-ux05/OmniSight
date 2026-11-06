
"""Data models for the OmniSight Vision Engine."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class VisionInput(BaseModel):
    """Evidence supplied to the Vision Engine."""

    run_id: str = Field(min_length=1, pattern=r".*\S.*")
    url: str = Field(min_length=1, pattern=r".*\S.*")

    screenshot_path: str | None = Field(
        default=None, min_length=1, pattern=r".*\S.*"
    )
    dom_snapshot_path: str | None = Field(
        default=None, min_length=1, pattern=r".*\S.*"
    )

    crop_box: "BoundingBox | None" = None
    crop_boxes: "list[BoundingBox] | None" = Field(
        default=None,
        min_length=1,
    )

    @model_validator(mode="after")
    def require_some_evidence(self):
        if not self.screenshot_path and not self.dom_snapshot_path:
            raise ValueError(
                "At least a screenshot path or DOM snapshot path is required."
            )

        if (
            self.crop_box is not None or self.crop_boxes is not None
        ) and not self.screenshot_path:
            raise ValueError("Crop boxes require a screenshot path.")

        if self.crop_box is not None and self.crop_boxes is not None:
            raise ValueError(
                "Use either crop_box or crop_boxes, not both."
            )

        return self


class EvidenceReferences(BaseModel):
    """References to evidence associated with a finding."""

    screenshot_path: str | None = None
    dom_snapshot_path: str | None = None


class BoundingBox(BaseModel):
    """Coordinates of a detected UI defect."""

    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)


class RepairRecommendation(BaseModel):
    """A suggested correction for a detected UI defect."""

    summary: str = Field(min_length=1)
    suggested_action: str = Field(min_length=1)
    rationale: str = Field(min_length=1)


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

    repair_recommendation: RepairRecommendation | None = None

    selector: str | None = None

    bounding_box: BoundingBox | None = None

    evidence: EvidenceReferences

    source: Literal["mock", "vlm"] = "mock"
