
"""Tests for Vision Engine evidence validation."""

from pathlib import Path

from vision_engine.evidence_validator import validate_evidence
from vision_engine.models import VisionInput


def test_valid_screenshot_passes(tmp_path):
    screenshot = tmp_path / "screenshot.png"
    screenshot.write_bytes(b"fake image data")

    input_data = VisionInput(
        run_id="test-001",
        url="https://example.com",
        screenshot_path=str(screenshot),
    )

    assert validate_evidence(input_data) == []


def test_valid_dom_snapshot_passes(tmp_path):
    dom_snapshot = tmp_path / "page.html"
    dom_snapshot.write_text("<html></html>", encoding="utf-8")

    input_data = VisionInput(
        run_id="test-002",
        url="https://example.com",
        dom_snapshot_path=str(dom_snapshot),
    )

    assert validate_evidence(input_data) == []


def test_missing_screenshot_is_reported(tmp_path):
    screenshot = tmp_path / "missing.png"

    input_data = VisionInput(
        run_id="test-003",
        url="https://example.com",
        screenshot_path=str(screenshot),
    )

    errors = validate_evidence(input_data)

    assert any("does not exist" in error for error in errors)
    assert any("No usable evidence" in error for error in errors)


def test_directory_is_not_accepted_as_evidence(tmp_path):
    directory = tmp_path / "screenshots"
    directory.mkdir()

    input_data = VisionInput(
        run_id="test-004",
        url="https://example.com",
        screenshot_path=str(directory),
    )

    errors = validate_evidence(input_data)

    assert any("not a file" in error for error in errors)


def test_invalid_screenshot_does_not_invalidate_valid_dom(tmp_path):
    screenshot = tmp_path / "missing.png"
    dom_snapshot = tmp_path / "page.html"
    dom_snapshot.write_text("<html></html>", encoding="utf-8")

    input_data = VisionInput(
        run_id="test-005",
        url="https://example.com",
        screenshot_path=str(screenshot),
        dom_snapshot_path=str(dom_snapshot),
    )

    errors = validate_evidence(input_data)

    assert len(errors) == 1
    assert "screenshot file does not exist" in errors[0]


def test_mock_detector_still_returns_findings(tmp_path):
    from vision_engine.detection.mock_detector import detect_mock

    screenshot = tmp_path / "screenshot.png"
    screenshot.write_bytes(b"fake image data")

    input_data = VisionInput(
        run_id="test-006",
        url="https://example.com",
        screenshot_path=str(screenshot),
    )

    findings = detect_mock(input_data)

    assert len(findings) == 2
    assert all(finding.source == "mock" for finding in findings)


def test_both_evidence_files_missing_are_reported(tmp_path):
    input_data = VisionInput(
        run_id="test-007",
        url="https://example.com",
        screenshot_path=str(tmp_path / "missing.png"),
        dom_snapshot_path=str(tmp_path / "missing.html"),
    )

    errors = validate_evidence(input_data)

    assert any("screenshot file does not exist" in error for error in errors)
    assert any("DOM snapshot file does not exist" in error for error in errors)
    assert any("No usable evidence files" in error for error in errors)


def test_valid_screenshot_with_missing_dom_passes_partially(tmp_path):
    screenshot = tmp_path / "screenshot.png"
    screenshot.write_bytes(b"fake image data")

    input_data = VisionInput(
        run_id="test-008",
        url="https://example.com",
        screenshot_path=str(screenshot),
        dom_snapshot_path=str(tmp_path / "missing.html"),
    )

    errors = validate_evidence(input_data)

    assert len(errors) == 1
    assert "DOM snapshot file does not exist" in errors[0]


def test_unreadable_screenshot_is_reported(tmp_path, monkeypatch):
    screenshot = tmp_path / "screenshot.png"
    screenshot.write_bytes(b"fake image data")

    original_open = Path.open

    def raise_permission_error(self, *args, **kwargs):
        if self == screenshot:
            raise PermissionError("Permission denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", raise_permission_error)

    input_data = VisionInput(
        run_id="test-run",
        url="https://example.com",
        screenshot_path=str(screenshot),
    )

    errors = validate_evidence(input_data)

    assert any("screenshot file cannot be read" in error for error in errors)
    assert "No usable evidence files were found." in errors


def test_empty_screenshot_is_rejected(tmp_path):
    screenshot = tmp_path / "empty.png"
    screenshot.write_bytes(b"")

    input_data = VisionInput(
        run_id="test-empty-screenshot",
        url="https://example.com",
        screenshot_path=str(screenshot),
    )

    errors = validate_evidence(input_data)

    assert any("screenshot file is empty" in error for error in errors)
    assert "No usable evidence files were found." in errors


def test_empty_screenshot_with_valid_dom_is_partially_usable(tmp_path):
    screenshot = tmp_path / "empty.png"
    screenshot.write_bytes(b"")

    dom_snapshot = tmp_path / "snapshot.html"
    dom_snapshot.write_text(
        "<html><body>Example page</body></html>",
        encoding="utf-8",
    )

    input_data = VisionInput(
        run_id="test-empty-screenshot-valid-dom",
        url="https://example.com",
        screenshot_path=str(screenshot),
        dom_snapshot_path=str(dom_snapshot),
    )

    errors = validate_evidence(input_data)

    assert any("screenshot file is empty" in error for error in errors)
    assert "No usable evidence files were found." not in errors


def test_empty_dom_snapshot_is_rejected(tmp_path):
    dom_snapshot = tmp_path / "empty.html"
    dom_snapshot.write_text("", encoding="utf-8")

    input_data = VisionInput(
        run_id="test-empty-dom",
        url="https://example.com",
        dom_snapshot_path=str(dom_snapshot),
    )

    errors = validate_evidence(input_data)

    assert any("DOM snapshot file is empty" in error for error in errors)
    assert "No usable evidence files were found." in errors


def test_unreadable_dom_snapshot_is_reported(tmp_path, monkeypatch):
    dom_snapshot = tmp_path / "page.html"
    dom_snapshot.write_text("<html></html>", encoding="utf-8")

    original_open = Path.open

    def raise_permission_error(self, *args, **kwargs):
        if self == dom_snapshot:
            raise PermissionError("Permission denied")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", raise_permission_error)

    input_data = VisionInput(
        run_id="test-unreadable-dom",
        url="https://example.com",
        dom_snapshot_path=str(dom_snapshot),
    )

    errors = validate_evidence(input_data)

    assert any(
        "DOM snapshot file cannot be read" in error for error in errors
    )
    assert "No usable evidence files were found." in errors


def test_empty_dom_with_valid_screenshot_is_partially_usable(tmp_path):
    screenshot = tmp_path / "screenshot.png"
    screenshot.write_bytes(b"fake image data")

    dom_snapshot = tmp_path / "empty.html"
    dom_snapshot.write_text("", encoding="utf-8")

    input_data = VisionInput(
        run_id="test-empty-dom-valid-screenshot",
        url="https://example.com",
        screenshot_path=str(screenshot),
        dom_snapshot_path=str(dom_snapshot),
    )

    errors = validate_evidence(input_data)

    assert any("DOM snapshot file is empty" in error for error in errors)
    assert "No usable evidence files were found." not in errors
