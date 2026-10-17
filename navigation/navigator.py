"""
Browser Agent -

Responsibilities:
- Launch browser
- Navigate to URL
- Collect page metadata
- Handle failures
- Close resources cleanly
"""

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
    screenshot_path: Optional[str] = None
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

                screenshot_path = ScreenshotManager.save_screenshot(
                    page,
                    run_id
                )

                return NavigationResult(
                    status="success",
                    run_id=run_id,
                    url=page.url,
                    page_title=title,
                    screenshot_path=screenshot_path
                )

        except PlaywrightTimeoutError as exc:

            return NavigationResult(
                status="failed",
                run_id=run_id,
                url=url,
                page_title="",
                error="Navigation timeout"
            )

        except Exception as exc:

            return NavigationResult(
                status="failed",
                run_id=run_id,
                url=url,
                page_title="",
                error=str(exc)
            )

        finally:

            try:
                if browser:
                    browser.close()
            except Exception:
                pass