
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from uuid import uuid4

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

from evidence.dom_capture import DOMCapture
from screenshots.screenshot_manager import ScreenshotManager


@dataclass
class NavigationResult:
    status: str
    url: str
    run_id: str = ""
    page_title: Optional[str] = None
    captured_at: Optional[str] = None
    timestamp: Optional[str] = None
    viewport: Optional[dict] = None
    screenshot_path: Optional[str] = None
    dom_snapshot_path: Optional[str] = None
    console_errors: list = field(default_factory=list)
    page_errors: list = field(default_factory=list)
    error: Optional[str] = None


class BrowserNavigator:

    def __init__(self, timeout_ms=30000, headless=True):
        self.timeout_ms = timeout_ms
        self.headless = headless

    @staticmethod
    def _current_timestamp():
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _is_valid_url(url):
        if not isinstance(url, str) or not url.strip():
            return False

        try:
            parsed = urlparse(url.strip())
            return (
                parsed.scheme in ("http", "https")
                and bool(parsed.netloc)
                and bool(parsed.hostname)
            )
        except Exception:
            return False

    @staticmethod
    def _failed_result(url, run_id, error):
        timestamp = BrowserNavigator._current_timestamp()

        return NavigationResult(
            status="failed",
            url=url if isinstance(url, str) else "",
            run_id=run_id if isinstance(run_id, str) else "",
            captured_at=timestamp,
            timestamp=timestamp,
            console_errors=[],
            page_errors=[],
            error=error
        )

    def navigate(self, url: str, run_id: str) -> NavigationResult:

        # Validate URL
        if not self._is_valid_url(url):
            return self._failed_result(url, run_id, "Invalid URL")

        # Validate run ID
        if not isinstance(run_id, str) or not run_id.strip():
            return self._failed_result(url, run_id, "run_id is required")

        console_errors = []
        page_errors = []

        timestamp = self._current_timestamp()

        try:
            with sync_playwright() as playwright:

                browser = playwright.chromium.launch(
                    headless=self.headless
                )

                page = browser.new_page(
                    viewport={"width": 1280, "height": 720}
                )

                # Capture browser console errors
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type == "error" else None
                )

                # Capture JavaScript errors
                page.on(
                    "pageerror",
                    lambda error: page_errors.append(str(error))
                )

                try:
                    response = page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=self.timeout_ms
                    )

                    # Allow a short time for page rendering
                    page.wait_for_timeout(500)

                    page_title = page.title()

                    viewport = page.viewport_size

                    timestamp = self._current_timestamp()

                    # Create screenshot
                    screenshot_path = ScreenshotManager.save_screenshot(
                        page,
                        run_id
                    )

                    # Capture DOM
                    dom_snapshot_path = DOMCapture.save_dom_snapshot(
                        page,
                        run_id
                    )

                    # Check whether evidence files exist
                    if not Path(screenshot_path).exists():
                        raise FileNotFoundError(
                            "Screenshot file was not created"
                        )

                    if not Path(dom_snapshot_path).exists():
                        raise FileNotFoundError(
                            "DOM snapshot file was not created"
                        )

                    result = NavigationResult(
                        status="success",
                        url=url,
                        run_id=run_id,
                        page_title=page_title,
                        captured_at=timestamp,
                        timestamp=timestamp,
                        viewport=viewport,
                        screenshot_path=screenshot_path,
                        dom_snapshot_path=dom_snapshot_path,
                        console_errors=list(console_errors),
                        page_errors=list(page_errors),
                        error=None
                    )

                    browser.close()
                    return result

                except PlaywrightTimeoutError:
                    browser.close()
                    return self._failed_result(
                        url,
                        run_id,
                        "Navigation timeout"
                    )

                except Exception as error:
                    browser.close()
                    return self._failed_result(
                        url,
                        run_id,
                        str(error)
                    )

        except Exception as error:
            return self._failed_result(
                url,
                run_id,
                str(error)
            )
