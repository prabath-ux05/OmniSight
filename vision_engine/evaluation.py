
"""Evaluate Vision Engine findings against manually verified defects."""

from math import isfinite

from pydantic import BaseModel, Field

from vision_engine.models import BoundingBox, VisionFinding


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


def _calculate_iou(
    first: BoundingBox,
    second: BoundingBox,
) -> float:
    """Calculate Intersection over Union for two bounding boxes."""

    left = max(first.x, second.x)
    top = max(first.y, second.y)
    right = min(
        first.x + first.width,
        second.x + second.width,
    )
    bottom = min(
        first.y + first.height,
        second.y + second.height,
    )

    intersection_width = max(0.0, right - left)
    intersection_height = max(0.0, bottom - top)
    intersection_area = intersection_width * intersection_height

    first_area = first.width * first.height
    second_area = second.width * second.height

    union_area = first_area + second_area - intersection_area

    if union_area <= 0:
        return 0.0

    return intersection_area / union_area


def _match_score(
    expected: VisionFinding,
    detected: VisionFinding,
    iou_threshold: float,
) -> float | None:
    """Return a match score, or None when the findings do not match."""

    if expected.category != detected.category:
        return None

    # When both selectors exist, require an exact selector match.
    if expected.selector is not None and detected.selector is not None:
        if expected.selector == detected.selector:
            return 1.0
        return None

    # When both bounding boxes exist, compare their spatial overlap.
    if (
        expected.bounding_box is not None
        and detected.bounding_box is not None
    ):
        iou = _calculate_iou(
            expected.bounding_box,
            detected.bounding_box,
        )

        if iou >= iou_threshold:
            return iou

        return None

    # Category-only fallback is allowed only when neither finding
    # has selector or bounding-box evidence.
    if (
        expected.selector is None
        and detected.selector is None
        and expected.bounding_box is None
        and detected.bounding_box is None
    ):
        return 0.0

    return None


def evaluate_findings(
    expected_findings: list[VisionFinding],
    detected_findings: list[VisionFinding],
    iou_threshold: float = 0.5,
) -> EvaluationResult:
    """
    Compare detector output with manually verified expected findings.

    Matching uses category, selector, and bounding-box overlap.

    Each expected finding can match at most one detected finding.
    Each detected finding can match at most one expected finding.

    Matching uses maximum-cardinality assignment, prioritizing
    higher-scoring candidate matches.

    Precision and recall are set to 0 when their denominator is zero.
    """

    if (
        not isinstance(iou_threshold, (int, float))
        or not isfinite(iou_threshold)
        or not 0.0 <= iou_threshold <= 1.0
    ):
        raise ValueError("iou_threshold must be between 0.0 and 1.0.")

    expected_ids = [finding.finding_id for finding in expected_findings]
    detected_ids = [finding.finding_id for finding in detected_findings]

    if len(expected_ids) != len(set(expected_ids)):
        raise ValueError("Expected findings contain duplicate finding IDs.")

    if len(detected_ids) != len(set(detected_ids)):
        raise ValueError("Detected findings contain duplicate finding IDs.")

    # Build possible matches, prioritizing higher IoU scores.
    candidates: list[list[int]] = []

    for expected in expected_findings:
        scores = []

        for index, detected in enumerate(detected_findings):
            score = _match_score(expected, detected, iou_threshold)

            if score is not None:
                scores.append((index, score))

        scores.sort(key=lambda item: item[1], reverse=True)
        candidates.append([index for index, _ in scores])

    # Maximum-cardinality bipartite matching.
    # Reassignment allows an earlier match to move when that
    # gives another expected finding a valid match.
    detected_to_expected: dict[int, int] = {}

    def assign(expected_index: int, visited: set[int]) -> bool:
        for detected_index in candidates[expected_index]:
            if detected_index in visited:
                continue

            visited.add(detected_index)

            previous_expected = detected_to_expected.get(detected_index)

            if previous_expected is None or assign(
                previous_expected,
                visited,
            ):
                detected_to_expected[detected_index] = expected_index
                return True

        return False

    for expected_index in range(len(expected_findings)):
        assign(expected_index, set())

    expected_to_detected = {
        expected_index: detected_index
        for detected_index, expected_index in detected_to_expected.items()
    }

    true_positive_ids = []
    false_negative_ids = []

    for expected_index, expected in enumerate(expected_findings):
        detected_index = expected_to_detected.get(expected_index)

        if detected_index is None:
            false_negative_ids.append(expected.finding_id)
        else:
            true_positive_ids.append(
                detected_findings[detected_index].finding_id
            )

    matched_detected_indices = set(detected_to_expected)

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
