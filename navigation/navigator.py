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

from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError
)


@dataclass
class NavigationResult:
    status: str
    url: str
    page_title: str
    error: Optional[str] = None


class BrowserNavigator:

    def __init__(
        self,
        timeout_ms: int = 30000,
        headless: bool = True
    ):
        self.timeout_ms = timeout_ms
        self.headless = headless

    def navigate(self, url: str) -> NavigationResult:

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

                return NavigationResult(
                    status="success",
                    url=page.url,
                    page_title=title
                )

        except PlaywrightTimeoutError:

            return NavigationResult(
                status="failed",
                url=url,
                page_title="",
                error="Navigation timeout"
            )

        except Exception as exc:

            return NavigationResult(
                status="failed",
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