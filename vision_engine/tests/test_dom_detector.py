
"""Tests for the heuristic DOM detector."""

from vision_engine.detection.dom_detector import detect_dom_issues
from vision_engine.models import VisionInput


def test_clean_html_returns_no_findings(tmp_path):
    dom = tmp_path / "clean.html"
    dom.write_text(
        '<html><body><img src="logo.png" alt="Company logo">'
        '<label for="email">Email</label>'
        '<input id="email" type="email"></body></html>',
        encoding="utf-8",
    )
    data = VisionInput(
        run_id="clean-test",
        url="https://example.com",
        dom_snapshot_path=str(dom),
    )

    assert detect_dom_issues(data) == []


def test_image_without_src_is_reported(tmp_path):
    dom = tmp_path / "missing-src.html"
    dom.write_text('<html><body><img alt="Logo"></body></html>', encoding="utf-8")
    data = VisionInput(
        run_id="missing-src",
        url="https://example.com",
        dom_snapshot_path=str(dom),
    )

    findings = detect_dom_issues(data)

    assert any(
        finding.category == "broken_image"
        and "src" in finding.description
        for finding in findings
    )


def test_image_without_alt_is_reported(tmp_path):
    dom = tmp_path / "missing-alt.html"
    dom.write_text('<html><body><img src="logo.png"></body></html>', encoding="utf-8")
    data = VisionInput(
        run_id="missing-alt",
        url="https://example.com",
        dom_snapshot_path=str(dom),
    )

    findings = detect_dom_issues(data)

    assert any(
        finding.category == "missing_visible_element"
        and "alt" in finding.description
        for finding in findings
    )


def test_unlabelled_input_is_reported(tmp_path):
    dom = tmp_path / "unlabelled.html"
    dom.write_text('<html><body><input id="email"></body></html>', encoding="utf-8")
    data = VisionInput(
        run_id="unlabelled",
        url="https://example.com",
        dom_snapshot_path=str(dom),
    )

    findings = detect_dom_issues(data)

    assert any("accessible label" in finding.description for finding in findings)


def test_missing_dom_path_is_rejected():
    data = VisionInput(
        run_id="no-dom",
        url="https://example.com",
        screenshot_path="screenshot.png",
    )

    try:
        detect_dom_issues(data)
    except ValueError as exc:
        assert "DOM snapshot path is required" in str(exc)
    else:
        raise AssertionError("Expected a ValueError when DOM path is missing")


def test_empty_dom_snapshot_is_rejected(tmp_path):
    dom = tmp_path / "empty.html"
    dom.write_text("", encoding="utf-8")
    data = VisionInput(
        run_id="empty-dom",
        url="https://example.com",
        dom_snapshot_path=str(dom),
    )

    try:
        detect_dom_issues(data)
    except ValueError as exc:
        assert "empty" in str(exc).lower()
    else:
        raise AssertionError("Expected a ValueError for an empty DOM snapshot")


def test_findings_preserve_evidence_and_have_unique_ids(tmp_path):
    dom = tmp_path / "issues.html"
    dom.write_text(
        '<html><body><img src=""><input id="email"></body></html>',
        encoding="utf-8",
    )
    data = VisionInput(
        run_id="evidence-test",
        url="https://example.com",
        dom_snapshot_path=str(dom),
    )

    findings = detect_dom_issues(data)

    assert len(findings) >= 2
    assert len({finding.finding_id for finding in findings}) == len(findings)

    for finding in findings:
        assert finding.evidence.dom_snapshot_path == str(dom)
        assert finding.finding_id.startswith("evidence-test-dom-")
        assert finding.source == "mock"



def test_label_after_input_is_recognized(tmp_path):
    dom = tmp_path / "label-after.html"
    dom.write_text(
        '<html><body><input id="email">'
        '<label for="email">Email address</label></body></html>',
        encoding="utf-8",
    )
    data = VisionInput(
        run_id="label-after",
        url="https://example.com",
        dom_snapshot_path=str(dom),
    )

    findings = detect_dom_issues(data)

    assert not any("accessible label" in f.description for f in findings)


def test_aria_label_is_recognized(tmp_path):
    dom = tmp_path / "aria-label.html"
    dom.write_text(
        '<html><body><input aria-label="Search"></body></html>',
        encoding="utf-8",
    )
    data = VisionInput(
        run_id="aria-label",
        url="https://example.com",
        dom_snapshot_path=str(dom),
    )

    findings = detect_dom_issues(data)

    assert not any("accessible label" in f.description for f in findings)


def test_hidden_input_does_not_require_label(tmp_path):
    dom = tmp_path / "hidden-input.html"
    dom.write_text(
        '<html><body><input type="hidden" name="token"></body></html>',
        encoding="utf-8",
    )
    data = VisionInput(
        run_id="hidden-input",
        url="https://example.com",
        dom_snapshot_path=str(dom),
    )

    findings = detect_dom_issues(data)

    assert not any("accessible label" in f.description for f in findings)


def test_unlabelled_select_is_reported(tmp_path):
    dom = tmp_path / "unlabelled-select.html"
    dom.write_text(
        '<html><body><select id="country"><option>India</option>'
        '</select></body></html>',
        encoding="utf-8",
    )
    data = VisionInput(
        run_id="unlabelled-select",
        url="https://example.com",
        dom_snapshot_path=str(dom),
    )

    findings = detect_dom_issues(data)

    assert any(
        "accessible label" in f.description and f.selector == "#country"
        for f in findings
    )
