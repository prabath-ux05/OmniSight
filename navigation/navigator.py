
import asyncio
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Optional, Union

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from evidence.dom_capture import DOMCapture
from screenshots.screenshot_manager import ScreenshotManager
from navigation.url_validator import validate_url, validate_run_id


VIEWPORT_PRESETS = {
    "desktop": {
        "width": 1280,
        "height": 800,
        "is_mobile": False,
        "has_touch": False,
        "device_scale_factor": 1.0,
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    },
    "tablet": {
        "width": 768,
        "height": 1024,
        "is_mobile": True,
        "has_touch": True,
        "device_scale_factor": 2.0,
        "user_agent": "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    },
    "mobile": {
        "width": 375,
        "height": 667,
        "is_mobile": True,
        "has_touch": True,
        "device_scale_factor": 2.0,
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    },
}


@dataclass
class NavigationResult:
    status: str
    url: str
    run_id: str = ""
    page_title: Optional[str] = None
    captured_at: Optional[str] = None
    timestamp: Optional[str] = None
    viewport: Optional[dict] = None
    viewport_name: Optional[str] = "desktop"
    screenshot_path: Optional[str] = None
    dom_snapshot_path: Optional[str] = None

    console_errors: list = field(default_factory=list)
    page_errors: list = field(default_factory=list)

    response_status: Optional[int] = None
    navigation_duration_ms: Optional[float] = None
    failed_requests: list = field(default_factory=list)

    error: Optional[str] = None


class BrowserNavigator:

    def __init__(
        self,
        timeout_ms=30000,
        headless=True,
        viewport_width=1280,
        viewport_height=720,
        render_wait_ms=500,
    ):
        if timeout_ms <= 0:
            raise ValueError("timeout_ms must be greater than zero")

        if viewport_width <= 0 or viewport_height <= 0:
            raise ValueError("Viewport dimensions must be positive")

        if render_wait_ms < 0:
            raise ValueError("render_wait_ms cannot be negative")

        self.timeout_ms = timeout_ms
        self.headless = headless
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.render_wait_ms = render_wait_ms

    @staticmethod
    def _current_timestamp():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _is_valid_url(url):
        is_valid, _ = validate_url(url)
        return is_valid

    @staticmethod
    def _ensure_windows_proactor_policy():
        if sys.platform == "win32":
            current_policy = asyncio.get_event_loop_policy()

            if not isinstance(
                current_policy,
                asyncio.WindowsProactorEventLoopPolicy,
            ):
                asyncio.set_event_loop_policy(
                    asyncio.WindowsProactorEventLoopPolicy()
                )

    @staticmethod
    def _failed_result(
        url,
        run_id,
        error,
        navigation_duration_ms=None,
        failed_requests=None,
        response_status=None,
        console_errors=None,
        page_errors=None,
    ):
        timestamp = BrowserNavigator._current_timestamp()

        return NavigationResult(
            status="failed",
            url=url if isinstance(url, str) else "",
            run_id=run_id if isinstance(run_id, str) else "",
            captured_at=timestamp,
            timestamp=timestamp,
            navigation_duration_ms=navigation_duration_ms,
            failed_requests=list(failed_requests or []),
            response_status=response_status,
            console_errors=list(console_errors or []),
            page_errors=list(page_errors or []),
            error=error,
        )

    @staticmethod
    def _execute_live_scroll_preview(page, run_id: str, viewport_name: str, preset: dict) -> list[dict]:
        """Perform automatic top-to-bottom page scrolling, capture live preview frames and detect defect coordinates."""
        try:
            from backend.app.services.preview_service import preview_service
        except ImportError:
            preview_service = None

        vp_w = preset.get("width", 1280)
        vp_h = preset.get("height", 800)

        # 1. Query real document height and scroll boundary
        try:
            metrics = page.evaluate("""() => {
                const body = document.body || {};
                const doc = document.documentElement || {};
                const scrollHeight = Math.max(
                    body.scrollHeight || 0,
                    doc.scrollHeight || 0,
                    body.offsetHeight || 0,
                    doc.offsetHeight || 0,
                    window.innerHeight || 0
                );
                const clientHeight = window.innerHeight || 800;
                return {
                    scrollHeight: Math.round(scrollHeight),
                    clientHeight: Math.round(clientHeight),
                    maxScrollY: Math.max(0, Math.round(scrollHeight - clientHeight))
                };
            }""")
        except Exception:
            metrics = {"scrollHeight": vp_h, "clientHeight": vp_h, "maxScrollY": 0}

        max_scroll_y = int(metrics.get("maxScrollY", 0))

        # 2. Extract visible candidate defects and their bounding boxes
        defects = []
        try:
            defects = page.evaluate("""() => {
                const found = [];
                // 1. Broken images (missing src or 0 natural dimensions after load)
                const imgs = Array.from(document.querySelectorAll('img'));
                imgs.forEach((img, idx) => {
                    const src = img.getAttribute('src');
                    const isBroken = (!src || !src.trim() || (img.complete && img.naturalWidth === 0));
                    if (isBroken) {
                        const r = img.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) {
                            found.push({
                                id: `preview_broken_img_${idx}`,
                                category: 'broken_image',
                                severity: 'medium',
                                selector: img.id ? `#${img.id}` : (img.className ? `img.${img.className.trim().split(/\\s+/)[0]}` : 'img'),
                                description: 'DOM/Visual: Image has missing source URL or zero natural dimensions.',
                                box: {
                                    x: Math.round(r.left + window.scrollX),
                                    y: Math.round(r.top + window.scrollY),
                                    width: Math.round(r.width),
                                    height: Math.round(r.height),
                                }
                            });
                        }
                    }
                });
                // 2. Horizontal layout overflow elements
                const candidateContainers = Array.from(document.querySelectorAll('div, section, p, table, pre, main, article, header, footer'));
                candidateContainers.forEach((el, idx) => {
                    if (found.length >= 8) return;
                    if (el.scrollWidth > el.clientWidth + 15 && el.clientWidth > 80) {
                        const r = el.getBoundingClientRect();
                        if (r.width > 0 && r.height > 0) {
                            found.push({
                                id: `preview_overflow_${idx}`,
                                category: 'layout_overflow',
                                severity: 'high',
                                selector: el.id ? `#${el.id}` : (el.className ? `.${el.className.trim().split(/\\s+/)[0]}` : el.tagName.toLowerCase()),
                                description: 'DOM/Visual: Content element exceeds viewport boundary (horizontal layout overflow).',
                                box: {
                                    x: Math.round(r.left + window.scrollX),
                                    y: Math.round(r.top + window.scrollY),
                                    width: Math.round(r.width),
                                    height: Math.round(r.height),
                                }
                            });
                        }
                    }
                });
                return found;
            }""")
        except Exception:
            defects = []

        # 3. Progressive scrolling top-to-bottom in steps
        if max_scroll_y > 0:
            num_steps = max(2, min(6, int(max_scroll_y / 400) + 1))
            scroll_positions = [int(round(i * (max_scroll_y / num_steps))) for i in range(num_steps + 1)]
        else:
            scroll_positions = [0]

        for idx, y in enumerate(scroll_positions):
            try:
                page.evaluate(f"window.scrollTo({{ top: {y}, left: 0, behavior: 'instant' }})")
                page.wait_for_timeout(120)
                frame_bytes = page.screenshot(type="jpeg", quality=55)
            except Exception:
                frame_bytes = None

            if frame_bytes and preview_service and run_id:
                ratio = (y / max_scroll_y) if max_scroll_y > 0 else 1.0
                step_pct = int(15 + ratio * 65)  # 15% -> 80%
                msg = f"Scanning {viewport_name} viewport: {y}px / {max_scroll_y}px ({int(ratio * 100)}%)"
                preview_service.publish_frame(
                    run_id=run_id,
                    frame_bytes=frame_bytes,
                    scroll_y=y,
                    max_scroll_y=max_scroll_y,
                    progress=step_pct,
                    stage="scrolling",
                    viewport=viewport_name,
                    viewport_width=vp_w,
                    viewport_height=vp_h,
                    message=msg,
                    defects=defects,
                )

        # 4. Scroll back to top before capturing primary evidence screenshot
        try:
            page.evaluate("window.scrollTo({ top: 0, left: 0, behavior: 'instant' })")
            page.wait_for_timeout(100)
        except Exception:
            pass

        return defects

    def navigate(
        self,
        url: str,
        run_id: str,
        viewport: Optional[Union[str, dict]] = "desktop",
    ) -> NavigationResult:

        # Resolve viewport preset
        vp_name = "desktop"
        if isinstance(viewport, str):
            candidate = viewport.strip().lower()
            if candidate in VIEWPORT_PRESETS:
                vp_name = candidate
                preset = VIEWPORT_PRESETS[candidate]
            else:
                preset = VIEWPORT_PRESETS["desktop"]
        elif isinstance(viewport, dict):
            vp_name = "custom"
            preset = {**VIEWPORT_PRESETS["desktop"], **viewport}
        else:
            preset = VIEWPORT_PRESETS["desktop"]

        # Step 1: Validate URL
        is_valid_url, url_message = validate_url(url)

        if not is_valid_url:
            return self._failed_result(url, run_id, url_message)

        url = url.strip()

        # Step 2: Validate run ID
        is_valid_run_id, run_id_message = validate_run_id(run_id)

        if not is_valid_run_id:
            return self._failed_result(url, run_id, run_id_message)

        run_id = run_id.strip()

        console_errors = []
        page_errors = []
        failed_requests = []

        response_status = None
        start_time = perf_counter()

        try:
            # Set the Windows event-loop policy before Playwright starts.
            self._ensure_windows_proactor_policy()

            with sync_playwright() as playwright:

                browser = playwright.chromium.launch(
                    headless=self.headless
                )

                try:
                    context_kwargs = {
                        "viewport": {
                            "width": preset["width"],
                            "height": preset["height"],
                        },
                        "is_mobile": preset.get("is_mobile", False),
                        "has_touch": preset.get("has_touch", False),
                        "device_scale_factor": preset.get("device_scale_factor", 1.0),
                    }
                    if preset.get("user_agent"):
                        context_kwargs["user_agent"] = preset["user_agent"]

                    try:
                        context = browser.new_context(**context_kwargs)
                        page = context.new_page()
                    except (TypeError, AttributeError):
                        page = browser.new_page(
                            viewport={
                                "width": preset["width"],
                                "height": preset["height"],
                            }
                        )

                    # Capture browser console errors
                    page.on(
                        "console",
                        lambda message: console_errors.append(
                            message.text
                        ) if message.type == "error" else None,
                    )

                    # Capture JavaScript errors
                    page.on(
                        "pageerror",
                        lambda error: page_errors.append(str(error)),
                    )

                    # Capture failed network requests
                    def capture_failed_request(request):
                        failure = request.failure

                        failed_requests.append({
                            "url": request.url,
                            "method": request.method,
                            "failure": str(failure)
                            if failure else "Request failed",
                        })

                    page.on(
                        "requestfailed",
                        capture_failed_request,
                    )

                    try:
                        # Navigate to the website
                        response = page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=self.timeout_ms,
                        )

                        # Capture HTTP response status
                        if response is not None:
                            response_status = response.status

                        # Allow dynamic content to render
                        if self.render_wait_ms > 0:
                            page.wait_for_timeout(self.render_wait_ms)

                        # Real-time Live Preview: Progressive Top-to-Bottom Scrolling & Frame Streaming
                        try:
                            self._execute_live_scroll_preview(
                                page=page,
                                run_id=run_id,
                                viewport_name=vp_name,
                                preset=preset,
                            )
                        except Exception:
                            pass

                        # Capture page metadata
                        page_title = page.title()
                        viewport = page.viewport_size
                        timestamp = self._current_timestamp()

                        # Capture screenshot
                        screenshot_path = (
                            ScreenshotManager.save_screenshot(
                                page,
                                run_id,
                                stage="before",
                                viewport=vp_name,
                            )
                        )

                        # Capture DOM snapshot
                        dom_snapshot_path = (
                            DOMCapture.save_dom_snapshot(
                                page,
                                run_id,
                                stage="before",
                                viewport=vp_name,
                            )
                        )

                        # Verify evidence files
                        if (
                            not screenshot_path
                            or not Path(screenshot_path).is_file()
                        ):
                            raise FileNotFoundError(
                                "Screenshot file was not created"
                            )

                        if (
                            not dom_snapshot_path
                            or not Path(dom_snapshot_path).is_file()
                        ):
                            raise FileNotFoundError(
                                "DOM snapshot file was not created"
                            )

                        # Calculate navigation duration
                        duration = round(
                            (perf_counter() - start_time) * 1000,
                            2,
                        )

                        # Identify HTTP errors
                        http_error = (
                            response_status is not None
                            and response_status >= 400
                        )

                        error_message = (
                            f"HTTP error: {response_status}"
                            if http_error
                            else None
                        )

                        # Return structured result
                        return NavigationResult(
                            status="failed" if http_error else "success",
                            url=page.url,
                            run_id=run_id,
                            page_title=page_title,
                            captured_at=timestamp,
                            timestamp=timestamp,
                            viewport=viewport,
                            viewport_name=vp_name,
                            screenshot_path=screenshot_path,
                            dom_snapshot_path=dom_snapshot_path,
                            console_errors=list(console_errors),
                            page_errors=list(page_errors),
                            response_status=response_status,
                            navigation_duration_ms=duration,
                            failed_requests=list(failed_requests),
                            error=error_message,
                        )

                    except PlaywrightTimeoutError:
                        duration = round(
                            (perf_counter() - start_time) * 1000,
                            2,
                        )

                        return self._failed_result(
                            url,
                            run_id,
                            "Navigation timeout",
                            navigation_duration_ms=duration,
                            failed_requests=failed_requests,
                            response_status=response_status,
                            console_errors=console_errors,
                            page_errors=page_errors,
                        )

                    except Exception as error:
                        duration = round(
                            (perf_counter() - start_time) * 1000,
                            2,
                        )

                        return self._failed_result(
                            url,
                            run_id,
                            str(error) or type(error).__name__,
                            navigation_duration_ms=duration,
                            failed_requests=failed_requests,
                            response_status=response_status,
                            console_errors=console_errors,
                            page_errors=page_errors,
                        )

                finally:
                    browser.close()

        except Exception as error:
            duration = round(
                (perf_counter() - start_time) * 1000,
                2,
            )

            return self._failed_result(
                url,
                run_id,
                str(error) or type(error).__name__,
                navigation_duration_ms=duration,
                failed_requests=failed_requests,
                response_status=response_status,
                console_errors=console_errors,
                page_errors=page_errors,
            )
