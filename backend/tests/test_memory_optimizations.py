"""Focused unit and integration tests for OmniSight Production Memory Optimization — Batch 1.

Covers:
1. Playwright lifecycle cleanup with try/finally (page.close, context.close, browser.close).
2. DEFAULT_CHROMIUM_ARGS flags and customizable launch_args.
3. Browser instance reuse across viewports via context manager (start_session/close).
4. Configurable maximum screenshot height (MAX_SCREENSHOT_HEIGHT, clipping on oversized pages, full_page on normal pages).
5. Process-wide inspection concurrency limit of one (queueing, lock acquisition, duplicate rejection, timeout).
6. Preview cache and raw frame buffer release upon run completion and failure.
"""

from contextlib import nullcontext
from pathlib import Path
import threading
import time
from unittest.mock import MagicMock, patch
import pytest

from backend.app.schemas.runs import RunCreateRequest
from backend.app.services.orchestrator import RunOrchestrator, run_orchestrator
from backend.app.services.preview_service import LivePreviewService, preview_service
from backend.app.services.run_store import run_store
from navigation.navigator import (
    DEFAULT_CHROMIUM_ARGS,
    BrowserNavigator,
    NavigationResult,
)
from screenshots.screenshot_manager import (
    DEFAULT_MAX_SCREENSHOT_HEIGHT,
    ScreenshotManager,
    get_max_screenshot_height,
)


@pytest.fixture(autouse=True)
def cleanup_memory_test_state():
    """Reset run_store, preview_service, and orchestrator concurrency lock between tests."""
    run_store.clear()
    preview_service.clear()
    run_orchestrator.reset()
    yield
    run_store.clear()
    preview_service.clear()
    run_orchestrator.reset()


@pytest.fixture(scope="module", autouse=True)
def sample_test_artifacts():
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
# 1 & 2. Chromium Args & Playwright try/finally Cleanup
# =============================================================================

def test_default_chromium_args_contains_container_safe_flags():
    """Verify DEFAULT_CHROMIUM_ARGS includes required low-memory / container flags."""
    assert "--disable-dev-shm-usage" in DEFAULT_CHROMIUM_ARGS
    assert "--no-sandbox" in DEFAULT_CHROMIUM_ARGS
    assert "--disable-setuid-sandbox" in DEFAULT_CHROMIUM_ARGS
    assert "--disable-gpu" in DEFAULT_CHROMIUM_ARGS
    assert "--disable-software-rasterizer" in DEFAULT_CHROMIUM_ARGS
    assert "--no-zygote" in DEFAULT_CHROMIUM_ARGS


def test_browser_navigator_custom_launch_args():
    """Verify BrowserNavigator allows overriding or extending launch_args."""
    custom_args = ["--disable-dev-shm-usage", "--mute-audio"]
    nav = BrowserNavigator(launch_args=custom_args)
    assert nav.launch_args == custom_args


def test_browser_navigator_page_and_context_closed_on_success(tmp_path):
    """Verify page and context are closed in finally block upon successful navigation."""
    mock_playwright = MagicMock()
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()

    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page

    mock_response = MagicMock()
    mock_response.status = 200
    mock_page.goto.return_value = mock_response

    mock_page.url = "https://example.com"
    mock_page.title.return_value = "Example"
    mock_page.viewport_size = {"width": 1280, "height": 800}
    mock_page.evaluate.return_value = {"maxScrollY": 0}

    sc_path = tmp_path / "before.png"
    sc_path.write_bytes(b"fake_png")
    dom_path = tmp_path / "dom.html"
    dom_path.write_text("<html></html>")

    with patch("navigation.navigator.sync_playwright") as mock_sp, \
         patch("navigation.navigator.ScreenshotManager.save_screenshot", return_value=str(sc_path)), \
         patch("navigation.navigator.DOMCapture.save_dom_snapshot", return_value=str(dom_path)):

        mock_sp.return_value.__enter__.return_value = mock_playwright
        mock_sp.return_value.start.return_value = mock_playwright
        nav = BrowserNavigator()
        res = nav.navigate("https://example.com", "run_test_cleanup_01")

        assert res.status == "success"
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()


def test_browser_navigator_page_and_context_closed_on_page_failure():
    """Verify page, context, and standalone browser are closed even when page.goto raises an error."""
    mock_playwright = MagicMock()
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()

    mock_playwright.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_page.goto.side_effect = RuntimeError("Simulated navigation crash")

    with patch("navigation.navigator.sync_playwright") as mock_sp:
        mock_sp.return_value.__enter__.return_value = mock_playwright
        mock_sp.return_value.start.return_value = mock_playwright
        nav = BrowserNavigator()
        res = nav.navigate("https://example.com", "run_test_fail_cleanup")

        assert res.status == "failed"
        assert "Simulated navigation crash" in res.error
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()


# =============================================================================
# 3. Browser Reuse Across Viewports
# =============================================================================

def test_browser_reuse_across_viewports_in_context_manager(tmp_path):
    """Verify browser instance is launched once and reused across multiple navigate() calls."""
    mock_playwright = MagicMock()
    mock_browser = MagicMock()
    mock_browser.is_connected.return_value = True

    mock_context_1 = MagicMock()
    mock_page_1 = MagicMock()
    mock_page_1.url = "https://example.com"
    mock_page_1.title.return_value = "Page 1"
    mock_page_1.viewport_size = {"width": 1280, "height": 800}
    mock_page_1.evaluate.return_value = {"maxScrollY": 0}
    mock_resp_1 = MagicMock()
    mock_resp_1.status = 200
    mock_page_1.goto.return_value = mock_resp_1

    mock_context_2 = MagicMock()
    mock_page_2 = MagicMock()
    mock_page_2.url = "https://example.com"
    mock_page_2.title.return_value = "Page 2"
    mock_page_2.viewport_size = {"width": 768, "height": 1024}
    mock_page_2.evaluate.return_value = {"maxScrollY": 0}
    mock_resp_2 = MagicMock()
    mock_resp_2.status = 200
    mock_page_2.goto.return_value = mock_resp_2

    mock_browser.new_context.side_effect = [mock_context_1, mock_context_2]
    mock_context_1.new_page.return_value = mock_page_1
    mock_context_2.new_page.return_value = mock_page_2
    mock_playwright.chromium.launch.return_value = mock_browser

    sc_path = tmp_path / "before.png"
    sc_path.write_bytes(b"fake_png")
    dom_path = tmp_path / "dom.html"
    dom_path.write_text("<html></html>")

    with patch("navigation.navigator.sync_playwright") as mock_sp, \
         patch("navigation.navigator.ScreenshotManager.save_screenshot", return_value=str(sc_path)), \
         patch("navigation.navigator.DOMCapture.save_dom_snapshot", return_value=str(dom_path)):

        mock_sp.return_value.__enter__.return_value = mock_playwright
        mock_sp.return_value.start.return_value = mock_playwright
        nav = BrowserNavigator()

        with nav:
            # 1. Desktop viewport
            res1 = nav.navigate("https://example.com", "run_reuse_01", viewport="desktop")
            assert res1.status == "success"
            mock_page_1.close.assert_called_once()
            mock_context_1.close.assert_called_once()
            # Browser must NOT be closed yet while in context session
            mock_browser.close.assert_not_called()

            # 2. Tablet viewport
            res2 = nav.navigate("https://example.com", "run_reuse_01", viewport="tablet")
            assert res2.status == "success"
            mock_page_2.close.assert_called_once()
            mock_context_2.close.assert_called_once()
            mock_browser.close.assert_not_called()

        # After exiting with nav context manager, browser and playwright are stopped
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        # Verify launch was called exactly ONCE across both viewports
        assert mock_playwright.chromium.launch.call_count == 1


# =============================================================================
# 4. Configurable Maximum Screenshot Height
# =============================================================================

def test_default_max_screenshot_height():
    """Verify default maximum screenshot height is 4000px."""
    assert DEFAULT_MAX_SCREENSHOT_HEIGHT == 4000
    assert get_max_screenshot_height() == 4000


def test_max_screenshot_height_env_override(monkeypatch):
    """Verify MAX_SCREENSHOT_HEIGHT env var overrides the default."""
    monkeypatch.setenv("MAX_SCREENSHOT_HEIGHT", "2500")
    assert get_max_screenshot_height() == 2500

    # 0 disables capping
    monkeypatch.setenv("MAX_SCREENSHOT_HEIGHT", "0")
    assert get_max_screenshot_height() == 0

    # Non-integer falls back to default
    monkeypatch.setenv("MAX_SCREENSHOT_HEIGHT", "invalid")
    assert get_max_screenshot_height() == 4000


def test_save_screenshot_normal_page_uses_full_page(tmp_path):
    """Verify normal-sized page (height <= max_height) uses full_page=True."""
    mock_page = MagicMock()
    mock_page.url = "https://example.com"
    mock_page.title.return_value = "Normal Page"
    mock_page.viewport_size = {"width": 1280, "height": 800}
    # Page height is 1500px, which is <= 4000
    mock_page.evaluate.return_value = 1500

    def fake_screenshot(path, **kwargs):
        # Write valid PNG header (1280x1500)
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # 16-byte header + width (1280) and height (1500) in big-endian
        header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x05\x00\x00\x00\x05\xdc\x08\x06\x00\x00\x00"
        p.write_bytes(header)

    mock_page.screenshot.side_effect = fake_screenshot

    out = ScreenshotManager.save_screenshot(
        mock_page,
        run_id="run_normal_page",
        artifact_root=str(tmp_path),
        viewport="desktop",
        max_height=4000,
    )
    assert Path(out).is_file()

    # Verify page.screenshot was called with full_page=True
    calls = mock_page.screenshot.call_args_list
    assert len(calls) == 1
    assert calls[0].kwargs.get("full_page") is True
    assert "clip" not in calls[0].kwargs


def test_save_screenshot_oversized_page_clips_height(tmp_path):
    """Verify oversized page (height > max_height) clips to max_height to save RAM."""
    mock_page = MagicMock()
    mock_page.url = "https://example.com/tall"
    mock_page.title.return_value = "Tall Page"
    mock_page.viewport_size = {"width": 1280, "height": 800}
    # Page height is 9000px, which exceeds max_height of 3000
    mock_page.evaluate.return_value = 9000

    def fake_screenshot(path, **kwargs):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        # 1280x3000 header
        header = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x05\x00\x00\x00\x0b\xb8\x08\x06\x00\x00\x00"
        p.write_bytes(header)

    mock_page.screenshot.side_effect = fake_screenshot

    out = ScreenshotManager.save_screenshot(
        mock_page,
        run_id="run_tall_page",
        artifact_root=str(tmp_path),
        viewport="desktop",
        max_height=3000,
    )
    assert Path(out).is_file()

    # Verify page.screenshot was called with clip={"x": 0, "y": 0, "width": 1280, "height": 3000}
    calls = mock_page.screenshot.call_args_list
    assert len(calls) == 1
    assert "clip" in calls[0].kwargs
    assert calls[0].kwargs["clip"] == {"x": 0, "y": 0, "width": 1280, "height": 3000}
    assert "full_page" not in calls[0].kwargs


# =============================================================================
# 5. Process-Wide Inspection Concurrency Limiter
# =============================================================================

def test_orchestrator_concurrency_lock_queues_and_serializes_runs():
    """Verify when run 1 is active, run 2 is queued, and proceeds only after run 1 finishes."""
    run1 = run_store.create(RunCreateRequest(url="https://example.com/site1"))
    run2 = run_store.create(RunCreateRequest(url="https://example.com/site2"))

    run1_started = threading.Event()
    run1_release = threading.Event()
    execution_order = []

    def mock_detector_1(vi):
        execution_order.append(f"start_{vi.run_id}")
        run1_started.set()
        run1_release.wait(timeout=5.0)
        execution_order.append(f"end_{vi.run_id}")
        return []

    def mock_detector_2(vi):
        execution_order.append(f"start_{vi.run_id}")
        execution_order.append(f"end_{vi.run_id}")
        return []

    mock_nav_result_1 = NavigationResult(
        run_id=run1.run_id,
        url=run1.url,
        page_title="Site 1",
        captured_at="2026-11-21T00:00:00Z",
        viewport={"width": 1280, "height": 800},
        screenshot_path="artifacts/test_sample_run/before.png",
        dom_snapshot_path="artifacts/test_sample_run/dom.html",
        status="success",
    )
    mock_nav_result_2 = NavigationResult(
        run_id=run2.run_id,
        url=run2.url,
        page_title="Site 2",
        captured_at="2026-11-21T00:00:00Z",
        viewport={"width": 1280, "height": 800},
        screenshot_path="artifacts/test_sample_run/before.png",
        dom_snapshot_path="artifacts/test_sample_run/dom.html",
        status="success",
    )

    def side_effect_nav(url, run_id, **kwargs):
        if run_id == run1.run_id:
            return mock_nav_result_1
        return mock_nav_result_2

    with patch("navigation.navigator.BrowserNavigator.navigate", side_effect=side_effect_nav):
        t1 = threading.Thread(
            target=run_orchestrator.execute_run,
            args=(run1.run_id, run1.url),
            kwargs={"detector": mock_detector_1, "viewports": ["desktop"]},
        )
        t2 = threading.Thread(
            target=run_orchestrator.execute_run,
            args=(run2.run_id, run2.url),
            kwargs={"detector": mock_detector_2, "viewports": ["desktop"]},
        )

        t1.start()
        # Wait until run1 enters detector and holds lock
        assert run1_started.wait(timeout=3.0)

        # Run 1 is now active
        assert run_orchestrator.is_run_active(run1.run_id) is True
        assert run_orchestrator.is_busy() is True

        # Launch run 2 concurrently
        t2.start()
        time.sleep(0.1)

        # Run 2 should be in queued status waiting for run 1 to finish
        r2_state = run_store.get(run2.run_id)
        assert r2_state.status == "queued"
        assert "waiting for active inspection" in r2_state.message

        # Now release run 1
        run1_release.set()
        t1.join(timeout=3.0)
        t2.join(timeout=3.0)

        # Both runs must finish successfully
        final_1 = run_store.get(run1.run_id)
        final_2 = run_store.get(run2.run_id)
        assert final_1.status == "completed"
        assert final_2.status == "completed"

        # Verify strict serial execution order
        assert execution_order == [
            f"start_{run1.run_id}",
            f"end_{run1.run_id}",
            f"start_{run2.run_id}",
            f"end_{run2.run_id}",
        ]


def test_orchestrator_concurrency_lock_timeout_handles_gracefully():
    """Verify run times out gracefully if another run holds lock beyond lock_timeout_seconds."""
    run1 = run_store.create(RunCreateRequest(url="https://example.com/blocking"))
    run2 = run_store.create(RunCreateRequest(url="https://example.com/waiting"))

    orch = RunOrchestrator(lock_timeout_seconds=0.2)

    # Manually hold lock to simulate long-running inspection
    assert orch._concurrency_lock.acquire(blocking=True)
    orch._active_run_id = run1.run_id

    try:
        # execute_run for run2 will wait up to 0.2s and then timeout
        orch.execute_run(run2.run_id, run2.url)

        r2 = run_store.get(run2.run_id)
        assert r2.status == "failed"
        assert "timed out waiting" in r2.error
        assert "timeout" in r2.message.lower()
    finally:
        orch.reset()


def test_orchestrator_rejects_duplicate_active_run():
    """Verify invoking execute_run on a run that is ALREADY active is safely ignored."""
    run = run_store.create(RunCreateRequest(url="https://example.com/site"))
    run_orchestrator._active_run_id = run.run_id

    try:
        # Calling execute_run on already active run_id should exit early without modifying run
        run_orchestrator.execute_run(run.run_id, run.url)
        assert run_store.get(run.run_id).status == "queued"
    finally:
        run_orchestrator.reset()


# =============================================================================
# 6. Preview Cache & Frame Memory Release
# =============================================================================

def test_preview_service_close_run_releases_raw_and_base64_frames():
    """Verify close_run releases raw bytes and sets frame_base64 to None."""
    service = LivePreviewService(max_cached_runs=5)
    run_id = "run_test_mem_release"

    service.init_run(run_id, "https://example.com")
    dummy_frame = b"\xff\xd8\xff\xe0dummy_data"
    service.publish_frame(run_id, dummy_frame, scroll_y=100, max_scroll_y=500)

    # Pre-close checks
    assert service.get_frame_bytes(run_id) == dummy_frame
    state_before = service.get_preview(run_id)
    assert state_before["frame_base64"] is not None

    # Call close_run
    service.close_run(run_id, release_frames=True)

    # Raw frame bytes must be released (None)
    assert service.get_frame_bytes(run_id) is None

    # State metadata must remain available for status polling, but frame_base64 is None
    state_after = service.get_preview(run_id)
    assert state_after is not None
    assert state_after["frame_base64"] is None
    assert state_after["run_id"] == run_id


def test_preview_service_release_run_frames_helper():
    """Verify release_run_frames explicitly frees image buffers."""
    service = LivePreviewService()
    run_id = "run_helper_test"
    service.init_run(run_id, "https://example.com")
    service.publish_frame(run_id, b"binary_frame_bytes", scroll_y=0, max_scroll_y=200)

    assert service.get_frame_bytes(run_id) is not None
    service.release_run_frames(run_id)
    assert service.get_frame_bytes(run_id) is None
    assert service.get_preview(run_id)["frame_base64"] is None


def test_orchestrator_releases_preview_frames_upon_run_completion():
    """Verify preview_service.close_run is executed at the end of execute_run."""
    run = run_store.create(RunCreateRequest(url="https://example.com/completed"))
    preview_service.init_run(run.run_id, run.url)
    preview_service.publish_frame(run.run_id, b"preview_frame", scroll_y=50, max_scroll_y=100)

    mock_nav_result = NavigationResult(
        run_id=run.run_id,
        url=run.url,
        page_title="Complete",
        captured_at="2026-11-21T00:00:00Z",
        viewport={"width": 1280, "height": 800},
        screenshot_path="artifacts/test_sample_run/before.png",
        dom_snapshot_path="artifacts/test_sample_run/dom.html",
        status="success",
    )

    with patch("navigation.navigator.BrowserNavigator.navigate", return_value=mock_nav_result):
        run_orchestrator.execute_run(run.run_id, run.url, detector=lambda vi: [])

    # The run completed: raw frame bytes should be evicted from memory
    assert preview_service.get_frame_bytes(run.run_id) is None
    preview_state = preview_service.get_preview(run.run_id)
    assert preview_state["stage"] == "completed"
    assert preview_state["frame_base64"] is None
