"""Live Website Scanning Preview Service.

Provides real-time frame buffering, scrolling telemetry, defect coordinates,
and Server-Sent Events (SSE) streaming for live website inspection.
"""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
import json
from pathlib import Path
import threading
from typing import Any, AsyncGenerator, Optional

from backend.app.core.logging import logger


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LivePreviewService:
    """Thread-safe in-memory buffer and streaming hub for live website scanning preview."""

    def __init__(self, max_cached_runs: int = 50) -> None:
        self._lock = threading.Lock()
        self._states: dict[str, dict[str, Any]] = {}
        self._raw_frames: dict[str, bytes] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._max_cached_runs = max_cached_runs

    def init_run(
        self,
        run_id: str,
        url: str,
        viewports: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Initialize or reset the live preview telemetry state for a new inspection run."""
        clean_vps = [v.strip().lower() for v in (viewports or ["desktop"]) if v]
        if not clean_vps:
            clean_vps = ["desktop"]

        initial_state: dict[str, Any] = {
            "run_id": run_id,
            "url": url,
            "viewport": clean_vps[0],
            "target_viewports": clean_vps,
            "viewport_width": 1280 if clean_vps[0] == "desktop" else (768 if clean_vps[0] == "tablet" else 375),
            "viewport_height": 800 if clean_vps[0] == "desktop" else (1024 if clean_vps[0] == "tablet" else 667),
            "stage": "queued",
            "progress": 0,
            "scroll_y": 0,
            "max_scroll_y": 0,
            "scroll_ratio": 0.0,
            "frame_base64": None,
            "defects": [],
            "message": "Initializing live inspection scanner...",
            "error": None,
            "updated_at": _utc_now_iso(),
        }

        with self._lock:
            # Enforce cache capacity
            if len(self._states) >= self._max_cached_runs:
                oldest_key = next(iter(self._states.keys()))
                self._states.pop(oldest_key, None)
                self._raw_frames.pop(oldest_key, None)
                self._subscribers.pop(oldest_key, None)

            self._states[run_id] = initial_state
            if run_id not in self._subscribers:
                self._subscribers[run_id] = []

        self._broadcast(run_id, initial_state)
        return initial_state

    def publish_frame(
        self,
        run_id: str,
        frame_bytes: bytes,
        *,
        scroll_y: int = 0,
        max_scroll_y: int = 0,
        progress: int = 0,
        stage: str = "scrolling",
        viewport: str = "desktop",
        viewport_width: int = 1280,
        viewport_height: int = 800,
        message: Optional[str] = None,
        defects: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """Publish a newly captured browser JPEG frame and its associated scroll telemetry."""
        b64_str = f"data:image/jpeg;base64,{base64.b64encode(frame_bytes).decode('ascii')}"
        scroll_ratio = float(scroll_y / max_scroll_y) if max_scroll_y > 0 else 0.0
        scroll_ratio = max(0.0, min(1.0, scroll_ratio))

        with self._lock:
            current = self._states.get(run_id) or {
                "run_id": run_id,
                "url": "",
                "target_viewports": [viewport],
            }
            existing_defects = current.get("defects", [])
            merged_defects = defects if defects is not None else existing_defects

            updated: dict[str, Any] = {
                **current,
                "viewport": viewport,
                "viewport_width": viewport_width,
                "viewport_height": viewport_height,
                "stage": stage,
                "progress": max(0, min(100, int(progress))),
                "scroll_y": int(scroll_y),
                "max_scroll_y": int(max_scroll_y),
                "scroll_ratio": round(scroll_ratio, 4),
                "frame_base64": b64_str,
                "defects": merged_defects,
                "message": message or f"Scanning {viewport} viewport at {scroll_y}px / {max_scroll_y}px",
                "error": None,
                "updated_at": _utc_now_iso(),
            }
            self._states[run_id] = updated
            self._raw_frames[run_id] = frame_bytes

        self._broadcast(run_id, updated)

    def update_status(
        self,
        run_id: str,
        *,
        stage: str,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        error: Optional[str] = None,
        viewport: Optional[str] = None,
        defects: Optional[list[dict[str, Any]]] = None,
    ) -> None:
        """Update live telemetry status without replacing the current visual frame."""
        with self._lock:
            current = self._states.get(run_id)
            if not current:
                current = {
                    "run_id": run_id,
                    "url": "",
                    "viewport": viewport or "desktop",
                    "target_viewports": [viewport or "desktop"],
                    "viewport_width": 1280,
                    "viewport_height": 800,
                    "progress": 0,
                    "scroll_y": 0,
                    "max_scroll_y": 0,
                    "scroll_ratio": 0.0,
                    "frame_base64": None,
                    "defects": [],
                }

            updated: dict[str, Any] = {**current}
            updated["stage"] = stage
            if progress is not None:
                updated["progress"] = max(0, min(100, int(progress)))
            if message is not None:
                updated["message"] = message
            if error is not None:
                updated["error"] = error
            if viewport is not None:
                updated["viewport"] = viewport
            if defects is not None:
                updated["defects"] = defects
            updated["updated_at"] = _utc_now_iso()

            self._states[run_id] = updated

        self._broadcast(run_id, updated)

    def get_preview(self, run_id: str) -> Optional[dict[str, Any]]:
        """Retrieve current preview state dictionary for a run, or None if not found."""
        with self._lock:
            state = self._states.get(run_id)
            if state is None:
                return None
            return dict(state)

    def get_frame_bytes(self, run_id: str) -> Optional[bytes]:
        """Retrieve latest raw JPEG frame bytes for direct image response."""
        with self._lock:
            return self._raw_frames.get(run_id)

    def _broadcast(self, run_id: str, payload: dict[str, Any]) -> None:
        """Deliver update payload to all active subscriber queues for this run in a thread-safe manner."""
        with self._lock:
            subscribers = list(self._subscribers.get(run_id, []))

        current_loop = None
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        for loop, q in subscribers:
            try:
                def _safe_put():
                    try:
                        q.put_nowait(payload)
                    except asyncio.QueueFull:
                        pass
                if current_loop == loop:
                    _safe_put()
                elif loop.is_running():
                    loop.call_soon_threadsafe(_safe_put)
                else:
                    _safe_put()
            except Exception as exc:
                logger.debug("Failed to put preview payload to subscriber queue: %s", str(exc))

    def format_sse(self, payload: dict[str, Any]) -> str:
        """Format dictionary into Server-Sent Events (SSE) data string."""
        return f"data: {json.dumps(payload)}\n\n"

    async def stream_events(
        self,
        run_id: str,
        timeout_seconds: float = 120.0,
    ) -> AsyncGenerator[str, None]:
        """Async generator yielding Server-Sent Events (SSE) formatted data for client streams."""
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=32)
        sub_entry = (loop, queue)

        with self._lock:
            if run_id not in self._subscribers:
                self._subscribers[run_id] = []
            self._subscribers[run_id].append(sub_entry)
            initial_state = self._states.get(run_id)

        try:
            # Immediately emit current state if present
            if initial_state:
                yield self.format_sse(initial_state)

            start_time = loop.time()
            while True:
                # Check overall timeout to prevent hanging connections
                if loop.time() - start_time > timeout_seconds:
                    logger.debug("SSE stream reached timeout for run %s", run_id)
                    break

                try:
                    payload = await asyncio.wait_for(queue.get(), timeout=4.0)
                    yield self.format_sse(payload)

                    # Close SSE stream when run reaches terminal state
                    stage = str(payload.get("stage", "")).lower()
                    if stage in ("completed", "failed", "cancelled"):
                        logger.debug("SSE stream closing naturally on terminal stage: %s", stage)
                        break
                except asyncio.TimeoutError:
                    # Send periodic SSE keep-alive ping comment to prevent client/proxy disconnection
                    yield ": keep-alive\n\n"

        except asyncio.CancelledError:
            logger.debug("Client cancelled SSE connection for run %s", run_id)
            raise
        finally:
            with self._lock:
                sub_list = self._subscribers.get(run_id, [])
                if sub_entry in sub_list:
                    sub_list.remove(sub_entry)
                if not sub_list:
                    self._subscribers.pop(run_id, None)

    def close_run(self, run_id: str) -> None:
        """Evict or finalize subscribers for a run."""
        with self._lock:
            self._subscribers.pop(run_id, None)

    def clear(self) -> None:
        """Clear all in-memory preview states (primarily for testing)."""
        with self._lock:
            self._states.clear()
            self._raw_frames.clear()
            self._subscribers.clear()


preview_service = LivePreviewService()
