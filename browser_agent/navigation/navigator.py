"""Browser Agent.

Responsibilities:
- Launch browser
- Navigate to URL
- Collect page metadata
- Capture browser console errors
- Capture page exceptions
- Capture screenshot evidence
- Capture DOM evidence
- Validate generated artifacts
- Handle failures
- Close resources cleanly
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sys
import asyncio
from typing import Optional, Union

try:
    from browser_agent.evidence.dom_capture import DOMCapture
    from browser_agent.screenshots.screenshot_manager import ScreenshotManager
except ImportError:
    from evidence.dom_capture import DOMCapture
    from screenshots.screenshot_manager import ScreenshotManager

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


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
    run_id: str
    url: str
    page_title: str
    captured_at: str
    viewport: dict
    viewport_name: Optional[str] = "desktop"

    screenshot_path: Optional[str] = None
    dom_snapshot_path: Optional[str] = None

    console_errors: list = None
    page_errors: list = None

    status: str = "success"
    error: Optional[str] = None


class BrowserNavigator:

    def __init__(
        self,
        timeout_ms: int = 30000,
        headless: bool = True,
    ):
        self.timeout_ms = timeout_ms
        self.headless = headless

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
        viewport: Optional[str | dict] = "desktop",
    ) -> NavigationResult:

        browser = None

        console_errors = []
        page_errors = []

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

        # URL Validation
        if not (
            url.startswith("http://")
            or url.startswith("https://")
        ):
            return NavigationResult(
                status="failed",
                run_id=run_id,
                url=url,
                page_title="",
                captured_at=datetime.now(timezone.utc).isoformat(),
                viewport={},
                viewport_name=vp_name,
                console_errors=[],
                page_errors=[],
                error="Invalid URL",
            )

        # run_id Validation
        if not run_id:
            return NavigationResult(
                status="failed",
                run_id="",
                url=url,
                page_title="",
                captured_at=datetime.now(timezone.utc).isoformat(),
                viewport={},
                viewport_name=vp_name,
                console_errors=[],
                page_errors=[],
                error="run_id is required",
            )

        try:
            if sys.platform == "win32":
                if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
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

                # Browser Console Errors
                page.on(
                    "console",
                    lambda msg: console_errors.append(msg.text)
                    if msg.type == "error"
                    else None,
                )

                # JavaScript Exceptions
                page.on("pageerror", lambda exc: page_errors.append(str(exc)))

                # Primary navigation: wait for page load, then attempt brief networkidle settlement
                try:
                    page.goto(url, wait_until="load", timeout=self.timeout_ms)
                except PlaywrightTimeoutError:
                    # On heavy or streaming sites (e.g. Amazon, media-rich sites), window.onload can be delayed;
                    # fallback to domcontentloaded to ensure structural DOM is captured
                    page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_ms)

                # Attempt brief wait for network idle (up to 3 seconds), but ignore timeout if network stays active
                try:
                    page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass

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

                title = page.title()
                viewport_size = page.viewport_size if page.viewport_size else {}
                capture_time = datetime.now(timezone.utc).isoformat()

                screenshot_path = ScreenshotManager.save_screenshot(
                    page, run_id, stage="before", viewport=vp_name
                )
                if not Path(screenshot_path).exists():
                    raise FileNotFoundError("Screenshot file not created")

                dom_snapshot_path = DOMCapture.save_dom_snapshot(
                    page, run_id, stage="before", viewport=vp_name
                )
                if not Path(dom_snapshot_path).exists():
                    raise FileNotFoundError("DOM snapshot file not created")

                return NavigationResult(
                    status="success",
                    run_id=run_id,
                    url=page.url,
                    page_title=title,
                    captured_at=capture_time,
                    viewport=viewport_size,
                    viewport_name=vp_name,
                    screenshot_path=screenshot_path,
                    dom_snapshot_path=dom_snapshot_path,
                    console_errors=console_errors,
                    page_errors=page_errors,
                )

        except PlaywrightTimeoutError:
            return NavigationResult(
                status="failed",
                run_id=run_id,
                url=url,
                page_title="",
                captured_at=datetime.now(timezone.utc).isoformat(),
                viewport={},
                console_errors=console_errors,
                page_errors=page_errors,
                error="Navigation timeout",
            )

        except Exception as exc:
            error_str = str(exc).strip() or f"{exc.__class__.__name__}: browser navigation failed"
            return NavigationResult(
                status="failed",
                run_id=run_id,
                url=url,
                page_title="",
                captured_at=datetime.now(timezone.utc).isoformat(),
                viewport={},
                console_errors=console_errors,
                page_errors=page_errors,
                error=error_str,
            )

        finally:
            try:
                if browser:
                    browser.close()
            except Exception:
                pass
