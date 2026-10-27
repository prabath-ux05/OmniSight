"""Self-Healing Locator Repair Engine.

Consumes verified UI defect findings and captured DOM evidence to
deterministically analyze, generate, rank, and validate replacement locators.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union
from bs4 import BeautifulSoup

from self_healing.analysis.dom_analyzer import find_target_element_in_dom
from self_healing.code_generation.locator_generator import generate_candidate_locators_for_element
from self_healing.code_generation.locator_ranker import score_and_rank_candidates
from self_healing.models import (
    CandidateLocator,
    LiveVerificationResult,
    RepairResult,
    RepairStrategy,
    RepairValidationResult,
)
from self_healing.verification.locator_validator import (
    validate_locator_in_dom,
    verify_locator_on_live_page,
)


# Accepted category identifiers for missing visible elements across schemas
MISSING_ELEMENT_CATEGORIES = {
    "missing_visible_element",
    "missing_element",
    "missing",
}


def _extract_finding_data(finding: Any) -> tuple[str, str, str, Optional[str]]:
    """Extract (finding_id, category, selector, dom_snapshot_path) from various finding types."""
    finding_id = "unknown_finding"
    category = "unknown_category"
    selector = ""
    dom_snapshot_path: Optional[str] = None

    if isinstance(finding, dict):
        finding_id = finding.get("finding_id", "unknown_finding")
        category = str(finding.get("category") or finding.get("defect_category") or "unknown_category")
        selector = str(finding.get("selector") or "").strip()
        evidence = finding.get("evidence") or {}
        if isinstance(evidence, dict):
            dom_snapshot_path = evidence.get("dom_snapshot_path")
        elif hasattr(evidence, "dom_snapshot_path"):
            dom_snapshot_path = getattr(evidence, "dom_snapshot_path", None)
    else:
        # Pydantic FindingResponse or Dataclass InspectionFinding
        finding_id = getattr(finding, "finding_id", "unknown_finding")
        raw_cat = getattr(finding, "category", None) or getattr(finding, "defect_category", None)
        category = getattr(raw_cat, "value", str(raw_cat or "unknown_category"))
        selector = str(getattr(finding, "selector", "") or "").strip()
        evidence = getattr(finding, "evidence", None)
        if evidence:
            dom_snapshot_path = getattr(evidence, "dom_snapshot_path", None)
        if not dom_snapshot_path and hasattr(finding, "metadata"):
            meta = getattr(finding, "metadata", {}) or {}
            dom_snapshot_path = meta.get("dom_snapshot_path") or meta.get("evidence", {}).get("dom_snapshot_path")

    return finding_id, category.lower(), selector, dom_snapshot_path


class SelfHealingEngine:
    """Orchestrator for autonomous locator repair."""

    def __init__(self) -> None:
        pass

    def repair_finding(
        self,
        finding: Any,
        dom_content: Optional[str] = None,
        dom_path: Optional[Union[str, Path]] = None,
        verify_live: bool = False,
        target_url: Optional[str] = None,
        page_instance: Optional[Any] = None,
    ) -> RepairResult:
        """Inspect a defect finding and repair its selector using captured DOM evidence.

        Args:
            finding: Real FindingResponse, InspectionFinding, or dict.
            dom_content: Optional raw HTML string (overrides file read).
            dom_path: Optional explicit file path to DOM HTML snapshot.
            verify_live: If True, navigate to target_url to verify the repaired locator on the live DOM.
            target_url: Live webpage URL for fresh-page verification.
            page_instance: Optional active Playwright Page instance.

        Returns:
            Structured RepairResult with candidates, best locator, snapshot validation, and live verification.
        """

        finding_id, category, original_selector, evidence_dom_path = _extract_finding_data(finding)

        # 1. Category check: only missing visible elements are candidates for locator repair
        if category not in MISSING_ELEMENT_CATEGORIES:
            return RepairResult(
                finding_id=finding_id,
                original_selector=original_selector,
                repaired=False,
                best_locator=None,
                confidence=0.0,
                strategy=None,
                candidate_locators=[],
                validation=None,
                reason=f"Finding category '{category}' is not a missing visible element; locator repair skipped.",
            )

        # 2. Selector check
        if not original_selector:
            return RepairResult(
                finding_id=finding_id,
                original_selector="",
                repaired=False,
                best_locator=None,
                confidence=0.0,
                strategy=None,
                candidate_locators=[],
                validation=None,
                reason="Original selector is missing or empty; cannot identify target element.",
            )

        # 3. Resolve DOM HTML content
        html: Optional[str] = None
        if dom_content is not None:
            html = dom_content
        else:
            effective_path = dom_path or evidence_dom_path
            if not effective_path:
                return RepairResult(
                    finding_id=finding_id,
                    original_selector=original_selector,
                    repaired=False,
                    best_locator=None,
                    confidence=0.0,
                    strategy=None,
                    candidate_locators=[],
                    validation=RepairValidationResult(
                        is_valid=False,
                        matches=0,
                        validation_message="No DOM snapshot path recorded in finding evidence.",
                    ),
                    reason="DOM evidence snapshot path is missing from finding.",
                )

            p = Path(effective_path)
            if not p.is_file():
                return RepairResult(
                    finding_id=finding_id,
                    original_selector=original_selector,
                    repaired=False,
                    best_locator=None,
                    confidence=0.0,
                    strategy=None,
                    candidate_locators=[],
                    validation=RepairValidationResult(
                        is_valid=False,
                        matches=0,
                        validation_message=f"DOM snapshot file not found on disk: {p}",
                    ),
                    reason=f"DOM evidence snapshot file not found on disk: '{p}'.",
                )

            try:
                html = p.read_text(encoding="utf-8")
            except Exception as exc:
                return RepairResult(
                    finding_id=finding_id,
                    original_selector=original_selector,
                    repaired=False,
                    best_locator=None,
                    confidence=0.0,
                    strategy=None,
                    candidate_locators=[],
                    validation=RepairValidationResult(
                        is_valid=False,
                        matches=0,
                        validation_message=f"Failed to read DOM snapshot: {exc}",
                    ),
                    reason=f"Failed to read DOM evidence snapshot file: {exc}",
                )

        if not html or not html.strip():
            return RepairResult(
                finding_id=finding_id,
                original_selector=original_selector,
                repaired=False,
                best_locator=None,
                confidence=0.0,
                strategy=None,
                candidate_locators=[],
                validation=RepairValidationResult(
                    is_valid=False,
                    matches=0,
                    validation_message="DOM HTML content is empty.",
                ),
                reason="DOM evidence snapshot content is completely empty.",
            )

        # 4. Parse DOM
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception as exc:
            return RepairResult(
                finding_id=finding_id,
                original_selector=original_selector,
                repaired=False,
                best_locator=None,
                confidence=0.0,
                strategy=None,
                candidate_locators=[],
                validation=None,
                reason=f"Malformed DOM HTML could not be parsed: {exc}",
            )

        # 5. Analyze DOM to locate target element
        target_element = find_target_element_in_dom(soup, original_selector)
        if target_element is None:
            return RepairResult(
                finding_id=finding_id,
                original_selector=original_selector,
                repaired=False,
                best_locator=None,
                confidence=0.0,
                strategy=None,
                candidate_locators=[],
                validation=RepairValidationResult(
                    is_valid=False,
                    matches=0,
                    validation_message=f"No matching element found for '{original_selector}'.",
                ),
                reason=f"No suitable replacement element matching '{original_selector}' was found in the DOM snapshot.",
            )

        # 6. Generate multi-strategy candidate locators
        raw_candidates = generate_candidate_locators_for_element(target_element, soup)
        if not raw_candidates:
            return RepairResult(
                finding_id=finding_id,
                original_selector=original_selector,
                repaired=False,
                best_locator=None,
                confidence=0.0,
                strategy=None,
                candidate_locators=[],
                validation=RepairValidationResult(
                    is_valid=False,
                    matches=0,
                    validation_message="No attributes or selectors could be synthesized.",
                ),
                reason="Target element lacked sufficient attributes or context to synthesize alternative locators.",
            )

        # 7. Score and rank candidates deterministically
        ranked_candidates = score_and_rank_candidates(raw_candidates, soup)

        # 8. Find best candidate that strictly resolves uniquely in the DOM
        best_candidate: Optional[CandidateLocator] = None
        for candidate in ranked_candidates:
            if candidate.is_unique and candidate.match_count == 1:
                best_candidate = candidate
                break

        if best_candidate is None:
            # All generated candidates were ambiguous (matches > 1) or non-matching (matches == 0)
            return RepairResult(
                finding_id=finding_id,
                original_selector=original_selector,
                repaired=False,
                best_locator=None,
                confidence=0.0,
                strategy=None,
                candidate_locators=ranked_candidates,
                validation=RepairValidationResult(
                    is_valid=False,
                    matches=ranked_candidates[0].match_count if ranked_candidates else 0,
                    validation_message="All generated candidates are ambiguous or non-unique in DOM snapshot.",
                ),
                reason="No candidate locator uniquely resolved the intended element without ambiguity.",
            )

        # 9. Verify the best locator candidate
        validation = validate_locator_in_dom(
            soup=soup,
            selector=best_candidate.selector,
            expected_element=target_element,
        )

        if not validation.is_valid:
            return RepairResult(
                finding_id=finding_id,
                original_selector=original_selector,
                repaired=False,
                best_locator=None,
                confidence=0.0,
                strategy=None,
                candidate_locators=ranked_candidates,
                validation=validation,
                reason=f"Validation failed for candidate '{best_candidate.selector}': {validation.validation_message}",
            )

        # 10. Fresh live-page verification if requested
        live_result: Optional[LiveVerificationResult] = None
        if verify_live and target_url:
            live_result = verify_locator_on_live_page(
                target_url=target_url,
                selector=best_candidate.selector,
                page_instance=page_instance,
            )

        reason_text = (
            f"Successfully repaired locator '{original_selector}' using {best_candidate.strategy.value} strategy: "
            f"'{best_candidate.selector}' ({best_candidate.description})."
        )
        if live_result and live_result.attempted:
            reason_text += f" Live page verification: {live_result.validation_message}"

        # 11. Successful unambiguous repair with snapshot & live verification!
        return RepairResult(
            finding_id=finding_id,
            original_selector=original_selector,
            repaired=True,
            best_locator=best_candidate.selector,
            confidence=best_candidate.confidence,
            strategy=best_candidate.strategy,
            candidate_locators=ranked_candidates,
            validation=validation,
            snapshot_validation=validation,
            live_verification=live_result,
            reason=reason_text,
        )



# Global singleton instance and functional helper
self_healing_engine = SelfHealingEngine()
repair_locator = self_healing_engine.repair_finding
