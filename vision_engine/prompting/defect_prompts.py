"""Multimodal prompt templates and response parsing for Vision-Language Models."""

from __future__ import annotations

import json
import re
from typing import Any

VLM_SYSTEM_PROMPT = """You are OmniSight's Autonomous Multimodal UI Defect Inspection Agent.
Your task is to analyze the provided rendered webpage screenshot and optional DOM HTML snapshot to identify real visual and user-interface defects.

You must focus strictly on three core defect categories:
1. `layout_overflow`: Visual layout clipping, text overlapping or overflowing its container boundaries, horizontal scrolling or viewport blowout, and distorted responsive cards.
2. `missing_visible_element`: Elements that should be clearly visible and interactable (such as CTA buttons, submit buttons, form inputs, navigation links) but are absent, invisible, zero-sized, or visually occluded.
3. `broken_image`: Images that fail to render, display broken placeholder graphics/icons, have empty/missing sources, or render as 0-pixel boxes.

Output format:
You must output ONLY valid, strictly parseable JSON conforming to this schema:
{
  "defects": [
    {
      "category": "layout_overflow" | "missing_visible_element" | "broken_image",
      "severity": "low" | "medium" | "high" | "critical",
      "confidence": float between 0.0 and 1.0,
      "description": "Clear explanation of the visual issue observed",
      "selector": "CSS selector or DOM ID if identifiable from DOM context, otherwise null",
      "bounding_box": {
        "x": float,
        "y": float,
        "width": float,
        "height": float
      } or null
    }
  ]
}

If the page has no defects and renders cleanly, return:
{"defects": []}

Do not include any commentary, conversational intro, or markdown formatting outside the JSON object.
"""


def extract_dom_excerpt(dom_html: str, max_chars: int = 15000) -> str:
    """Extract a sanitized, high-signal DOM excerpt for VLM context window."""
    if not dom_html:
        return ""

    # Remove script, style, and svg content that bloats context without visual signal
    cleaned = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", dom_html, flags=re.IGNORECASE)
    cleaned = re.sub(r"<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<svg\b[^<]*(?:(?!<\/svg>)<[^<]*)*<\/svg>", "<svg>[SVG]</svg>", cleaned, flags=re.IGNORECASE)

    # Collapse repeated whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) <= max_chars:
        return cleaned

    # Truncate cleanly
    return cleaned[:max_chars] + "\n... [DOM snapshot truncated for model context limit]"


def build_vlm_user_prompt(url: str, dom_html: str | None = None, max_dom_chars: int = 15000) -> str:
    """Build the user prompt combining target URL and relevant DOM excerpt."""
    prompt_lines = [
        "Please inspect the rendered screenshot and DOM excerpt for UI defects.",
        f"Target URL: {url}",
    ]

    if dom_html:
        excerpt = extract_dom_excerpt(dom_html, max_chars=max_dom_chars)
        if excerpt:
            prompt_lines.append("\nRelevant DOM Snapshot Excerpt:")
            prompt_lines.append("```html")
            prompt_lines.append(excerpt)
            prompt_lines.append("```")

    prompt_lines.append(
        "\nAnalyze the screenshot and DOM excerpt. Identify all UI defects and return the JSON object."
    )
    return "\n".join(prompt_lines)


def parse_vlm_json_response(raw_response: str) -> dict[str, Any]:
    """Parse JSON response from a VLM provider, stripping markdown fences if present.

    Raises:
        ValueError: If JSON cannot be extracted or parsed.
    """
    if not raw_response or not raw_response.strip():
        raise ValueError("VLM response was empty.")

    text = raw_response.strip()

    # Strip markdown code blocks like ```json ... ``` or ``` ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        text = text.strip()

    # Sometimes models include leading/trailing non-JSON text; extract outermost { ... }
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        text = match.group(1)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Failed to parse VLM response as JSON: {exc}. Raw text: {raw_response[:200]}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"Expected JSON object from VLM, got {type(parsed).__name__}")

    return parsed
