"""Parse and validate structured responses from a future VLM."""

import json

from pydantic import ValidationError

from vision_engine.models import VisionFinding


def _reject_duplicate_json_keys(pairs: list[tuple[str, object]]) -> dict:
    """Build a dictionary while rejecting duplicate JSON object keys."""
    result = {}

    for key, value in pairs:
        if key in result:
            raise ValueError(
                f"VLM response contains duplicate JSON key '{key}'."
            )

        result[key] = value

    return result


def parse_vlm_response(response: str) -> list[VisionFinding]:
    """Parse a JSON array and validate every VLM finding.

    Raises:
        ValueError: If the response is invalid JSON, contains duplicate
            JSON keys, is not a JSON array, contains malformed findings,
            contains duplicate finding IDs, or contains findings not
            marked as originating from a VLM.
    """
    try:
        data = json.loads(
            response,
            object_pairs_hook=_reject_duplicate_json_keys,
        )
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("VLM response must contain valid JSON.") from exc

    if not isinstance(data, list):
        raise ValueError("VLM response must be a JSON array.")

    findings: list[VisionFinding] = []
    seen_finding_ids: set[str] = set()

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

        if finding.finding_id in seen_finding_ids:
            raise ValueError(
                f"Duplicate finding_id '{finding.finding_id}' "
                f"at index {index}."
            )

        seen_finding_ids.add(finding.finding_id)
        findings.append(finding)

    return findings