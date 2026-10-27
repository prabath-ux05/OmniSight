"""Tests for future VLM prompt construction."""

import json

from vision_engine.models import VisionInput
from vision_engine.prompting.vlm_prompt import build_vlm_prompt


def test_prompt_includes_run_metadata_and_supported_categories():
    input_data = VisionInput(
        run_id="run-001",
        url="https://example.com",
        screenshot_path="evidence/screenshot.png",
    )

    prompt = build_vlm_prompt(input_data)

    assert "run-001" in prompt
    assert "https://example.com" in prompt
    assert "layout_overflow" in prompt
    assert "missing_visible_element" in prompt
    assert "broken_image" in prompt
    assert '"source"' in prompt
    assert '"vlm"' in prompt


def test_prompt_marks_available_evidence_correctly():
    input_data = VisionInput(
        run_id="run-002",
        url="https://example.com/form",
        dom_snapshot_path="evidence/page.html",
    )

    prompt = build_vlm_prompt(input_data)
    metadata_text = prompt.split("Evidence metadata:\n", 1)[1].split(
        "\n\nImportant limitations:", 1
    )[0]
    metadata = json.loads(metadata_text)

    assert metadata["screenshot_available"] is False
    assert metadata["dom_snapshot_available"] is True
    assert metadata["run_id"] == "run-002"


def test_prompt_warns_against_inventing_findings():
    input_data = VisionInput(
        run_id="run-003",
        url="https://example.com",
        screenshot_path="screenshot.png",
        dom_snapshot_path="page.html",
    )

    prompt = build_vlm_prompt(input_data)

    assert "Do not invent defects" in prompt
    assert "Return an empty array []" in prompt
    assert "does not load evidence" in build_vlm_prompt.__doc__
    assert "call a model, or perform inference" in build_vlm_prompt.__doc__