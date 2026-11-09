"""Artifact serving routes for OmniSight inspection screenshots, DOM snapshots, and metadata."""

import os
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from backend.app.core.logging import logger
from backend.app.schemas.artifacts import ArtifactResponse
from backend.app.schemas.errors import ErrorResponse

router = APIRouter(prefix="/api/v1/artifacts", tags=["Artifacts"])

ARTIFACTS_ROOT = Path("artifacts").resolve()


def _sanitize_path_component(component: str, name: str = "identifier") -> str:
    """Validate path component and prevent directory traversal sequences."""
    raw = component.strip() if component else ""
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {name}: must not be empty or whitespace.",
        )
    if ".." in raw or "/" in raw or "\\" in raw or "\0" in raw:
        logger.warning("Blocked directory traversal attempt in %s: %r", name, component)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {name}: directory traversal attempt blocked.",
        )
    clean = os.path.basename(raw)
    if len(clean) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {name}: length exceeds maximum allowed 128 characters.",
        )
    return clean


@router.get(
    "/{run_id}/screenshot",
    summary="Serve inspection run screenshot",
    description="Streams the captured visual screenshot for an inspection run.",
    responses={
        200: {"description": "Screenshot image successfully streamed"},
        400: {"model": ErrorResponse, "description": "Invalid run_id format"},
        404: {"model": ErrorResponse, "description": "Screenshot not found for run"},
    },
)
def get_run_screenshot(run_id: str):
    """Serve the primary screenshot artifact for a specific run."""
    clean_id = _sanitize_path_component(run_id, "run_id")
    target_file = (ARTIFACTS_ROOT / clean_id / "before.png").resolve()

    if target_file.is_file() and str(target_file).startswith(str(ARTIFACTS_ROOT)):
        return FileResponse(target_file, media_type="image/png")

    from backend.app.services.run_store import run_store
    art = run_store.get_artifact_by_type(clean_id, "screenshot")
    if art and Path(art.storage_path).is_file():
        return FileResponse(Path(art.storage_path).resolve(), media_type="image/png")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Screenshot artifact for run '{clean_id}' not found.",
    )


@router.get(
    "/{run_id}/dom",
    summary="Serve inspection run DOM snapshot",
    description="Streams the saved DOM HTML snapshot for an inspection run.",
    responses={
        200: {"description": "DOM HTML snapshot successfully streamed"},
        400: {"model": ErrorResponse, "description": "Invalid run_id format"},
        404: {"model": ErrorResponse, "description": "DOM snapshot not found for run"},
    },
)
def get_run_dom(run_id: str):
    """Serve the primary DOM snapshot artifact for a specific run."""
    clean_id = _sanitize_path_component(run_id, "run_id")
    target_file = (ARTIFACTS_ROOT / clean_id / "dom.html").resolve()

    if target_file.is_file() and str(target_file).startswith(str(ARTIFACTS_ROOT)):
        return FileResponse(target_file, media_type="text/html")

    from backend.app.services.run_store import run_store
    art = run_store.get_artifact_by_type(clean_id, "dom_snapshot")
    if art and Path(art.storage_path).is_file():
        return FileResponse(Path(art.storage_path).resolve(), media_type="text/html")

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"DOM snapshot artifact for run '{clean_id}' not found.",
    )


@router.get(
    "/{run_id}/{filename}",
    summary="Serve inspection artifact file",
    description=(
        "Streams a captured screenshot or DOM snapshot for an inspection run. "
        "Validates path boundaries to prevent directory traversal."
    ),
    responses={
        200: {"description": "Artifact file successfully retrieved"},
        400: {"model": ErrorResponse, "description": "Invalid artifact path or directory traversal detected"},
        404: {"model": ErrorResponse, "description": "Artifact file not found on disk"},
    },
)
def get_artifact(run_id: str, filename: str):
    """Serve a screenshot or DOM artifact file for a specific run."""
    clean_run_id = _sanitize_path_component(run_id, "run_id")
    clean_filename = _sanitize_path_component(filename, "filename")

    target_file = (ARTIFACTS_ROOT / clean_run_id / clean_filename).resolve()

    # Prevent directory traversal attacks
    if not str(target_file).startswith(str(ARTIFACTS_ROOT)):
        logger.warning("Blocked directory traversal attempt: %s", target_file)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid artifact path: directory traversal attempt blocked.",
        )

    if not target_file.is_file():
        logger.info("Artifact not found: %s", target_file)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Artifact '{clean_filename}' for run '{clean_run_id}' not found.",
        )

    media_type = "image/png" if clean_filename.lower().endswith(".png") else "text/html"
    return FileResponse(target_file, media_type=media_type)
