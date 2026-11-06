"""Integration tests for OmniSight Browser Agent, Vision Engine, and Artifact Serving."""

from pathlib import Path
from unittest.mock import patch
from fastapi import HTTPException
import pytest

from backend.app.api.artifacts import get_artifact
from backend.app.api.runs import execute_run_pipeline
from backend.app.schemas.runs import RunCreateRequest
from backend.app.services.orchestrator import run_orchestrator
from backend.app.services.run_store import run_store
from navigation.navigator import NavigationResult


@pytest.fixture(autouse=True)
def clean_run_store():
    """Ensure in-memory repository is reset before each test."""
    run_store.clear()
    yield
    run_store.clear()


@pytest.fixture(scope="module", autouse=True)
def ensure_sample_artifacts():
    """Ensure sample artifact fixture files exist for testing."""
    sample_dir = Path("artifacts") / "test_sample_run"
    sample_dir.mkdir(parents=True, exist_ok=True)
    png_file = sample_dir / "before.png"
    dom_file = sample_dir / "dom.html"

    if not png_file.exists():
        png_file.write_bytes(b"\x89PNG\r\n\x1a\nfake_image_bytes")
    if not dom_file.exists():
        dom_file.write_text("<!DOCTYPE html><html><body><h1>OmniSight Test</h1></body></html>", encoding="utf-8")

    yield


# =============================================================================
# Day 16: Artifact Serving Tests
# =============================================================================

def test_artifacts_endpoint_serves_screenshot_file():
    """Day 16: Verify get_artifact serves PNG screenshot with correct media type."""
    response = get_artifact("test_sample_run", "before.png")

    assert response.status_code == 200
    assert response.media_type == "image/png"
    assert Path(response.path).name == "before.png"


def test_artifacts_endpoint_serves_dom_snapshot_file():
    """Day 16: Verify get_artifact serves DOM snapshot with HTML media type."""
    response = get_artifact("test_sample_run", "dom.html")

    assert response.status_code == 200
    assert response.media_type == "text/html"
    assert Path(response.path).name == "dom.html"


def test_artifacts_endpoint_missing_file_raises_404():
    """Day 16: Verify missing artifact raises HTTP 404."""
    with pytest.raises(HTTPException) as exc_info:
        get_artifact("run_nonexistent_xyz", "before.png")

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()


def test_artifacts_endpoint_empty_inputs_raises_400():
    """Day 16: Verify empty run_id or filename raises HTTP 400."""
    with pytest.raises(HTTPException) as exc_info:
        get_artifact("   ", "before.png")

    assert exc_info.value.status_code == 400


# =============================================================================
# Day 17: End-to-End Orchestrator Integration Tests
# =============================================================================

def test_orchestrator_success_lifecycle():
    """Day 17: Verify orchestrator transitions through capturing -> analyzing -> completed."""
    run = run_store.create(RunCreateRequest(url="http://127.0.0.1:8000/"))

    mock_nav_result = NavigationResult(
        run_id=run.run_id,
        url=run.url,
        page_title="OmniSight Dashboard",
        captured_at="2026-10-25T00:00:00Z",
        viewport={"width": 1280, "height": 800},
        screenshot_path="artifacts/test_sample_run/before.png",
        dom_snapshot_path="artifacts/test_sample_run/dom.html",
        status="success",
        error=None,
    )

    with patch("navigation.navigator.BrowserNavigator.navigate", return_value=mock_nav_result):
        run_orchestrator.execute_run(run.run_id, run.url)

    updated = run_store.get(run.run_id)
    assert updated is not None
    assert updated.status == "completed"
    assert "Inspection complete" in updated.message
    assert updated.error is None

    # Check findings were retrieved and stored
    findings = run_store.get_findings(run.run_id)
    assert isinstance(findings, list)


def test_orchestrator_handles_navigation_failure():
    """Day 17: Verify orchestrator updates status='failed' when Browser Agent navigation fails."""
    run = run_store.create(RunCreateRequest(url="http://127.0.0.1:8000/broken"))

    mock_failed_result = NavigationResult(
        run_id=run.run_id,
        url=run.url,
        page_title="",
        captured_at="2026-10-25T00:00:00Z",
        viewport={},
        screenshot_path=None,
        dom_snapshot_path=None,
        status="failed",
        error="net::ERR_CONNECTION_REFUSED",
    )

    with patch("navigation.navigator.BrowserNavigator.navigate", return_value=mock_failed_result):
        run_orchestrator.execute_run(run.run_id, run.url)

    updated = run_store.get(run.run_id)
    assert updated is not None
    assert updated.status == "failed"
    assert "ERR_CONNECTION_REFUSED" in updated.error


def test_orchestrator_handles_vision_engine_exception():
    """Day 17: Verify orchestrator marks run='failed' if Vision Engine throws an error."""
    run = run_store.create(RunCreateRequest(url="http://127.0.0.1:8000/"))

    mock_nav_result = NavigationResult(
        run_id=run.run_id,
        url=run.url,
        page_title="OmniSight",
        captured_at="2026-10-25T00:00:00Z",
        viewport={"width": 1280, "height": 800},
        screenshot_path="artifacts/test_sample_run/before.png",
        dom_snapshot_path="artifacts/test_sample_run/dom.html",
        status="success",
    )

    with patch("navigation.navigator.BrowserNavigator.navigate", return_value=mock_nav_result), \
         patch("vision_engine.detection.dom_detector.detect_dom_issues", side_effect=ValueError("Corrupt DOM snapshot")):
        run_orchestrator.execute_run(run.run_id, run.url)

    updated = run_store.get(run.run_id)
    assert updated is not None
    assert updated.status == "failed"
    assert "Corrupt DOM snapshot" in updated.error


def test_execute_run_pipeline_endpoint_unit():
    """Day 17: Verify POST /api/v1/runs/{run_id}/execute endpoint executes the pipeline."""
    run = run_store.create(RunCreateRequest(url="http://127.0.0.1:8000/"))

    mock_nav_result = NavigationResult(
        run_id=run.run_id,
        url=run.url,
        page_title="OmniSight",
        captured_at="2026-10-25T00:00:00Z",
        viewport={"width": 1280, "height": 800},
        screenshot_path="artifacts/test_sample_run/before.png",
        dom_snapshot_path="artifacts/test_sample_run/dom.html",
        status="success",
    )

    with patch("navigation.navigator.BrowserNavigator.navigate", return_value=mock_nav_result):
        res = execute_run_pipeline(run.run_id)

    assert res.run_id == run.run_id
    assert res.status == "completed"


def test_execute_run_pipeline_endpoint_unknown_run_raises_404():
    """Day 17: Verify execute_run_pipeline raises HTTP 404 for unknown run."""
    with pytest.raises(HTTPException) as exc_info:
        execute_run_pipeline("run_nonexistent_xyz")

    assert exc_info.value.status_code == 404
    assert "not found" in exc_info.value.detail.lower()
