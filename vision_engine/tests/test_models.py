"""Tests for Vision Engine data models."""

import pytest
from pydantic import ValidationError

from vision_engine.models import BoundingBox, VisionInput


def test_vision_input_accepts_multiple_crop_boxes():
    boxes = [
        BoundingBox(x=10, y=20, width=100, height=80),
        BoundingBox(x=200, y=150, width=120, height=90),
    ]

    result = VisionInput(
        run_id="test-run",
        url="https://example.com",
        screenshot_path="screenshot.png",
        crop_boxes=boxes,
    )

    assert result.crop_boxes == boxes
    assert result.crop_box is None


def test_vision_input_rejects_empty_crop_boxes():
    with pytest.raises(ValidationError):
        VisionInput(
            run_id="test-run",
            url="https://example.com",
            screenshot_path="screenshot.png",
            crop_boxes=[],
        )


def test_vision_input_rejects_crop_boxes_without_screenshot():
    with pytest.raises(ValidationError, match="Crop boxes require a screenshot path"):
        VisionInput(
            run_id="test-run",
            url="https://example.com",
            dom_snapshot_path="page.html",
            crop_boxes=[
                BoundingBox(x=10, y=20, width=100, height=80)
            ],
        )


def test_vision_input_rejects_both_crop_box_fields():
    box = BoundingBox(x=10, y=20, width=100, height=80)

    with pytest.raises(ValidationError, match="Use either crop_box or crop_boxes"):
        VisionInput(
            run_id="test-run",
            url="https://example.com",
            screenshot_path="screenshot.png",
            crop_box=box,
            crop_boxes=[box],
        )


def test_vision_input_still_accepts_single_crop_box():
    box = BoundingBox(x=10, y=20, width=100, height=80)

    result = VisionInput(
        run_id="test-run",
        url="https://example.com",
        screenshot_path="screenshot.png",
        crop_box=box,
    )

    assert result.crop_box == box
    assert result.crop_boxes is None