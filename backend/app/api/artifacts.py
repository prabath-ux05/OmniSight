"""Artifact serving route for OmniSight inspection screenshots and DOM snapshots."""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from backend.app.core.logging import logger

router = APIRouter(prefix="/api/v1/artifacts", tags=["Artifacts"])

ARTIFACTS_ROOT = Path("artifacts").resolve()


@router.get(
    "/{run_id}/{filename}",
    summary="Serve inspection artifact file",
    description=(
        "Streams a captured screenshot or DOM snapshot for an inspection run. "
        "Validates path boundaries to prevent directory traversal."
    ),
    responses={
        200: {"description": "Artifact file successfully retrieved"},
        400: {"description": "Invalid artifact path or directory traversal detected"},
        404: {"description": "Artifact file not found on disk"},
    },
)
def get_artifact(run_id: str, filename: str):
    """Serve a screenshot or DOM artifact file for a specific run."""
    clean_run_id = os.path.basename(run_id.strip())
    clean_filename = os.path.basename(filename.strip())

    if not clean_run_id or not clean_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="run_id and filename are required.",
        )

    target_file = (ARTIFACTS_ROOT / clean_run_id / clean_filename).resolve()

    # Prevent directory traversal attacks
    if not str(target_file).startswith(str(ARTIFACTS_ROOT)):
        logger.warning("Blocked directory traversal attempt: %s", target_file)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid artifact path.",
        )

    if not target_file.is_file():
        logger.info("Artifact not found: %s", target_file)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{clean_filename}' for run '{clean_run_id}' not found.",
        )

    media_type = "image/png" if clean_filename.lower().endswith(".png") else "text/html"
    return FileResponse(target_file, media_type=media_type)
