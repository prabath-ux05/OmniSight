"""Multimodal prompting strategies, system templates, and vision reasoning."""

from vision_engine.prompting.defect_prompts import (
    VLM_SYSTEM_PROMPT,
    build_vlm_user_prompt,
    extract_dom_excerpt,
    parse_vlm_json_response,
)

__all__ = [
    "VLM_SYSTEM_PROMPT",
    "build_vlm_user_prompt",
    "extract_dom_excerpt",
    "parse_vlm_json_response",
]
