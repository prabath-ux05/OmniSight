"""Parse and validate structured responses from a future VLM."""

import json

from pydantic import ValidationError

from vision_engine.models import VisionFinding


def parse_vlm_response(response: str) -> list[VisionFinding]:
    """Parse a JSON array and validate every VLM finding.

    Raises:
        ValueError: If the response is invalid JSON, is not a JSON array,
            contains malformed findings, or contains findings not marked
            as originating from a VLM.
    """
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("VLM response must contain valid JSON.") from exc

    if not isinstance(data, list):
        raise ValueError("VLM response must be a JSON array.")

    findings: list[VisionFinding] = []

    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(
                f"Finding at index {index} must be a JSON object."
            )

        if item.get("source") != "vlm":
            raise ValueError(
                f"Finding at index {index} must have source='vlm'."
            )

        try:
            finding = VisionFinding.model_validate(item)
        except ValidationError as exc:
            raise ValueError(
                f"Finding at index {index} failed schema validation: {exc}"
            ) from exc

        findings.append(finding)

    return findings