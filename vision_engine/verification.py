"""Before-and-after visual repair verification for OmniSight."""

from typing import Literal

from pydantic import BaseModel, Field

from vision_engine.evidence_validator import validate_evidence
from vision_engine.models import VisionFinding, VisionInput


VerificationStatus = Literal[
    "resolved",
    "partially_resolved",
    "unresolved",
    "unverifiable",
]


class VerificationResult(BaseModel):
    """Structured result of verifying a UI repair."""

    run_id: str
    original_finding_id: str
    status: VerificationStatus
    explanation: str = Field(min_length=1)
    before_evidence: bool
    after_evidence: bool
    matched_finding_ids: list[str] = Field(default_factory=list)


def verify_repair(
    original_finding: VisionFinding,
    before_input: VisionInput,
    after_input: VisionInput,
    after_findings: list[VisionFinding],
) -> VerificationResult:
    """
    Compare an original defect with findings from the repaired page.

    The after_findings must come from an actual analysis of the
    after-repair evidence. This function does not perform VLM inference.
    """

    before_errors = validate_evidence(before_input)
    after_errors = validate_evidence(after_input)

    if before_errors or after_errors:
        problems = before_errors + after_errors

        return VerificationResult(
            run_id=after_input.run_id,
            original_finding_id=original_finding.finding_id,
            status="unverifiable",
            explanation=(
                "Repair cannot be verified because evidence is invalid: "
                + "; ".join(problems)
            ),
            before_evidence=not before_errors,
            after_evidence=not after_errors,
        )

    # Match findings using category and, when available, CSS selector.
    matching_findings = [
        finding
        for finding in after_findings
        if finding.category == original_finding.category
        and (
            original_finding.selector is None
            or finding.selector == original_finding.selector
        )
    ]

    if not matching_findings:
        return VerificationResult(
            run_id=after_input.run_id,
            original_finding_id=original_finding.finding_id,
            status="resolved",
            explanation=(
                "The original defect was not detected in the "
                "after-repair findings."
            ),
            before_evidence=True,
            after_evidence=True,
        )

    severity_order = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }

    original_severity = severity_order[original_finding.severity]

    less_severe_findings = [
        finding
        for finding in matching_findings
        if severity_order[finding.severity] < original_severity
    ]

    matched_ids = [
        finding.finding_id for finding in matching_findings
    ]

    if less_severe_findings:
        status: VerificationStatus = "partially_resolved"
        explanation = (
            "The original defect is still detected, but its reported "
            "severity has decreased."
        )
    else:
        status = "unresolved"
        explanation = (
            "The original defect is still detected after the repair."
        )

    return VerificationResult(
        run_id=after_input.run_id,
        original_finding_id=original_finding.finding_id,
        status=status,
        explanation=explanation,
        before_evidence=True,
        after_evidence=True,
        matched_finding_ids=matched_ids,
    )