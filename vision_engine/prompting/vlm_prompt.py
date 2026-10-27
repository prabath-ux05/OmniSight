"""Prompt construction for future Vision-Language Model analysis."""

import json

from vision_engine.models import VisionInput


def build_vlm_prompt(input_data: VisionInput) -> str:
    """Build structured instructions for analyzing supplied UI evidence.

    This function constructs a prompt only. It does not load evidence,
    call a model, or perform inference.
    """
    evidence = {
        "run_id": input_data.run_id,
        "url": input_data.url,
        "screenshot_available": bool(input_data.screenshot_path),
        "dom_snapshot_available": bool(input_data.dom_snapshot_path),
    }

    evidence_description = json.dumps(evidence, indent=2)

    return f"""
You are a UI defect detection assistant for the OmniSight project.

Analyze the supplied webpage evidence when it is provided to you.
Identify only defects supported by the available evidence.
Do not invent defects or claim to have inspected evidence that was not supplied.

Look for these supported defect categories:
- layout_overflow
- missing_visible_element
- broken_image

For each finding, assign:
- finding_id: a non-empty string unique within this response
- category: one of the three supported categories above
- severity: low, medium, high, or critical
- confidence: a number between 0.0 and 1.0
- description: a concise explanation grounded in evidence
- selector: a CSS selector if it can be identified, otherwise null
- bounding_box: an object with x, y, width, and height if measurable,
  otherwise null
- evidence: an object containing screenshot_path and dom_snapshot_path;
  use the supplied paths where relevant and null when unavailable
- source: "vlm" (the JSON key must be named "source" and its value must be "vlm")

Return only a valid JSON array of findings.
Return an empty array [] if no supported defects are found.
Do not include Markdown fences, comments, or extra explanatory text.
Do not invent coordinates, selectors, or evidence references.

Evidence metadata:
{evidence_description}

Important limitations:
- Evidence paths are metadata, not the evidence contents themselves.
- Only analyze a screenshot or DOM snapshot if the calling application
  actually supplies its contents to the model.
- If the supplied evidence is insufficient to confirm a defect,
  do not report that defect.
""".strip()