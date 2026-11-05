"""Tests for before-and-after visual repair verification."""

from vision_engine.models import (
    EvidenceReferences,
    VisionFinding,
    VisionInput,
)
from vision_engine.verification import verify_repair


def create_finding(
    finding_id="finding-1",
    category="layout_overflow",
    severity="high",
    selector="#main",
):
    return VisionFinding(
        finding_id=finding_id,
        category=category,
        severity=severity,
        confidence=0.95,
        description="UI layout defect detected",
        selector=selector,
        evidence=EvidenceReferences(
            screenshot_path="before.png",
            dom_snapshot_path="before.html",
        ),
        source="vlm",
    )


def create_input(run_id, screenshot_path):
    return VisionInput(
        run_id=run_id,
        url="https://example.com",
        screenshot_path=str(screenshot_path),
    )


def test_repair_is_resolved_when_no_matching_finding_remains(tmp_path):
    before_file = tmp_path / "before.png"
    after_file = tmp_path / "after.png"
    before_file.write_bytes(b"before screenshot")
    after_file.write_bytes(b"after screenshot")

    original = create_finding()
    before_input = create_input("before-run", before_file)
    after_input = create_input("after-run", after_file)

    result = verify_repair(
        original,
        before_input,
        after_input,
        [],
    )

    assert result.status == "resolved"
    assert result.run_id == "after-run"
    assert result.original_finding_id == "finding-1"
    assert result.matched_finding_ids == []


def test_repair_is_partially_resolved_when_severity_decreases(tmp_path):
    before_file = tmp_path / "before.png"
    after_file = tmp_path / "after.png"
    before_file.write_bytes(b"before screenshot")
    after_file.write_bytes(b"after screenshot")

    original = create_finding(severity="high")
    remaining = create_finding(
        finding_id="finding-2",
        severity="medium",
    )

    result = verify_repair(
        original,
        create_input("before-run", before_file),
        create_input("after-run", after_file),
        [remaining],
    )

    assert result.status == "partially_resolved"
    assert result.matched_finding_ids == ["finding-2"]


def test_repair_is_unresolved_when_same_severity_remains(tmp_path):
    before_file = tmp_path / "before.png"
    after_file = tmp_path / "after.png"
    before_file.write_bytes(b"before screenshot")
    after_file.write_bytes(b"after screenshot")

    original = create_finding(severity="high")
    remaining = create_finding(
        finding_id="finding-2",
        severity="high",
    )

    result = verify_repair(
        original,
        create_input("before-run", before_file),
        create_input("after-run", after_file),
        [remaining],
    )

    assert result.status == "unresolved"
    assert result.matched_finding_ids == ["finding-2"]


def test_different_selector_is_not_matched(tmp_path):
    before_file = tmp_path / "before.png"
    after_file = tmp_path / "after.png"
    before_file.write_bytes(b"before screenshot")
    after_file.write_bytes(b"after screenshot")

    original = create_finding(selector="#main")
    unrelated = create_finding(
        finding_id="finding-2",
        selector="#footer",
    )

    result = verify_repair(
        original,
        create_input("before-run", before_file),
        create_input("after-run", after_file),
        [unrelated],
    )

    assert result.status == "resolved"
    assert result.matched_finding_ids == []


def test_repair_is_unverifiable_when_after_evidence_is_missing(tmp_path):
    before_file = tmp_path / "before.png"
    before_file.write_bytes(b"before screenshot")

    missing_after_file = tmp_path / "missing-after.png"

    original = create_finding()

    result = verify_repair(
        original,
        create_input("before-run", before_file),
        create_input("after-run", missing_after_file),
        [],
    )

    assert result.status == "unverifiable"
    assert result.before_evidence is True
    assert result.after_evidence is False


def test_repair_is_unresolved_when_any_matching_finding_keeps_high_severity(
    tmp_path,
):
    before_file = tmp_path / "before.png"
    after_file = tmp_path / "after.png"
    before_file.write_bytes(b"before screenshot")
    after_file.write_bytes(b"after screenshot")

    original = create_finding(severity="high")

    reduced = create_finding(
        finding_id="finding-2",
        severity="medium",
    )
    unchanged = create_finding(
        finding_id="finding-3",
        severity="high",
    )

    result = verify_repair(
        original,
        create_input("before-run", before_file),
        create_input("after-run", after_file),
        [reduced, unchanged],
    )

    assert result.status == "unresolved"
    assert result.matched_finding_ids == ["finding-2", "finding-3"]