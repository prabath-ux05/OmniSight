"""Safe, non-destructive patch generation for verified self-healing locator repairs.

Safety constraints:
- Path traversal (e.g. '../', absolute system paths) is strictly blocked.
- Changes are restricted to the explicitly provided target workspace.
- Modification of OmniSight's own internal architecture files is rejected.
- Target files must exist and contain the original selector; never guesses code.
- Generates standard, minimal unified diffs for reviewable inspection.
"""

from __future__ import annotations

import difflib
import os
from pathlib import Path
from typing import Optional

from self_healing.models import PatchResult


class PatchSecurityError(ValueError):
    """Raised when a patch path violates security constraints or workspace boundaries."""


FORBIDDEN_INTERNAL_DIRS: frozenset[str] = frozenset({
    "backend",
    "frontend",
    "vision_engine",
    "self_healing",
    "github_integration",
    "integration",
    "browser_agent",
})


def validate_target_path(
    target_file: str,
    workspace_root: Optional[str] = None,
    allow_internal: bool = False,
) -> Path:
    """Validate and resolve a target file path against security rules.

    Args:
        target_file: The relative or absolute path to the target test/code file.
        workspace_root: Optional workspace boundary directory (defaults to current working directory).
        allow_internal: If True, bypasses internal directory protection (only for test fixtures).

    Returns:
        Resolved absolute Path.

    Raises:
        PatchSecurityError: If the path traverses outside workspace or targets OmniSight internals.
    """
    if not target_file or not target_file.strip():
        raise PatchSecurityError("Target file path cannot be empty or whitespace.")

    clean_target = target_file.strip().replace("\\", "/")
    root_path = Path(workspace_root or os.getcwd()).resolve()

    # Block obvious traversal strings
    parts = clean_target.split("/")
    if ".." in parts:
        raise PatchSecurityError(f"Path traversal ('..') is prohibited: '{target_file}'")

    target_path = Path(clean_target)
    if not target_path.is_absolute():
        resolved_path = (root_path / target_path).resolve()
    else:
        resolved_path = target_path.resolve()

    # Boundary check: resolved path must reside within root_path
    try:
        rel_to_root = resolved_path.relative_to(root_path)
    except ValueError as exc:
        raise PatchSecurityError(
            f"Target file '{target_file}' resolves outside the allowed workspace '{root_path}'."
        ) from exc

    # Self-modification protection: reject edits to OmniSight internal source directories
    if not allow_internal and rel_to_root.parts:
        top_dir = rel_to_root.parts[0].lower()
        if top_dir in FORBIDDEN_INTERNAL_DIRS:
            raise PatchSecurityError(
                f"Refusing to generate patch targeting OmniSight internal module '{top_dir}'."
            )

    return resolved_path


def generate_locator_patch(
    original_selector: str,
    proposed_locator: str,
    target_file: str,
    workspace_root: Optional[str] = None,
    allow_internal: bool = False,
) -> PatchResult:
    """Generate a minimal, safe unified diff replacing a broken locator.

    Args:
        original_selector: The broken locator string targeted for replacement.
        proposed_locator: The verified alternative locator string.
        target_file: Relative or absolute path to the file containing the locator.
        workspace_root: Root workspace directory for path resolution.
        allow_internal: Whether to allow internal directories (for testing).

    Returns:
        PatchResult containing diff string, match count, or failure error.
    """
    if not original_selector or not original_selector.strip():
        return PatchResult(
            success=False,
            target_file=target_file,
            original_selector=original_selector or "",
            proposed_locator=proposed_locator or "",
            replaced_count=0,
            error="Original selector cannot be empty or whitespace.",
        )

    if not proposed_locator or not proposed_locator.strip():
        return PatchResult(
            success=False,
            target_file=target_file,
            original_selector=original_selector,
            proposed_locator="",
            replaced_count=0,
            error="Proposed locator cannot be empty or whitespace.",
        )

    try:
        resolved_path = validate_target_path(
            target_file=target_file,
            workspace_root=workspace_root,
            allow_internal=allow_internal,
        )
    except PatchSecurityError as sec_err:
        return PatchResult(
            success=False,
            target_file=target_file,
            original_selector=original_selector,
            proposed_locator=proposed_locator,
            replaced_count=0,
            error=str(sec_err),
        )

    if not resolved_path.is_file():
        return PatchResult(
            success=False,
            target_file=target_file,
            original_selector=original_selector,
            proposed_locator=proposed_locator,
            replaced_count=0,
            error=f"Target file does not exist or is not a regular file: '{target_file}'",
        )

    try:
        original_content = resolved_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        return PatchResult(
            success=False,
            target_file=target_file,
            original_selector=original_selector,
            proposed_locator=proposed_locator,
            replaced_count=0,
            error=f"Failed to read target file '{target_file}': {exc}",
        )

    # Count occurrences
    occurrence_count = original_content.count(original_selector)
    if occurrence_count == 0:
        return PatchResult(
            success=False,
            target_file=target_file,
            original_selector=original_selector,
            proposed_locator=proposed_locator,
            replaced_count=0,
            error=(
                f"Original selector '{original_selector}' was not found in target file '{target_file}'. "
                "Refusing to generate an unverified or corrupted patch."
            ),
        )

    # Perform replacement
    patched_content = original_content.replace(original_selector, proposed_locator)

    # Generate unified diff
    orig_lines = original_content.splitlines(keepends=True)
    patch_lines = patched_content.splitlines(keepends=True)
    root = Path(workspace_root or os.getcwd()).resolve()
    rel_display_path = (
        resolved_path.relative_to(root).as_posix()
        if resolved_path.is_relative_to(root)
        else resolved_path.name
    )

    diff_generator = difflib.unified_diff(
        orig_lines,
        patch_lines,
        fromfile=f"a/{rel_display_path}",
        tofile=f"b/{rel_display_path}",
        lineterm="",
    )
    diff_text = "\n".join(line.rstrip("\r\n") for line in diff_generator)

    return PatchResult(
        success=True,
        target_file=rel_display_path,
        diff=diff_text,
        original_selector=original_selector,
        proposed_locator=proposed_locator,
        replaced_count=occurrence_count,
        error=None,
    )
