"""Comprehensive automated tests for OmniSight artifact serving, metadata persistence, and path traversal security."""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from fastapi import HTTPException

from backend.app.api.artifacts import get_artifact, get_run_dom, get_run_screenshot
from backend.app.main import app
from backend.app.schemas.runs import RunCreateRequest
from backend.app.services.orchestrator import run_orchestrator
from backend.app.services.run_store import run_store
from navigation.navigator import NavigationResult


@pytest.fixture(scope="module", autouse=True)
def setup_test_sample_artifacts():
    """Ensure sample artifact fixture files exist for testing."""
    sample_dir = Path("artifacts") / "test_artifact_sample_run"
    sample_dir.mkdir(parents=True, exist_ok=True)
    png_file = sample_dir / "before.png"
    dom_file = sample_dir / "dom.html"

    if not png_file.exists():
        png_file.write_bytes(b"\x89PNG\r\n\x1a\nfake_image_bytes_day3")
    if not dom_file.exists():
        dom_file.write_text("<!DOCTYPE html><html><body><h1>Day 3 Test</h1></body></html>", encoding="utf-8")

    yield


async def dispatch_asgi_get(path: str) -> tuple[int, dict | bytes]:
    """Helper to dispatch an ASGI GET request."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [(b"accept", b"*/*")],
    }
    response_body = []
    status_code = None

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await app(scope, receive, send)
    raw = b"".join(response_body)
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        data = raw
    return status_code, data


# =============================================================================
# Artifact Serving and Security Tests
# =============================================================================

def test_artifacts_endpoint_serves_screenshot_via_direct_route():
    """Verify GET /api/v1/artifacts/{run_id}/screenshot streams the screenshot."""
    res = get_run_screenshot("test_artifact_sample_run")
    assert res.status_code == 200
    assert res.media_type == "image/png"
    assert Path(res.path).name == "before.png"


def test_artifacts_endpoint_serves_dom_via_direct_route():
    """Verify GET /api/v1/artifacts/{run_id}/dom streams the HTML DOM snapshot."""
    res = get_run_dom("test_artifact_sample_run")
    assert res.status_code == 200
    assert res.media_type == "text/html"
    assert Path(res.path).name == "dom.html"


def test_artifacts_endpoint_blocks_directory_traversal_dotdot():
    """Verify directory traversal using .. is strictly blocked with HTTP 400."""
    with pytest.raises(HTTPException) as exc_info:
        get_run_screenshot("../secret")
    assert exc_info.value.status_code == 400
    assert "directory traversal" in exc_info.value.detail.lower()

    with pytest.raises(HTTPException) as exc_info:
        get_run_dom("..\\windows\\system32")
    assert exc_info.value.status_code == 400
    assert "directory traversal" in exc_info.value.detail.lower()


def test_artifacts_endpoint_missing_screenshot_returns_404():
    """Verify missing screenshot file raises HTTP 404."""
    with pytest.raises(HTTPException) as exc_info:
        get_run_screenshot("run_nonexistent_xyz")
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


def test_artifacts_endpoint_missing_dom_returns_404():
    """Verify missing DOM snapshot file raises HTTP 404."""
    with pytest.raises(HTTPException) as exc_info:
        get_run_dom("run_nonexistent_xyz")
    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


# =============================================================================
# Artifact Metadata and Database Persistence Tests
# =============================================================================

def test_artifacts_metadata_endpoint_lists_all_recorded_artifacts():
    """Verify GET /api/v1/runs/{run_id}/artifacts returns recorded metadata."""
    run = run_store.create(RunCreateRequest(url="https://example.com/artifacts"))

    # Record two artifacts in database
    run_store.record_artifact(
        run_id=run.run_id,
        artifact_type="screenshot",
        storage_path="artifacts/test_artifact_sample_run/before.png",
        content_type="image/png",
    )
    run_store.record_artifact(
        run_id=run.run_id,
        artifact_type="dom_snapshot",
        storage_path="artifacts/test_artifact_sample_run/dom.html",
        content_type="text/html",
    )

    status_code, data = asyncio.run(dispatch_asgi_get(f"/api/v1/runs/{run.run_id}/artifacts"))
    assert status_code == 200
    assert isinstance(data, list)
    assert len(data) == 2

    types = {item["artifact_type"] for item in data}
    assert "screenshot" in types
    assert "dom_snapshot" in types

    for item in data:
        assert item["run_id"] == run.run_id
        assert item["download_url"].startswith("/api/v1/artifacts/")


def test_artifacts_metadata_endpoint_unknown_run_returns_404():
    """Verify GET /api/v1/runs/{run_id}/artifacts returns 404 for unknown run."""
    status_code, data = asyncio.run(dispatch_asgi_get("/api/v1/runs/run_unknown_9999/artifacts"))
    assert status_code == 404
    assert "not found" in data["detail"].lower()


def test_orchestrator_records_screenshot_and_dom_artifacts_in_database():
    """Verify orchestrator automatically records artifacts in database during pipeline execution."""
    run = run_store.create(RunCreateRequest(url="http://127.0.0.1:8000/"))

    mock_nav_result = NavigationResult(
        run_id=run.run_id,
        url=run.url,
        page_title="OmniSight Evidence Test",
        captured_at="2026-11-02T12:00:00Z",
        viewport={"width": 1280, "height": 800},
        screenshot_path="artifacts/test_artifact_sample_run/before.png",
        dom_snapshot_path="artifacts/test_artifact_sample_run/dom.html",
        status="success",
        error=None,
    )

    with patch("navigation.navigator.BrowserNavigator.navigate", return_value=mock_nav_result):
        run_orchestrator.execute_run(run.run_id, run.url)

    # Check that artifact metadata was automatically recorded in DB
    artifacts = run_store.get_artifacts(run.run_id)
    assert artifacts is not None
    assert len(artifacts) >= 2

    types = {a.artifact_type for a in artifacts}
    assert "screenshot" in types
    assert "dom_snapshot" in types
