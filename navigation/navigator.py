
import asyncio
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from typing import Optional

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

from evidence.dom_capture import DOMCapture
from screenshots.screenshot_manager import ScreenshotManager
from navigation.url_validator import validate_url, validate_run_id


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

    def navigate(self, url: str, run_id: str) -> NavigationResult:

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
                    page = browser.new_page(
                        viewport={
                            "width": self.viewport_width,
                            "height": self.viewport_height,
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
                            )
                        )

                        # Capture DOM snapshot
                        dom_snapshot_path = (
                            DOMCapture.save_dom_snapshot(
                                page,
                                run_id,
                                stage="before",
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
