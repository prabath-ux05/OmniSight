"""Deterministic scoring, ranking, and deduplication for candidate locators."""

from __future__ import annotations

import re
from typing import Sequence
from bs4 import BeautifulSoup

from self_healing.models import CandidateLocator, RepairStrategy
from self_healing.verification.locator_validator import count_matches_in_dom

STRATEGY_BASE_CONFIDENCE: dict[RepairStrategy, float] = {
    RepairStrategy.DATA_ATTRIBUTE: 0.95,
    RepairStrategy.STABLE_ID: 0.90,
    RepairStrategy.ACCESSIBLE_ROLE_NAME: 0.85,
    RepairStrategy.UNIQUE_TEXT: 0.80,
    RepairStrategy.SEMANTIC_CSS: 0.70,
    RepairStrategy.HIERARCHICAL: 0.65,
    RepairStrategy.FALLBACK: 0.50,
}

HAS_TEXT_REGEX = re.compile(r'^([a-zA-Z0-9_\-]+)?:has-text\("([^"]+)"\)$')


def count_text_matches(soup: BeautifulSoup, tag_name: str | None, text_value: str) -> int:
    """Count how many elements in the DOM have the given tag and exact/partial text."""
    tags_to_check = soup.find_all(tag_name if tag_name else True)
    count = 0
    clean_search = text_value.strip().lower()
    for t in tags_to_check:
        t_text = t.get_text(separator=" ", strip=True).lower()
        if clean_search in t_text:
            count += 1
    return count


def score_and_rank_candidates(
    raw_candidates: Sequence[tuple[str, RepairStrategy, str]],
    soup: BeautifulSoup,
) -> list[CandidateLocator]:
    """Score, validate uniqueness, and rank candidate locators deterministically.

    Args:
        raw_candidates: Sequence of (selector, strategy, description) tuples.
        soup: Parsed BeautifulSoup DOM snapshot.

    Returns:
        List of CandidateLocator objects, ordered from best to worst.
    """
    seen_selectors: set[str] = set()
    ranked_candidates: list[CandidateLocator] = []

    for selector, strategy, description in raw_candidates:
        clean_sel = selector.strip()
        if not clean_sel or clean_sel in seen_selectors:
            continue
        seen_selectors.add(clean_sel)

        # Handle Playwright-style :has-text selectors vs standard CSS
        text_match = HAS_TEXT_REGEX.match(clean_sel)
        if text_match:
            tag_name = text_match.group(1) or None
            text_val = text_match.group(2)
            match_count = count_text_matches(soup, tag_name, text_val)
        else:
            match_count = count_matches_in_dom(soup, clean_sel)

        base_conf = STRATEGY_BASE_CONFIDENCE.get(strategy, 0.50)

        if match_count == 1:
            is_unique = True
            confidence = base_conf
        elif match_count > 1:
            is_unique = False
            # Significant penalty for non-unique / ambiguous locators
            confidence = max(0.10, round(base_conf - 0.40, 2))
        else:
            is_unique = False
            confidence = 0.0

        ranked_candidates.append(
            CandidateLocator(
                selector=clean_sel,
                strategy=strategy,
                confidence=round(confidence, 2),
                is_unique=is_unique,
                match_count=match_count,
                description=description,
            )
        )

    # Deterministic multi-key sorting:
    # 1. Uniqueness (unique locators always outrank ambiguous or non-matching ones)
    # 2. Confidence score descending
    # 3. Match count proximity to 1 (1 is ideal)
    # 4. Brevity (shorter selectors preferred on ties)
    # 5. Selector string alphabetical (deterministic tie-breaker)
    ranked_candidates.sort(
        key=lambda c: (
            1 if c.is_unique else 0,
            c.confidence,
            -abs(c.match_count - 1),
            -len(c.selector),
            c.selector,
        ),
        reverse=True,
    )

    return ranked_candidates
