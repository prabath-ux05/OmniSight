"""Tests for VLM response parsing and validation."""

import json

import pytest

from vision_engine.detection.vlm_response_parser import parse_vlm_response
from vision_engine.models import VisionFinding


def make_valid_finding() -> dict:
    """Return a valid example matching the existing finding schema."""
    return {
        "finding_id": "finding-001",
        "category": "broken_image",
        "severity": "high",
        "confidence": 0.95,
        "description": "An image appears to be broken.",
        "selector": "img.hero",
        "bounding_box": {
            "x": 10,
            "y": 20,
            "width": 100,
            "height": 80,
        },
        "evidence": {
            "screenshot_path": "evidence/screenshot.png",
            "dom_snapshot_path": "evidence/page.html",
        },
        "source": "vlm",
    }


def test_parse_valid_finding():
    response = json.dumps([make_valid_finding()])

    findings = parse_vlm_response(response)

    assert len(findings) == 1
    assert isinstance(findings[0], VisionFinding)
    assert findings[0].finding_id == "finding-001"
    assert findings[0].category == "broken_image"
    assert findings[0].source == "vlm"


def test_parse_empty_array():
    assert parse_vlm_response("[]") == []


def test_reject_invalid_json():
    with pytest.raises(ValueError, match="valid JSON"):
        parse_vlm_response("not json")


def test_reject_non_array_response():
    with pytest.raises(ValueError, match="JSON array"):
        parse_vlm_response(json.dumps(make_valid_finding()))


def test_reject_unsupported_category():
    finding = make_valid_finding()
    finding["category"] = "unknown_defect"

    with pytest.raises(ValueError, match="schema validation"):
        parse_vlm_response(json.dumps([finding]))


def test_reject_confidence_outside_allowed_range():
    finding = make_valid_finding()
    finding["confidence"] = 1.5

    with pytest.raises(ValueError, match="schema validation"):
        parse_vlm_response(json.dumps([finding]))


def test_reject_finding_with_wrong_source():
    finding = make_valid_finding()
    finding["source"] = "mock"

    with pytest.raises(ValueError, match="source='vlm'"):
        parse_vlm_response(json.dumps([finding]))


def test_reject_non_object_finding():
    with pytest.raises(ValueError, match="JSON object"):
        parse_vlm_response(json.dumps(["not a finding"]))


def test_reject_duplicate_finding_ids():
    first_finding = make_valid_finding()
    second_finding = make_valid_finding()

    second_finding["category"] = "layout_overflow"
    second_finding["description"] = "A layout overflow was detected."

    response = json.dumps([first_finding, second_finding])

    with pytest.raises(ValueError, match="Duplicate finding_id"):
        parse_vlm_response(response)


def test_accept_findings_with_unique_ids():
    first_finding = make_valid_finding()
    second_finding = make_valid_finding()

    second_finding["finding_id"] = "finding-002"
    second_finding["category"] = "layout_overflow"

    response = json.dumps([first_finding, second_finding])

    findings = parse_vlm_response(response)

    assert len(findings) == 2
    assert findings[0].finding_id == "finding-001"
    assert findings[1].finding_id == "finding-002"