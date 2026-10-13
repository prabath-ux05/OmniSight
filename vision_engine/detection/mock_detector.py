
"""Deterministic mock detector for the OmniSight Vision Engine."""

from typing import Literal

from vision_engine.evidence_validator import validate_evidence
from vision_engine.models import (
    EvidenceReferences,
    VisionFinding,
    VisionInput,
)


MockScenario = Literal["defect", "clean"]


def detect_mock(
    input_data: VisionInput,
    *,
    scenario: MockScenario = "defect",
) -> list[VisionFinding]:
    """
    Return predictable mock findings for a configured scenario.

    This is mock behavior only. It does not inspect screenshot pixels,
    analyze DOM content, or detect real UI defects.

    Args:
        input_data: Inspection input containing evidence paths.
        scenario: "defect" returns sample findings; "clean" returns none.

    Raises:
        ValueError: If evidence validation fails.
    """
    errors = validate_evidence(input_data)

    if errors:
        raise ValueError(
            "Evidence validation failed: " + "; ".join(errors)
        )

    if scenario == "clean":
        return []

    evidence = EvidenceReferences(
        screenshot_path=input_data.screenshot_path,
        dom_snapshot_path=input_data.dom_snapshot_path,
    )

    return [
        VisionFinding(
            finding_id=f"{input_data.run_id}-mock-001",
            category="layout_overflow",
            severity="medium",
            confidence=0.90,
            description=(
                "Mock finding: possible layout overflow. "
                "This is sample output, not a verified defect."
            ),
            selector=None,
            evidence=evidence,
            source="mock",
        ),
        VisionFinding(
            finding_id=f"{input_data.run_id}-mock-002",
            category="broken_image",
            severity="low",
            confidence=0.85,
            description=(
                "Mock finding: possible broken image. "
                "This is sample output, not a verified defect."
            ),
            selector=None,
            evidence=evidence,
            source="mock",
        ),
    ]
