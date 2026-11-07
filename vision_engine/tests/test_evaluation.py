"""Tests for Vision Engine detection evaluation."""

import pytest

from vision_engine.evaluation import evaluate_findings
from vision_engine.models import EvidenceReferences, VisionFinding


def create_finding(finding_id, category="layout_overflow", selector="#main"):
    return VisionFinding(
        finding_id=finding_id,
        category=category,
        severity="high",
        confidence=0.95,
        description="UI defect detected",
        selector=selector,
        evidence=EvidenceReferences(
            screenshot_path="screenshot.png",
        ),
        source="vlm",
    )


def test_evaluation_counts_true_positives():
    expected = [create_finding("expected-1")]
    detected = [create_finding("detected-1")]

    result = evaluate_findings(expected, detected)

    assert result.true_positive_count == 1
    assert result.false_positive_count == 0
    assert result.false_negative_count == 0
    assert result.precision == 1.0
    assert result.recall == 1.0
    assert result.f1_score == 1.0


def test_evaluation_identifies_false_positive():
    expected = [create_finding("expected-1")]
    detected = [
        create_finding("detected-1"),
        create_finding("detected-2", category="broken_image"),
    ]

    result = evaluate_findings(expected, detected)

    assert result.true_positive_count == 1
    assert result.false_positive_ids == ["detected-2"]
    assert result.false_negative_count == 0
    assert result.precision == 0.5
    assert result.recall == 1.0


def test_evaluation_identifies_missed_defect():
    expected = [
        create_finding("expected-1"),
        create_finding("expected-2", category="broken_image"),
    ]
    detected = [create_finding("detected-1")]

    result = evaluate_findings(expected, detected)

    assert result.true_positive_count == 1
    assert result.false_positive_count == 0
    assert result.false_negative_ids == ["expected-2"]
    assert result.precision == 1.0
    assert result.recall == 0.5


def test_evaluation_calculates_f1_score():
    expected = [
        create_finding("expected-1"),
        create_finding("expected-2"),
    ]
    detected = [
        create_finding("detected-1"),
        create_finding("detected-2"),
        create_finding("detected-3", category="broken_image"),
    ]

    result = evaluate_findings(expected, detected)

    assert result.true_positive_count == 2
    assert result.false_positive_count == 1
    assert result.false_negative_count == 0
    assert result.precision == pytest.approx(2 / 3)
    assert result.recall == 1.0
    assert result.f1_score == pytest.approx(0.8)


def test_evaluation_does_not_match_different_selectors():
    expected = [create_finding("expected-1", selector="#header")]
    detected = [create_finding("detected-1", selector="#footer")]

    result = evaluate_findings(expected, detected)

    assert result.true_positive_count == 0
    assert result.false_positive_ids == ["detected-1"]
    assert result.false_negative_ids == ["expected-1"]


def test_evaluation_rejects_duplicate_expected_ids():
    expected = [
        create_finding("duplicate"),
        create_finding("duplicate"),
    ]

    with pytest.raises(ValueError, match="duplicate finding IDs"):
        evaluate_findings(expected, [])


def test_evaluation_rejects_duplicate_detected_ids():
    detected = [
        create_finding("duplicate"),
        create_finding("duplicate"),
    ]

    with pytest.raises(ValueError, match="duplicate finding IDs"):
        evaluate_findings([], detected)


def test_evaluation_handles_empty_inputs():
    result = evaluate_findings([], [])

    assert result.true_positive_count == 0
    assert result.false_positive_count == 0
    assert result.false_negative_count == 0
    assert result.precision == 0.0
    assert result.recall == 0.0
    assert result.f1_score == 0.0