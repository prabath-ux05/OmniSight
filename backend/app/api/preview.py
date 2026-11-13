"""API endpoints for real-time Live Website Scanning Preview."""

from pathlib import Path
from typing import Optional
from urllib.parse import unquote
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse, StreamingResponse

from backend.app.api.deps import check_run_access, get_current_user_optional
from backend.app.core.logging import logger
from backend.app.models.user import UserModel
from backend.app.services.preview_service import preview_service
from backend.app.services.run_store import run_store

router = APIRouter(prefix="/api/v1/runs", tags=["Live Preview"])


def _validate_run_id(run_id: str) -> str:
    cleaned = unquote(run_id).strip() if run_id else ""
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid run_id: identifier must not be empty or whitespace.",
        )
    if len(cleaned) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid run_id: identifier exceeds maximum allowed length of 128 characters.",
        )
    return cleaned


@router.get(
    "/{run_id}/preview",
    status_code=status.HTTP_200_OK,
    summary="Get current live scanning preview state and telemetry",
    description="Returns current preview frame, scrolling position, progress percentage, stage, and defect highlights.",
)
def get_preview_status(
    run_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
):
    """Retrieve current preview state for an active or completed inspection run."""
    clean_id = _validate_run_id(run_id)

    run = run_store.get(clean_id)
    if not run and not preview_service.get_preview(clean_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_id}' was not found.",
        )
    if run:
        check_run_access(run, current_user)

    preview = preview_service.get_preview(clean_id)
    if preview:
        return JSONResponse(status_code=status.HTTP_200_OK, content=preview)

    # Fallback to run_store if run completed before preview was requested
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_id}' was not found.",
        )

    # Construct synthesized completed preview state from historical run
    findings = run_store.get_findings(clean_id)
    defect_list = []
    for f in findings:
        defect_list.append({
            "id": f.finding_id,
            "category": f.category,
            "severity": f.severity,
            "selector": f.selector,
            "description": f.description,
            "viewport": getattr(f, "viewport", "desktop") or "desktop",
            "box": None,
        })

    viewports = run_store._run_viewports.get(clean_id, ["desktop"])
    synthesized = {
        "run_id": clean_id,
        "url": run.url,
        "viewport": viewports[0] if viewports else "desktop",
        "target_viewports": viewports,
        "viewport_width": 1280,
        "viewport_height": 800,
        "stage": run.status,
        "progress": 100 if run.status == "completed" else 0,
        "scroll_y": 0,
        "max_scroll_y": 0,
        "scroll_ratio": 1.0 if run.status == "completed" else 0.0,
        "frame_base64": None,
        "defects": defect_list,
        "message": run.message or f"Inspection {run.status}",
        "error": run.error,
        "updated_at": run.completed_at or run.created_at,
    }
    return JSONResponse(status_code=status.HTTP_200_OK, content=synthesized)


@router.get(
    "/{run_id}/preview/stream",
    summary="Stream live preview frames and telemetry via Server-Sent Events (SSE)",
    description="Provides real-time SSE stream of scanning progress, browser scrolling, and frames.",
)
async def stream_preview_events(
    run_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
):
    """Server-Sent Events endpoint streaming real-time browser preview frames and telemetry."""
    clean_id = _validate_run_id(run_id)

    # Ensure run exists and enforce ownership access
    run = run_store.get(clean_id)
    if not run and not preview_service.get_preview(clean_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_id}' was not found.",
        )
    if run:
        check_run_access(run, current_user)

    return StreamingResponse(
        preview_service.stream_events(clean_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get(
    "/{run_id}/preview/frame",
    summary="Get latest raw JPEG preview frame",
    description="Returns the latest captured browser JPEG frame with telemetry in response headers.",
)
def get_preview_frame(
    run_id: str,
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
):
    """Retrieve raw binary JPEG frame for the given run."""
    clean_id = _validate_run_id(run_id)

    # Ensure run exists and enforce ownership access
    run = run_store.get(clean_id)
    if not run and not preview_service.get_preview(clean_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run '{clean_id}' was not found.",
        )
    if run:
        check_run_access(run, current_user)

    raw_bytes = preview_service.get_frame_bytes(clean_id)
    if raw_bytes:
        state = preview_service.get_preview(clean_id) or {}
        headers = {
            "Content-Type": "image/jpeg",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Scan-Progress": str(state.get("progress", 0)),
            "X-Scan-Scroll-Y": str(state.get("scroll_y", 0)),
            "X-Scan-Max-Scroll": str(state.get("max_scroll_y", 0)),
            "X-Scan-Viewport": str(state.get("viewport", "desktop")),
            "X-Scan-Stage": str(state.get("stage", "scrolling")),
        }
        return Response(content=raw_bytes, media_type="image/jpeg", headers=headers)

    # Fallback to saved screenshot artifact file on disk if exists
    for artifact_name in ("before.png", "before_desktop.png", "screenshot.png"):
        candidate = Path("evidence") / clean_id / artifact_name
        if candidate.is_file():
            return Response(
                content=candidate.read_bytes(),
                media_type="image/png",
                headers={"Cache-Control": "no-cache"},
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No preview frame currently available for run '{clean_id}'.",
    )
