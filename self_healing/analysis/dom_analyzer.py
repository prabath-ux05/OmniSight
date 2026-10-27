"""DOM snapshot analyzer for identifying target elements and locator drift."""

from __future__ import annotations

import re
from typing import Optional
from bs4 import BeautifulSoup, Tag

SELECTOR_TOKEN_SPLIT_REGEX = re.compile(r"[#._\-:\[\]=\"'\s]+")


def extract_selector_tokens(selector: str) -> set[str]:
    """Break a CSS/XPath selector into semantic word tokens.

    Example:
        '#btn-trigger-self-heal' -> {'btn', 'trigger', 'self', 'heal'}
        'button[data-testid="submit-cta"]' -> {'button', 'data', 'testid', 'submit', 'cta'}
    """
    raw_tokens = SELECTOR_TOKEN_SPLIT_REGEX.split(selector.lower())
    # Filter common short punctuation and noise
    return {
        t for t in raw_tokens
        if len(t) >= 3 and t not in {"button", "input", "div", "span", "data", "testid", "class", "type"}
    }


def find_target_element_in_dom(
    soup: BeautifulSoup,
    original_selector: str,
) -> Optional[Tag]:
    """Find the intended target Tag in the DOM snapshot.

    1. First tries direct selector resolution (if element exists in DOM but selector needs healing).
    2. If not found directly, performs semantic token and attribute matching across interactive elements.

    Args:
        soup: Parsed BeautifulSoup DOM snapshot.
        original_selector: Original selector string that failed or requires repair.

    Returns:
        The matched Tag in the DOM, or None if no plausible element was found.
    """
    clean_selector = original_selector.strip()
    if not clean_selector:
        return None

    # Step 1: Direct match attempt
    try:
        direct_matches = soup.select(clean_selector)
        if len(direct_matches) == 1:
            return direct_matches[0]
        if len(direct_matches) > 1:
            # If multiple match the original, return the first as target for disambiguation
            return direct_matches[0]
    except Exception:
        # Invalid selector syntax, fall through to semantic matching
        pass

    # Step 2: Extract search tokens from selector
    tokens = extract_selector_tokens(clean_selector)
    if not tokens:
        return None

    # Determine expected tag if discernible
    expected_tag: Optional[str] = None
    first_token = clean_selector.split()[0].split(".")[0].split("#")[0].split("[")[0].lower()
    if first_token in {"button", "input", "a", "select", "textarea", "img", "table", "form", "div", "span"}:
        expected_tag = first_token

    # Candidate elements pool (focus on interactive and meaningful structural tags)
    search_tags = [expected_tag] if expected_tag else ["button", "a", "input", "select", "textarea", "div", "span"]
    candidates = soup.find_all(search_tags)

    best_element: Optional[Tag] = None
    highest_score = 0

    for elem in candidates:
        score = 0
        attrs = elem.attrs

        # 1. Check data attributes for token overlap
        for attr_name, attr_val in attrs.items():
            if not isinstance(attr_val, str):
                continue
            val_lower = attr_val.lower()
            for token in tokens:
                if token in val_lower:
                    if "testid" in attr_name or "qa" in attr_name or "cy" in attr_name:
                        score += 5  # Strong testid match
                    elif attr_name in {"id", "name"}:
                        score += 4  # ID/name match
                    elif attr_name == "class":
                        score += 2  # Class match
                    else:
                        score += 1

        # 2. Check inner text
        elem_text = elem.get_text(separator=" ", strip=True).lower()
        for token in tokens:
            if token in elem_text:
                score += 3

        # 3. Exact tag preference
        if expected_tag and elem.name.lower() == expected_tag:
            score += 2

        if score > highest_score and score >= 3:
            highest_score = score
            best_element = elem

    return best_element
