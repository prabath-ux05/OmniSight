"""
Browser Agent -

Responsibilities:
- Launch browser
- Navigate to URL
- Collect page metadata
- Handle failures
- Close resources cleanly
"""
from datetime import datetime, timezone
from evidence.dom_capture import DOMCapture
from dataclasses import dataclass
from typing import Optional
from screenshots.screenshot_manager import ScreenshotManager


from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)


@dataclass
class NavigationResult:
    status: str
    run_id: str
    url: str
    page_title: str
    captured_at: str
    viewport: dict
    screenshot_path: Optional[str] = None
    dom_snapshot_path: Optional[str] = None
    error: Optional[str] = None


class BrowserNavigator:

    def __init__(
        self,
        timeout_ms: int = 30000,
        headless: bool = True
    ):
        self.timeout_ms = timeout_ms
        self.headless = headless

    def navigate(self, url: str, run_id: str) -> NavigationResult:

        browser = None

        try:
            with sync_playwright() as p:

                browser = p.chromium.launch(
                    headless=self.headless
                )

                page = browser.new_page()

                page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=self.timeout_ms
                )

                title = page.title()

                viewport = page.viewport_size

                capture_time = datetime.now(
                    timezone.utc
                ).isoformat()

                screenshot_path = ScreenshotManager.save_screenshot(
                    page,
                    run_id
                )

                dom_snapshot_path = DOMCapture.save_dom_snapshot(
                    page,
                    run_id
                )

                return NavigationResult(
                    status="success",
                    run_id=run_id,
                    url=page.url,
                    page_title=title,
                    captured_at=capture_time,
                    viewport=viewport,
                    screenshot_path=screenshot_path,
                    dom_snapshot_path=dom_snapshot_path
                )

        except PlaywrightTimeoutError as exc:

            return NavigationResult(
                status="failed",
                run_id=run_id,
                url=url,
                page_title="",
                captured_at=datetime.now(
                    timezone.utc
                ).isoformat(),
                viewport={},
                error="Navigation timeout"
            )

        except Exception as exc:

            return NavigationResult(
                status="failed",
                run_id=run_id,
                url=url,
                page_title="",
                captured_at=datetime.now(
                    timezone.utc
                ).isoformat(),
                viewport={},
                error=str(exc)
            )

        finally:

            try:
                if browser:
                    browser.close()
            except Exception:
                pass