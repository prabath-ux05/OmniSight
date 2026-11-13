"""Tests for OmniSight Live Website Scanning Preview service, API endpoints, and browser integration."""

import json
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException

from backend.app.api.preview import get_preview_status, get_preview_frame, _validate_run_id
from backend.app.services.preview_service import preview_service
from backend.app.services.run_store import run_store
from backend.app.schemas.runs import RunCreateRequest


@pytest.fixture(autouse=True)
def cleanup_preview():
    preview_service.clear()
    yield
    preview_service.clear()


def test_preview_service_init_and_publish():
    """Test preview_service lifecycle: init_run, publish_frame, update_status, and get_preview."""
    run_id = "run_test_preview_001"
    url = "https://example.com"
    viewports = ["desktop", "mobile"]

    # 1. Initialize run
    init_state = preview_service.init_run(run_id=run_id, url=url, viewports=viewports)
    assert init_state["run_id"] == run_id
    assert init_state["url"] == url
    assert init_state["viewport"] == "desktop"
    assert init_state["progress"] == 0
    assert init_state["stage"] == "queued"
    assert init_state["frame_base64"] is None

    # 2. Publish frame
    dummy_frame = b"\xff\xd8\xff\xe0dummy_jpeg_bytes"
    preview_service.publish_frame(
        run_id=run_id,
        frame_bytes=dummy_frame,
        scroll_y=300,
        max_scroll_y=1200,
        progress=40,
        stage="scrolling",
        viewport="desktop",
        message="Scanning desktop: 300px / 1200px",
        defects=[{
            "id": "defect_01",
            "category": "broken_image",
            "severity": "medium",
            "selector": "#hero-img",
            "box": {"x": 50, "y": 80, "width": 400, "height": 200},
        }],
    )

    state = preview_service.get_preview(run_id)
    assert state is not None
    assert state["stage"] == "scrolling"
    assert state["progress"] == 40
    assert state["scroll_y"] == 300
    assert state["max_scroll_y"] == 1200
    assert state["scroll_ratio"] == 0.25
    assert state["frame_base64"].startswith("data:image/jpeg;base64,")
    assert len(state["defects"]) == 1
    assert state["defects"][0]["selector"] == "#hero-img"

    # 3. Retrieve raw frame bytes
    raw_bytes = preview_service.get_frame_bytes(run_id)
    assert raw_bytes == dummy_frame

    # 4. Update status without overwriting frame
    preview_service.update_status(
        run_id,
        stage="completed",
        progress=100,
        message="Inspection complete",
    )
    final_state = preview_service.get_preview(run_id)
    assert final_state["stage"] == "completed"
    assert final_state["progress"] == 100
    assert final_state["frame_base64"] == state["frame_base64"]


def test_preview_service_format_sse_and_subscriber_broadcast():
    """Verify SSE event serialization format and subscriber queue delivery."""
    run_id = "run_sse_test_002"
    init_state = preview_service.init_run(run_id=run_id, url="https://example.com")

    # Verify SSE data formatting
    sse_text = preview_service.format_sse(init_state)
    assert sse_text.startswith("data: {")
    assert sse_text.endswith("}\n\n")
    parsed = json.loads(sse_text[6:].strip())
    assert parsed["run_id"] == run_id
    assert parsed["stage"] == "queued"

    # Verify subscriber queue delivery
    mock_queue = MagicMock()
    mock_loop = MagicMock()
    mock_loop.is_running.return_value = False

    preview_service._subscribers[run_id] = [(mock_loop, mock_queue)]

    preview_service.publish_frame(
        run_id=run_id,
        frame_bytes=b"sample_frame",
        scroll_y=150,
        max_scroll_y=600,
        progress=25,
        stage="scrolling",
    )

    assert mock_queue.put_nowait.called
    delivered = mock_queue.put_nowait.call_args[0][0]
    assert delivered["stage"] == "scrolling"
    assert delivered["scroll_y"] == 150
    assert delivered["progress"] == 25


def test_api_preview_endpoints_direct():
    """Test get_preview_status, get_preview_frame, and _validate_run_id."""
    # 1. Validation checks
    with pytest.raises(HTTPException) as exc_empty:
        _validate_run_id("   ")
    assert exc_empty.value.status_code == 400

    with pytest.raises(HTTPException) as exc_long:
        _validate_run_id("a" * 150)
    assert exc_long.value.status_code == 400

    # 2. Non-existent run -> 404
    with pytest.raises(HTTPException) as exc_404:
        get_preview_status("run_unknown_9999")
    assert exc_404.value.status_code == 404

    # 3. Active run in preview_service
    run_id = "run_active_preview_test"
    preview_service.init_run(run_id, "https://test.com")
    preview_service.publish_frame(
        run_id=run_id,
        frame_bytes=b"dummy_frame",
        scroll_y=200,
        max_scroll_y=1000,
        progress=50,
        stage="scrolling",
        viewport="tablet",
    )

    resp_active = get_preview_status(run_id)
    assert resp_active.status_code == 200
    body = json.loads(resp_active.body)
    assert body["run_id"] == run_id
    assert body["stage"] == "scrolling"
    assert body["scroll_y"] == 200
    assert body["progress"] == 50
    assert body["viewport"] == "tablet"

    # 4. Fallback to run_store for historical completed run
    req = RunCreateRequest(url="https://historical.com", viewports=["desktop"])
    created_run = run_store.create(req)
    run_store.update_run(created_run.run_id, status="completed", message="Audited historical run")

    resp_hist = get_preview_status(created_run.run_id)
    assert resp_hist.status_code == 200
    hist_body = json.loads(resp_hist.body)
    assert hist_body["run_id"] == created_run.run_id
    assert hist_body["stage"] == "completed"
    assert hist_body["progress"] == 100


def test_api_get_preview_frame_and_headers():
    """Test get_preview_frame returns JPEG bytes and telemetry headers."""
    run_id = "run_frame_header_test"
    dummy_jpeg = b"\xff\xd8\xff\xe0dummy_jpeg"
    preview_service.init_run(run_id, "https://frame-test.com")
    preview_service.publish_frame(
        run_id=run_id,
        frame_bytes=dummy_jpeg,
        scroll_y=450,
        max_scroll_y=1500,
        progress=60,
        stage="scrolling",
        viewport="mobile",
    )

    resp = get_preview_frame(run_id)
    assert resp.status_code == 200
    assert resp.body == dummy_jpeg
    assert resp.headers["content-type"] == "image/jpeg"
    assert resp.headers["x-scan-progress"] == "60"
    assert resp.headers["x-scan-scroll-y"] == "450"
    assert resp.headers["x-scan-max-scroll"] == "1500"
    assert resp.headers["x-scan-viewport"] == "mobile"


def test_navigator_execute_live_scroll_preview_mocked():
    """Test BrowserNavigator._execute_live_scroll_preview with mocked Playwright page."""
    from navigation.navigator import BrowserNavigator

    mock_page = MagicMock()
    # Mock page dimensions: scrollHeight=1600, clientHeight=800 -> maxScrollY=800
    mock_page.evaluate.side_effect = [
        {"scrollHeight": 1600, "clientHeight": 800, "maxScrollY": 800},
        [
            {
                "id": "broken_img_0",
                "category": "broken_image",
                "severity": "medium",
                "selector": "#broken-banner",
                "box": {"x": 20, "y": 60, "width": 300, "height": 150},
            }
        ],
        None,  # scrollTo step 1
        None,  # scrollTo step 2
        None,  # scrollTo step 3
        None,  # scrollTo step 4
        None,  # scrollTo 0 (return to top)
    ]
    mock_page.screenshot.return_value = b"\xff\xd8\xff\xe0fake_jpeg_frame"

    run_id = "run_mock_nav_scroll_test"
    preset = {"width": 1280, "height": 800}

    defects = BrowserNavigator._execute_live_scroll_preview(
        page=mock_page,
        run_id=run_id,
        viewport_name="desktop",
        preset=preset,
    )

    assert len(defects) == 1
    assert defects[0]["selector"] == "#broken-banner"
    assert mock_page.screenshot.call_count >= 1

    # Verify frame was published to preview_service
    state = preview_service.get_preview(run_id)
    assert state is not None
    assert state["viewport"] == "desktop"
    assert state["stage"] == "scrolling"
    assert len(state["defects"]) == 1
