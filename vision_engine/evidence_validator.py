"""Validate evidence files supplied to the Vision Engine."""

from pathlib import Path

from vision_engine.models import VisionInput


def validate_evidence(input_data: VisionInput) -> list[str]:
    """
    Validate the evidence files referenced by a VisionInput.

    Returns a list of validation errors.
    An empty list means all supplied evidence paths are valid and readable.
    At least one evidence file must be usable.
    """

    errors: list[str] = []
    usable_evidence = 0

    evidence_paths = {
        "screenshot": input_data.screenshot_path,
        "DOM snapshot": input_data.dom_snapshot_path,
    }

    for evidence_name, raw_path in evidence_paths.items():
        if raw_path is None:
            continue

        path = Path(raw_path)

        if not path.exists():
            errors.append(
                f"{evidence_name} file does not exist: {raw_path}"
            )
            continue

        if not path.is_file():
            errors.append(
                f"{evidence_name} path is not a file: {raw_path}"
            )
            continue

        try:
            with path.open("rb") as evidence_file:
                if not evidence_file.read(1):
                    errors.append(f"{evidence_name} file is empty: {raw_path}")
                    continue
        except OSError:
            errors.append(f"{evidence_name} file cannot be read: {raw_path}")
            continue

        usable_evidence += 1

    if usable_evidence == 0 and not errors:
        errors.append("No evidence files were supplied.")

    if usable_evidence == 0 and errors:
        errors.append("No usable evidence files were found.")

    return errors