
"""
Browser Agent

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

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from evidence.dom_capture import DOMCapture
from screenshots.screenshot_manager import ScreenshotManager

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


@dataclass
class NavigationResult:
    run_id: str
    url: str
    page_title: str
    captured_at: str
    viewport: dict

    screenshot_path: Optional[str] = None
    dom_snapshot_path: Optional[str] = None

    console_errors: list = field(default_factory=list)
    page_errors: list = field(default_factory=list)

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
    def _current_timestamp() -> str:
        """Return the current UTC timestamp in ISO 8601 format."""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _failed_result(
        url: str,
        run_id: str,
        error: str,
        console_errors: Optional[list] = None,
        page_errors: Optional[list] = None,
    ) -> NavigationResult:
        """Create a consistent result for failed navigation."""
        return NavigationResult(
            status="failed",
            run_id=run_id,
            url=url,
            page_title="",
            captured_at=BrowserNavigator._current_timestamp(),
            viewport={},
            console_errors=(
                console_errors if console_errors is not None else []
            ),
            page_errors=(
                page_errors if page_errors is not None else []
            ),
            error=error,
        )

    def navigate(
        self,
        url: str,
        run_id: str,
    ) -> NavigationResult:
        browser = None

        console_errors = []
        page_errors = []

        # Validate URL.
        if not isinstance(url, str) or not url.strip():
            return self._failed_result(
                url=str(url),
                run_id=str(run_id) if run_id is not None else "",
                error="Invalid URL",
            )

        url = url.strip()

        if not url.startswith(("http://", "https://")):
            return self._failed_result(
                url=url,
                run_id=str(run_id) if run_id is not None else "",
                error="Invalid URL",
            )

        # Validate run_id.
        if not isinstance(run_id, str) or not run_id.strip():
            return self._failed_result(
                url=url,
                run_id="",
                error="run_id is required",
            )

        run_id = run_id.strip()

        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=self.headless
                )

                page = browser.new_page()

                # Collect browser console errors.
                page.on(
                    "console",
                    lambda message: console_errors.append(message.text)
                    if message.type == "error"
                    else None,
                )

                # Collect uncaught JavaScript exceptions.
                page.on(
                    "pageerror",
                    lambda exception: page_errors.append(str(exception)),
                )

                # Navigate to the requested URL.
                page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=self.timeout_ms,
                )

                # Collect page metadata.
                title = page.title()

                viewport = page.viewport_size or {}

                capture_time = self._current_timestamp()

                # Capture screenshot evidence.
                screenshot_path = ScreenshotManager.save_screenshot(
                    page,
                    run_id,
                )

                if (
                    not screenshot_path
                    or not Path(screenshot_path).is_file()
                ):
                    raise FileNotFoundError(
                        "Screenshot file not created"
                    )

                # Capture DOM evidence.
                dom_snapshot_path = DOMCapture.save_dom_snapshot(
                    page,
                    run_id,
                )

                if (
                    not dom_snapshot_path
                    or not Path(dom_snapshot_path).is_file()
                ):
                    raise FileNotFoundError(
                        "DOM snapshot file not created"
                    )

                return NavigationResult(
                    status="success",
                    run_id=run_id,
                    url=page.url,
                    page_title=title,
                    captured_at=capture_time,
                    viewport=viewport,
                    screenshot_path=str(screenshot_path),
                    dom_snapshot_path=str(dom_snapshot_path),
                    console_errors=console_errors.copy(),
                    page_errors=page_errors.copy(),
                    error=None,
                )

        except PlaywrightTimeoutError:
            return self._failed_result(
                url=url,
                run_id=run_id,
                error="Navigation timeout",
                console_errors=console_errors.copy(),
                page_errors=page_errors.copy(),
            )

        except Exception as exc:
            return self._failed_result(
                url=url,
                run_id=run_id,
                error=str(exc),
                console_errors=console_errors.copy(),
                page_errors=page_errors.copy(),
            )

        finally:
            # Ensure browser resources are cleaned up.
            if browser is not None:
                try:
                    browser.close()
                except Exception:
                    pass
