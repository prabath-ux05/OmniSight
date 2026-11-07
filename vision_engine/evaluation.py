"""Evaluate Vision Engine findings against manually verified defects."""

from pydantic import BaseModel, Field

from vision_engine.models import VisionFinding


class EvaluationResult(BaseModel):
    """Structured defect-detection evaluation results."""

    true_positive_ids: list[str] = Field(default_factory=list)
    false_positive_ids: list[str] = Field(default_factory=list)
    false_negative_ids: list[str] = Field(default_factory=list)

    precision: float = Field(ge=0.0, le=1.0)
    recall: float = Field(ge=0.0, le=1.0)
    f1_score: float = Field(ge=0.0, le=1.0)

    @property
    def true_positive_count(self) -> int:
        return len(self.true_positive_ids)

    @property
    def false_positive_count(self) -> int:
        return len(self.false_positive_ids)

    @property
    def false_negative_count(self) -> int:
        return len(self.false_negative_ids)


def _matches(
    expected: VisionFinding,
    detected: VisionFinding,
) -> bool:
    """Check whether a detected finding matches an expected defect."""

    if expected.category != detected.category:
        return False

    # If the expected defect has a selector, require an exact match.
    if expected.selector is not None:
        return expected.selector == detected.selector

    # Without an expected selector, category is used for matching.
    return True


def evaluate_findings(
    expected_findings: list[VisionFinding],
    detected_findings: list[VisionFinding],
) -> EvaluationResult:
    """
    Compare detector output with manually verified expected findings.

    Each expected finding can match at most one detected finding.
    Each detected finding can match at most one expected finding.

    Precision and recall are set to 0 when their denominator is zero.
    """

    expected_ids = [finding.finding_id for finding in expected_findings]
    detected_ids = [finding.finding_id for finding in detected_findings]

    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError("Expected findings contain duplicate finding IDs.")

    if len(detected_ids) != len(set(detected_ids)):
        raise ValueError("Detected findings contain duplicate finding IDs.")

    matched_detected_indices: set[int] = set()
    true_positive_ids: list[str] = []
    false_negative_ids: list[str] = []

    # Match each expected defect with at most one detector result.
    for expected in expected_findings:
        matched_index = None

        for index, detected in enumerate(detected_findings):
            if index in matched_detected_indices:
                continue

            if _matches(expected, detected):
                matched_index = index
                break

        if matched_index is None:
            false_negative_ids.append(expected.finding_id)
        else:
            matched_detected_indices.add(matched_index)
            true_positive_ids.append(
                detected_findings[matched_index].finding_id
            )

    false_positive_ids = [
        finding.finding_id
        for index, finding in enumerate(detected_findings)
        if index not in matched_detected_indices
    ]

    true_positive_count = len(true_positive_ids)
    false_positive_count = len(false_positive_ids)
    false_negative_count = len(false_negative_ids)

    precision_denominator = true_positive_count + false_positive_count
    recall_denominator = true_positive_count + false_negative_count

    precision = (
        true_positive_count / precision_denominator
        if precision_denominator
        else 0.0
    )

    recall = (
        true_positive_count / recall_denominator
        if recall_denominator
        else 0.0
    )

    f1_score = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return EvaluationResult(
        true_positive_ids=true_positive_ids,
        false_positive_ids=false_positive_ids,
        false_negative_ids=false_negative_ids,
        precision=precision,
        recall=recall,
        f1_score=f1_score,
    )