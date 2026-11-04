
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from time import perf_counter

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)

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

    # Existing diagnostics
    console_errors: list = field(default_factory=list)
    page_errors: list = field(default_factory=list)

    # Day 2 additions
    response_status: Optional[int] = None
    navigation_duration_ms: Optional[float] = None
    failed_requests: list = field(default_factory=list)

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
    def _failed_result(
        url,
        run_id,
        error,
        navigation_duration_ms=None,
        failed_requests=None,
        response_status=None
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
            console_errors=[],
            page_errors=[],
            error=error
        )

    def navigate(self, url: str, run_id: str) -> NavigationResult:

        # Step 1: Validate URL
        if not self._is_valid_url(url):
            return self._failed_result(
                url, run_id, "Invalid URL"
            )

        # Step 2: Validate run ID
        if not isinstance(run_id, str) or not run_id.strip():
            return self._failed_result(
                url, run_id, "run_id is required"
            )

        console_errors = []
        page_errors = []
        failed_requests = []

        response_status = None
        start_time = perf_counter()

        try:
            with sync_playwright() as playwright:

                browser = playwright.chromium.launch(
                    headless=self.headless
                )

                try:
                    page = browser.new_page(
                        viewport={
                            "width": 1280,
                            "height": 720
                        }
                    )

                    # Step 3: Capture console errors
                    page.on(
                        "console",
                        lambda message: console_errors.append(
                            message.text
                        ) if message.type == "error" else None
                    )

                    # Step 4: Capture JavaScript errors
                    page.on(
                        "pageerror",
                        lambda error: page_errors.append(str(error))
                    )

                    # Step 5: Capture failed network requests
                    def capture_failed_request(request):
                        failure = request.failure

                        failed_requests.append({
                            "url": request.url,
                            "method": request.method,
                            "failure": str(failure)
                            if failure else "Request failed"
                        })

                    page.on(
                        "requestfailed",
                        capture_failed_request
                    )

                    try:
                        # Step 6: Navigate to the website
                        response = page.goto(
                            url,
                            wait_until="domcontentloaded",
                            timeout=self.timeout_ms
                        )

                        # Step 7: Capture HTTP response status
                        if response is not None:
                            response_status = response.status

                        # Allow a short time for page rendering
                        page.wait_for_timeout(500)

                        # Step 8: Capture page metadata
                        page_title = page.title()
                        viewport = page.viewport_size

                        timestamp = self._current_timestamp()

                        # Step 9: Capture full-page screenshot
                        screenshot_path = (
                            ScreenshotManager.save_screenshot(
                                page,
                                run_id
                            )
                        )

                        # Step 10: Capture DOM snapshot
                        dom_snapshot_path = (
                            DOMCapture.save_dom_snapshot(
                                page,
                                run_id
                            )
                        )

                        # Step 11: Verify evidence files
                        if not Path(screenshot_path).exists():
                            raise FileNotFoundError(
                                "Screenshot file was not created"
                            )

                        if not Path(dom_snapshot_path).exists():
                            raise FileNotFoundError(
                                "DOM snapshot file was not created"
                            )

                        # Step 12: Calculate navigation duration
                        duration = round(
                            (perf_counter() - start_time) * 1000,
                            2
                        )

                        # Step 13: Return structured result
                        return NavigationResult(
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
                            response_status=response_status,
                            navigation_duration_ms=duration,
                            failed_requests=list(failed_requests),
                            error=None
                        )

                    except PlaywrightTimeoutError:
                        duration = round(
                            (perf_counter() - start_time) * 1000,
                            2
                        )

                        return self._failed_result(
                            url,
                            run_id,
                            "Navigation timeout",
                            navigation_duration_ms=duration,
                            failed_requests=failed_requests,
                            response_status=response_status
                        )

                    except Exception as error:
                        duration = round(
                            (perf_counter() - start_time) * 1000,
                            2
                        )

                        return self._failed_result(
                            url,
                            run_id,
                            str(error),
                            navigation_duration_ms=duration,
                            failed_requests=failed_requests,
                            response_status=response_status
                        )

                finally:
                    browser.close()

        except Exception as error:
            duration = round(
                (perf_counter() - start_time) * 1000,
                2
            )

            return self._failed_result(
                url,
                run_id,
                str(error),
                navigation_duration_ms=duration,
                failed_requests=failed_requests,
                response_status=response_status
            )
