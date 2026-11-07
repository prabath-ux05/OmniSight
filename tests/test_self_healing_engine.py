"""Focused test suite for the Self-Healing Locator Repair Engine.

Tests:
1. Valid missing-element repair using resilient data-attribute strategy.
2. Deterministic multiple-candidate scoring and ranking order.
3. Invalid / unresolvable candidates (never claim repair).
4. Duplicate / non-unique selectors (reject ambiguous repairs).
5. Malformed or missing DOM evidence snapshots.
6. No suitable repair candidate in DOM.
7. Category gating (non-missing categories skipped).
8. Real demo-site HTML repair round-trip.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from backend.app.schemas.findings import EvidenceReferences, FindingResponse
from integration.contracts import DefectCategory, InspectionFinding, Severity
from self_healing.models import RepairResult, RepairStrategy
from self_healing.repair_engine import SelfHealingEngine, repair_locator


# Sample clean DOM snippet resembling the OmniSight demo portal
SAMPLE_HERO_DOM = """<!DOCTYPE html>
<html lang="en">
<head><title>OmniSight Portal</title></head>
<body>
  <div id="hero-actions-container" class="hero-actions-group">
    <button
      id="btn-trigger-self-heal"
      class="btn-primary cta-action-btn"
      type="button"
      data-testid="trigger-self-heal-cta"
      aria-label="Trigger Self-Healing Workflow"
    >
      <span class="btn-text">Trigger Self-Healing Job</span>
    </button>
    <button
      id="btn-export-telemetry"
      class="btn-secondary"
      type="button"
      data-testid="export-telemetry-btn"
    >
      <span class="btn-text">Export Telemetry</span>
    </button>
  </div>
</body>
</html>
"""


# ============================================================================
# 1. Valid Missing-Element Repair Tests
# ============================================================================

def test_valid_missing_element_repair_data_attribute():
    """Verify that a missing visible element finding is repaired using a data attribute."""
    finding = FindingResponse(
        finding_id="defect_missing_001",
        category="missing_visible_element",
        severity="medium",
        confidence=0.88,
        description="Primary CTA button missing or failed to locate.",
        selector="#btn-trigger-self-heal",
        source="mock",
    )

    result = repair_locator(finding=finding, dom_content=SAMPLE_HERO_DOM)

    assert isinstance(result, RepairResult)
    assert result.finding_id == "defect_missing_001"
    assert result.original_selector == "#btn-trigger-self-heal"
    assert result.repaired is True
    assert result.best_locator is not None
    assert "data-testid" in result.best_locator
    assert result.strategy == RepairStrategy.DATA_ATTRIBUTE
    assert result.confidence == 0.95

    # Verification outcome
    assert result.validation is not None
    assert result.validation.is_valid is True
    assert result.validation.matches == 1
    assert result.validation.resolved_tag == "button"
    assert "Successfully repaired locator" in result.reason


def test_valid_repair_with_inspection_finding_contract():
    """Verify repair engine accepts shared InspectionFinding contract instances."""
    finding = InspectionFinding(
        defect_category=DefectCategory.MISSING_ELEMENT,
        severity=Severity.HIGH,
        description="CTA button locator drift.",
        selector="#btn-trigger-self-heal",
        confidence=0.92,
        metadata={"finding_id": "if_missing_002"},
    )

    result = repair_locator(finding=finding, dom_content=SAMPLE_HERO_DOM)

    assert result.repaired is True
    assert result.strategy == RepairStrategy.DATA_ATTRIBUTE
    assert result.validation.matches == 1


# ============================================================================
# 2. Multiple Candidate Ranking Tests
# ============================================================================

def test_multiple_candidate_ranking_order():
    """Verify candidates are scored and ranked in deterministic confidence order."""
    finding = FindingResponse(
        finding_id="defect_rank_003",
        category="missing_visible_element",
        severity="high",
        confidence=0.90,
        description="Rank candidate test",
        selector="#btn-trigger-self-heal",
    )

    result = repair_locator(finding=finding, dom_content=SAMPLE_HERO_DOM)

    assert result.repaired is True
    assert len(result.candidate_locators) >= 4

    # Verify candidates are sorted descending by confidence / priority
    confidences = [c.confidence for c in result.candidate_locators if c.is_unique]
    assert confidences == sorted(confidences, reverse=True)

    # Top candidate must be DATA_ATTRIBUTE (confidence 0.95)
    top = result.candidate_locators[0]
    assert top.strategy == RepairStrategy.DATA_ATTRIBUTE
    assert top.confidence == 0.95
    assert top.is_unique is True
    assert top.match_count == 1

    # Strategies present in candidate list
    strategies = {c.strategy for c in result.candidate_locators}
    assert RepairStrategy.DATA_ATTRIBUTE in strategies
    assert RepairStrategy.STABLE_ID in strategies
    assert RepairStrategy.ACCESSIBLE_ROLE_NAME in strategies
    assert RepairStrategy.SEMANTIC_CSS in strategies


# ============================================================================
# 3. Invalid and Unresolvable Candidate Tests
# ============================================================================

def test_unresolvable_candidate_never_claims_repair():
    """Verify engine never claims repaired if candidate cannot resolve element in DOM."""
    # DOM without the target element
    bare_dom = "<html><body><header><h1>Dashboard</h1></header></body></html>"

    finding = FindingResponse(
        finding_id="defect_unresolvable_004",
        category="missing_visible_element",
        severity="medium",
        confidence=0.85,
        description="Missing element test",
        selector="#nonexistent-cta-button",
    )

    result = repair_locator(finding=finding, dom_content=bare_dom)

    assert result.repaired is False
    assert result.best_locator is None
    assert result.confidence == 0.0
    assert result.strategy is None
    assert "No suitable replacement element" in result.reason


# ============================================================================
# 4. Duplicate and Non-Unique Selectors Tests
# ============================================================================

def test_duplicate_non_unique_selectors_cannot_repair():
    """Verify ambiguous candidates matching multiple elements cannot be marked repaired."""
    # DOM with 3 identical buttons lacking unique IDs or testids
    ambiguous_dom = """
    <html><body>
      <button class="generic-btn">Click</button>
      <button class="generic-btn">Click</button>
      <button class="generic-btn">Click</button>
    </body></html>
    """

    finding = FindingResponse(
        finding_id="defect_ambiguous_005",
        category="missing_visible_element",
        severity="low",
        confidence=0.75,
        description="Ambiguous button",
        selector="button.generic-btn",
    )

    result = repair_locator(finding=finding, dom_content=ambiguous_dom)

    # Must NOT claim repair because all selectors match 3 elements
    assert result.repaired is False
    assert result.best_locator is None
    for cand in result.candidate_locators:
        assert cand.is_unique is False
        assert cand.match_count == 3
    assert "No candidate locator uniquely resolved" in result.reason


# ============================================================================
# 5. Malformed and Missing DOM Evidence Tests
# ============================================================================

def test_missing_dom_file_path_fails_gracefully(tmp_path):
    """Verify graceful failure when evidence snapshot file does not exist on disk."""
    non_existent_file = tmp_path / "artifacts" / "run_missing" / "dom.html"

    finding = FindingResponse(
        finding_id="defect_missing_dom_006",
        category="missing_visible_element",
        severity="medium",
        confidence=0.80,
        description="Missing DOM path test",
        selector="#target-btn",
        evidence=EvidenceReferences(dom_snapshot_path=str(non_existent_file)),
    )

    result = repair_locator(finding=finding)

    assert result.repaired is False
    assert result.best_locator is None
    assert result.validation is not None
    assert result.validation.is_valid is False
    assert "not found on disk" in result.reason


def test_empty_dom_content_fails_gracefully():
    """Verify graceful failure when DOM snapshot content is completely empty."""
    finding = FindingResponse(
        finding_id="defect_empty_dom_007",
        category="missing_visible_element",
        severity="medium",
        confidence=0.80,
        description="Empty DOM test",
        selector="#target-btn",
    )

    result = repair_locator(finding=finding, dom_content="   ")

    assert result.repaired is False
    assert result.best_locator is None
    assert result.validation.is_valid is False
    assert "empty" in result.reason.lower()


# ============================================================================
# 6. Category and Input Gating Tests
# ============================================================================

def test_non_missing_element_category_skips_repair():
    """Verify layout_overflow and broken_image categories are not repaired."""
    overflow_finding = FindingResponse(
        finding_id="defect_overflow_008",
        category="layout_overflow",
        severity="high",
        confidence=0.92,
        description="Layout overflow in container",
        selector="#content-panel",
    )

    result = repair_locator(finding=overflow_finding, dom_content=SAMPLE_HERO_DOM)

    assert result.repaired is False
    assert result.best_locator is None
    assert "not a missing visible element" in result.reason
    assert result.candidate_locators == []


def test_empty_selector_fails_gracefully():
    """Verify finding with empty or None selector is safely rejected."""
    finding = FindingResponse(
        finding_id="defect_no_sel_009",
        category="missing_visible_element",
        severity="low",
        confidence=0.70,
        description="No selector finding",
        selector="",
    )

    result = repair_locator(finding=finding, dom_content=SAMPLE_HERO_DOM)

    assert result.repaired is False
    assert "Original selector is missing or empty" in result.reason


# ============================================================================
# 7. Real Demo Site File Round-Trip Test
# ============================================================================

def test_real_demo_site_html_locator_repair():
    """Verify self-healing engine on actual demo_site/index.html file."""
    demo_site_html_path = Path("demo_site") / "index.html"
    assert demo_site_html_path.is_file(), "demo_site/index.html must exist"

    finding = FindingResponse(
        finding_id="defect_real_demo_010",
        category="missing_visible_element",
        severity="medium",
        confidence=0.88,
        description="Primary CTA button missing.",
        selector="#btn-trigger-self-heal",
        evidence=EvidenceReferences(dom_snapshot_path=str(demo_site_html_path)),
    )

    engine = SelfHealingEngine()
    result = engine.repair_finding(finding)

    assert result.repaired is True
    assert result.best_locator == '[data-testid="trigger-self-heal-cta"]'
    assert result.strategy == RepairStrategy.DATA_ATTRIBUTE
    assert result.confidence == 0.95
    assert result.validation.is_valid is True
    assert result.validation.matches == 1
    assert result.validation.resolved_tag == "button"
