"""Locator verification against DOM snapshots.

Guarantees that no locator candidate is claimed as repaired unless it
actually and uniquely resolves to the intended target element in the DOM.
"""

from __future__ import annotations

from typing import Any, Optional
from bs4 import BeautifulSoup, Tag

from self_healing.models import LiveVerificationResult, RepairValidationResult


def validate_locator_in_dom(
    soup: BeautifulSoup,
    selector: str,
    expected_element: Optional[Tag] = None,
) -> RepairValidationResult:
    """Validate a candidate selector against a parsed DOM snapshot.

    Args:
        soup: Parsed BeautifulSoup DOM snapshot.
        selector: CSS or attribute selector string to validate.
        expected_element: Optional BeautifulSoup Tag reference that the selector
            is expected to resolve to. If provided, ensures the resolved element
            is identical to expected_element.

    Returns:
        RepairValidationResult with resolvability, match count, and message.
    """
    if not selector or not selector.strip():
        return RepairValidationResult(
            is_valid=False,
            matches=0,
            validation_message="Selector is empty or blank.",
        )

    try:
        elements = soup.select(selector)
    except Exception as exc:
        return RepairValidationResult(
            is_valid=False,
            matches=0,
            validation_message=f"Invalid selector syntax: {exc}",
        )

    match_count = len(elements)

    if match_count == 0:
        return RepairValidationResult(
            is_valid=False,
            matches=0,
            validation_message=f"Selector '{selector}' matched 0 elements in the DOM snapshot.",
        )

    if match_count > 1:
        return RepairValidationResult(
            is_valid=False,
            matches=match_count,
            resolved_tag=elements[0].name,
            resolved_html_snippet=str(elements[0])[:120],
            validation_message=f"Ambiguous selector: matches {match_count} elements in DOM.",
        )

    # Exactly 1 match
    resolved = elements[0]

    # If an expected element is provided, verify it resolves to that specific element
    if expected_element is not None and resolved is not expected_element:
        return RepairValidationResult(
            is_valid=False,
            matches=1,
            resolved_tag=resolved.name,
            resolved_html_snippet=str(resolved)[:120],
            validation_message="Selector resolved 1 element, but not the targeted element.",
        )

    snippet = str(resolved)
    if len(snippet) > 120:
        snippet = snippet[:117] + "..."

    return RepairValidationResult(
        is_valid=True,
        matches=1,
        resolved_tag=resolved.name,
        resolved_html_snippet=snippet,
        validation_message=f"Uniquely resolved 1 <{resolved.name}> element in DOM snapshot.",
    )


def count_matches_in_dom(soup: BeautifulSoup, selector: str) -> int:
    """Return the number of elements matching selector in DOM (0 if invalid syntax)."""
    if not selector or not selector.strip():
        return 0
    try:
        return len(soup.select(selector))
    except Exception:
        return 0


def verify_locator_on_live_page(
    target_url: str,
    selector: str,
    timeout_ms: int = 15000,
    headless: bool = True,
    page_instance: Optional[Any] = None,
) -> LiveVerificationResult:
    """Test a candidate locator against a fresh live page navigation using Playwright.

    Args:
        target_url: The webpage URL to navigate to and inspect.
        selector: Candidate CSS or attribute selector string to test.
        timeout_ms: Maximum navigation and query timeout in milliseconds.
        headless: Whether to run headless browser.
        page_instance: Optional already-open Playwright Page instance.

    Returns:
        LiveVerificationResult indicating resolvability and match count on the live page.
    """
    if not selector or not selector.strip():
        return LiveVerificationResult(
            attempted=False,
            is_verified=False,
            matches=0,
            target_url=target_url,
            validation_message="Cannot verify empty or blank selector on live page.",
        )

    if not target_url or not (target_url.startswith("http://") or target_url.startswith("https://")):
        return LiveVerificationResult(
            attempted=False,
            is_verified=False,
            matches=0,
            target_url=target_url,
            validation_message="Target URL is missing or invalid for fresh-page verification.",
        )

    # 1. If an active page instance is passed, inspect directly
    if page_instance is not None:
        try:
            elements = page_instance.locator(selector)
            match_count = elements.count()
            tag_name = None
            if match_count == 1:
                try:
                    tag_name = elements.first.evaluate("el => el.tagName.toLowerCase()")
                except Exception:
                    tag_name = None

            is_unique = (match_count == 1)
            msg = (
                f"Uniquely verified 1 <{tag_name or 'element'}> on live page '{target_url}'."
                if is_unique
                else f"Live page match count is {match_count} (expected 1 unique match)."
            )
            return LiveVerificationResult(
                attempted=True,
                is_verified=is_unique,
                matches=match_count,
                target_url=target_url,
                resolved_tag=tag_name,
                validation_message=msg,
            )
        except Exception as exc:
            return LiveVerificationResult(
                attempted=True,
                is_verified=False,
                matches=0,
                target_url=target_url,
                validation_message=f"Live element evaluation error: {exc}",
            )

    # 2. Otherwise launch fresh Playwright browser to inspect live target page
    try:
        import sys
        import asyncio
        if sys.platform == "win32":
            if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            try:
                page = browser.new_page()
                page.goto(target_url, wait_until="domcontentloaded", timeout=timeout_ms)
                elements = page.locator(selector)
                match_count = elements.count()
                tag_name = None
                if match_count == 1:
                    try:
                        tag_name = elements.first.evaluate("el => el.tagName.toLowerCase()")
                    except Exception:
                        tag_name = None

                is_unique = (match_count == 1)
                msg = (
                    f"Uniquely verified 1 <{tag_name or 'element'}> on fresh live page '{target_url}'."
                    if is_unique
                    else f"Fresh live page match count is {match_count} (expected 1 unique match)."
                )
                return LiveVerificationResult(
                    attempted=True,
                    is_verified=is_unique,
                    matches=match_count,
                    target_url=target_url,
                    resolved_tag=tag_name,
                    validation_message=msg,
                )
            finally:
                browser.close()
    except Exception as exc:
        is_timeout = "Timeout" in type(exc).__name__
        msg = (
            f"Fresh-page navigation timed out after {timeout_ms}ms."
            if is_timeout
            else f"Live fresh-page verification error: {exc}"
        )
        return LiveVerificationResult(
            attempted=True,
            is_verified=False,
            matches=0,
            target_url=target_url,
            validation_message=msg,
        )
