"""Focused test suite for OmniSight shared integration contracts.

Tests construction, type normalization, validation rules, serialization,
and deserialization for InspectionState, DefectCategory, Severity,
InspectionRequest, and InspectionFinding.
"""

from __future__ import annotations

import json
import pytest

from integration.contracts import (
    DefectCategory,
    DemoInspectionState,
    InspectionFinding,
    InspectionRequest,
    InspectionState,
    Severity,
)
from integration.demo_runner import construct_demo_url


# ============================================================================
# InspectionState Tests
# ============================================================================

def test_inspection_state_members_and_values():
    """Verify all expected inspection state members and their string values."""
    expected = {
        InspectionState.CLEAN: "clean",
        InspectionState.OVERFLOW: "overflow",
        InspectionState.MISSING: "missing",
        InspectionState.IMAGE: "image",
        InspectionState.ALL: "all",
    }
    for member, expected_val in expected.items():
        assert member.value == expected_val
        assert member == expected_val
        assert isinstance(member, str)

    # Alias check
    assert DemoInspectionState is InspectionState


def test_inspection_state_normalization():
    """Verify parsing and normalization from strings and existing enum instances."""
    assert InspectionState.from_str("clean") is InspectionState.CLEAN
    assert InspectionState.from_str(" OVERFLOW ") is InspectionState.OVERFLOW
    assert InspectionState.from_str("Missing") is InspectionState.MISSING
    assert InspectionState.from_str(InspectionState.IMAGE) is InspectionState.IMAGE
    assert InspectionState("all") is InspectionState.ALL


def test_inspection_state_invalid_values():
    """Verify invalid inspection states raise descriptive errors."""
    with pytest.raises(ValueError, match="Unsupported inspection state"):
        InspectionState.from_str("corrupted_state")

    with pytest.raises(TypeError, match="State must be a str or InspectionState"):
        InspectionState.from_str(12345)  # type: ignore[arg-type]


# ============================================================================
# DefectCategory Tests
# ============================================================================

def test_defect_category_members_and_aliases():
    """Verify defect category enum members, values, and alias mappings."""
    assert DefectCategory.OVERFLOW.value == "overflow"
    assert DefectCategory.MISSING_ELEMENT.value == "missing_element"
    assert DefectCategory.BROKEN_IMAGE.value == "broken_image"
    assert DefectCategory.OTHER.value == "other"

    # Direct aliases
    assert DefectCategory.MISSING is DefectCategory.MISSING_ELEMENT
    assert DefectCategory.IMAGE is DefectCategory.BROKEN_IMAGE


def test_defect_category_normalization():
    """Verify flexible parsing with hyphen/underscore and short names."""
    assert DefectCategory.from_str("overflow") is DefectCategory.OVERFLOW
    assert DefectCategory.from_str("layout_overflow") is DefectCategory.OVERFLOW
    assert DefectCategory.from_str("missing") is DefectCategory.MISSING_ELEMENT
    assert DefectCategory.from_str("missing-element") is DefectCategory.MISSING_ELEMENT
    assert DefectCategory.from_str("missing_element") is DefectCategory.MISSING_ELEMENT
    assert DefectCategory.from_str("broken-image") is DefectCategory.BROKEN_IMAGE
    assert DefectCategory.from_str("image") is DefectCategory.BROKEN_IMAGE
    assert DefectCategory.from_str("other") is DefectCategory.OTHER
    assert DefectCategory.from_str(DefectCategory.OVERFLOW) is DefectCategory.OVERFLOW


def test_defect_category_invalid_values():
    """Verify invalid defect categories raise ValueError/TypeError."""
    with pytest.raises(ValueError, match="Unsupported defect category"):
        DefectCategory.from_str("non_existent_category")

    with pytest.raises(TypeError, match="DefectCategory must be a str or DefectCategory"):
        DefectCategory.from_str(None)  # type: ignore[arg-type]


# ============================================================================
# Severity Tests
# ============================================================================

def test_severity_levels():
    """Verify severity enum members and string equality."""
    expected = {
        Severity.INFO: "info",
        Severity.LOW: "low",
        Severity.MEDIUM: "medium",
        Severity.HIGH: "high",
        Severity.CRITICAL: "critical",
    }
    for member, val in expected.items():
        assert member.value == val
        assert member == val
        assert isinstance(member, str)


def test_severity_normalization():
    """Verify case-insensitive parsing and enum pass-through."""
    assert Severity.from_str("info") is Severity.INFO
    assert Severity.from_str(" LOW ") is Severity.LOW
    assert Severity.from_str("Medium") is Severity.MEDIUM
    assert Severity.from_str("HIGH") is Severity.HIGH
    assert Severity.from_str("critical") is Severity.CRITICAL
    assert Severity.from_str(Severity.HIGH) is Severity.HIGH


def test_severity_invalid_values():
    """Verify invalid severity levels raise ValueError/TypeError."""
    with pytest.raises(ValueError, match="Unsupported severity"):
        Severity.from_str("extreme")

    with pytest.raises(TypeError, match="Severity must be a str or Severity"):
        Severity.from_str(["high"])  # type: ignore[arg-type]


# ============================================================================
# InspectionRequest Tests
# ============================================================================

def test_inspection_request_construction_minimal():
    """Verify default construction with minimal required target_url."""
    req = InspectionRequest("http://127.0.0.1:8080")
    assert req.target_url == "http://127.0.0.1:8080"
    assert req.url == "http://127.0.0.1:8080"
    assert req.state is InspectionState.CLEAN
    assert req.timeout == 5.0
    assert req.metadata == {}


def test_inspection_request_construction_full():
    """Verify construction with all parameters specified."""
    req = InspectionRequest(
        target_url="http://127.0.0.1:8080/?defect=overflow",
        state="overflow",
        timeout=12.5,
        metadata={"run_id": "test-run-101", "browser": "chromium"},
    )
    assert req.target_url == "http://127.0.0.1:8080/?defect=overflow"
    assert req.state is InspectionState.OVERFLOW
    assert req.timeout == 12.5
    assert req.metadata == {"run_id": "test-run-101", "browser": "chromium"}


def test_inspection_request_url_alias():
    """Verify url keyword argument works as an alias for target_url."""
    req = InspectionRequest(url="http://127.0.0.1:8080/portal")
    assert req.target_url == "http://127.0.0.1:8080/portal"
    assert req.url == "http://127.0.0.1:8080/portal"


def test_inspection_request_validation():
    """Verify validation for empty URL, invalid timeout, state, and metadata."""
    # Empty URL
    with pytest.raises(ValueError, match="target_url cannot be empty"):
        InspectionRequest("")
    with pytest.raises(ValueError, match="target_url cannot be empty"):
        InspectionRequest("   ")

    # Invalid timeout
    with pytest.raises(ValueError, match="timeout must be greater than 0"):
        InspectionRequest("http://127.0.0.1:8080", timeout=0)
    with pytest.raises(ValueError, match="timeout must be greater than 0"):
        InspectionRequest("http://127.0.0.1:8080", timeout=-2.5)
    with pytest.raises(TypeError, match="timeout must be a number"):
        InspectionRequest("http://127.0.0.1:8080", timeout="fast")  # type: ignore[arg-type]

    # Invalid state
    with pytest.raises(ValueError, match="Unsupported inspection state"):
        InspectionRequest("http://127.0.0.1:8080", state="unsupported_state")

    # Invalid metadata
    with pytest.raises(TypeError, match="metadata must be a dict"):
        InspectionRequest("http://127.0.0.1:8080", metadata="not_a_dict")  # type: ignore[arg-type]


def test_inspection_request_serialization_roundtrip():
    """Verify to_dict, from_dict, to_json, and from_json roundtripping."""
    original = InspectionRequest(
        target_url="http://127.0.0.1:8080/?defect=image",
        state=InspectionState.IMAGE,
        timeout=8.0,
        metadata={"environment": "staging"},
    )

    # Dict roundtrip
    data_dict = original.to_dict()
    assert data_dict == {
        "target_url": "http://127.0.0.1:8080/?defect=image",
        "state": "image",
        "timeout": 8.0,
        "metadata": {"environment": "staging"},
    }
    reconstructed_from_dict = InspectionRequest.from_dict(data_dict)
    assert reconstructed_from_dict == original

    # JSON roundtrip
    json_str = original.to_json()
    assert isinstance(json_str, str)
    parsed = json.loads(json_str)
    assert parsed["state"] == "image"

    reconstructed_from_json = InspectionRequest.from_json(json_str)
    assert reconstructed_from_json == original


def test_inspection_request_from_dict_validation():
    """Verify from_dict checks for input type and missing required fields."""
    with pytest.raises(TypeError, match="Expected dict"):
        InspectionRequest.from_dict("invalid_payload")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="missing 'target_url'"):
        InspectionRequest.from_dict({"timeout": 5.0})


# ============================================================================
# InspectionFinding Tests
# ============================================================================

def test_inspection_finding_construction_minimal():
    """Verify finding construction with minimal required fields."""
    finding = InspectionFinding(
        defect_category=DefectCategory.OVERFLOW,
        severity=Severity.HIGH,
        description="Metric counter overflow detected outside card bounds.",
    )
    assert finding.defect_category is DefectCategory.OVERFLOW
    assert finding.severity is Severity.HIGH
    assert finding.description == "Metric counter overflow detected outside card bounds."
    assert finding.selector is None
    assert finding.confidence is None
    assert finding.metadata == {}


def test_inspection_finding_construction_full():
    """Verify finding construction with all optional fields and string coercions."""
    finding = InspectionFinding(
        defect_category="broken_image",
        severity="critical",
        description="Service topology diagram image failed to load with 404.",
        selector="#service-topology-image",
        confidence=0.98,
        metadata={"element_id": "service-topology-image", "asset_type": "svg"},
    )
    assert finding.defect_category is DefectCategory.BROKEN_IMAGE
    assert finding.severity is Severity.CRITICAL
    assert finding.selector == "#service-topology-image"
    assert finding.confidence == 0.98
    assert finding.metadata["asset_type"] == "svg"


def test_inspection_finding_validation():
    """Verify validation on description, confidence, defect_category, and severity."""
    # Empty description
    with pytest.raises(ValueError, match="description cannot be empty"):
        InspectionFinding(
            defect_category=DefectCategory.OVERFLOW,
            severity=Severity.MEDIUM,
            description="   ",
        )

    # Invalid confidence range
    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        InspectionFinding(
            defect_category=DefectCategory.OVERFLOW,
            severity=Severity.MEDIUM,
            description="Valid description",
            confidence=1.25,
        )
    with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
        InspectionFinding(
            defect_category=DefectCategory.OVERFLOW,
            severity=Severity.MEDIUM,
            description="Valid description",
            confidence=-0.1,
        )
    with pytest.raises(TypeError, match="confidence must be a number or None"):
        InspectionFinding(
            defect_category=DefectCategory.OVERFLOW,
            severity=Severity.MEDIUM,
            description="Valid description",
            confidence="high",  # type: ignore[arg-type]
        )

    # Invalid category and severity
    with pytest.raises(ValueError, match="Unsupported defect category"):
        InspectionFinding(
            defect_category="random_defect",
            severity=Severity.LOW,
            description="Valid description",
        )
    with pytest.raises(ValueError, match="Unsupported severity"):
        InspectionFinding(
            defect_category=DefectCategory.OVERFLOW,
            severity="mega_critical",
            description="Valid description",
        )

    # Invalid metadata type
    with pytest.raises(TypeError, match="metadata must be a dict"):
        InspectionFinding(
            defect_category=DefectCategory.OVERFLOW,
            severity=Severity.LOW,
            description="Valid description",
            metadata=["invalid"],  # type: ignore[arg-type]
        )


def test_inspection_finding_serialization_roundtrip():
    """Verify finding to_dict, from_dict, to_json, and from_json."""
    finding = InspectionFinding(
        defect_category=DefectCategory.MISSING_ELEMENT,
        severity=Severity.HIGH,
        description="Locator '#btn-trigger-self-heal' not visible in DOM.",
        selector="#btn-trigger-self-heal",
        confidence=0.92,
        metadata={"action": "repaired_selector"},
    )

    data = finding.to_dict()
    assert data["defect_category"] == "missing_element"
    assert data["severity"] == "high"
    assert data["selector"] == "#btn-trigger-self-heal"
    assert data["confidence"] == 0.92
    assert data["metadata"] == {"action": "repaired_selector"}

    # from_dict roundtrip
    restored = InspectionFinding.from_dict(data)
    assert restored == finding

    # to_json / from_json roundtrip
    json_str = finding.to_json()
    assert isinstance(json_str, str)
    restored_json = InspectionFinding.from_json(json_str)
    assert restored_json == finding


def test_inspection_finding_from_dict_validation():
    """Verify from_dict validates dictionary structure and required keys."""
    with pytest.raises(TypeError, match="Expected dict"):
        InspectionFinding.from_dict(None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="missing 'defect_category'"):
        InspectionFinding.from_dict({
            "severity": "high",
            "description": "Missing category",
        })

    with pytest.raises(ValueError, match="missing 'severity'"):
        InspectionFinding.from_dict({
            "defect_category": "overflow",
            "description": "Missing severity",
        })

    with pytest.raises(ValueError, match="missing 'description'"):
        InspectionFinding.from_dict({
            "defect_category": "overflow",
            "severity": "high",
        })


# ============================================================================
# Interoperability with Demo Flow Tests
# ============================================================================

def test_interoperability_with_demo_runner_urls():
    """Verify InspectionState directly works with demo_runner construct_demo_url."""
    base = "http://127.0.0.1:8080"

    # Direct enum usage with construct_demo_url
    clean_url = construct_demo_url(base, InspectionState.CLEAN)
    assert clean_url == "http://127.0.0.1:8080/?state=clean"

    overflow_url = construct_demo_url(base, InspectionState.OVERFLOW)
    assert overflow_url == "http://127.0.0.1:8080/?defect=overflow"

    missing_url = construct_demo_url(base, InspectionState.MISSING)
    assert missing_url == "http://127.0.0.1:8080/?defect=missing"

    image_url = construct_demo_url(base, InspectionState.IMAGE)
    assert image_url == "http://127.0.0.1:8080/?defect=image"

    all_url = construct_demo_url(base, InspectionState.ALL)
    assert all_url == "http://127.0.0.1:8080/?defects=all"


def test_demo_defect_scenarios_modeled_as_findings():
    """Verify all 3 controlled demo defect scenarios can be represented as typed findings."""
    # 1. Overflow Defect Scenario
    overflow_finding = InspectionFinding(
        defect_category=DefectCategory.OVERFLOW,
        severity=Severity.HIGH,
        description="Layout overflow: text exceeding card width in #card-active-jobs",
        selector="#card-active-jobs",
        confidence=0.96,
        metadata={"subtext_id": "metric-active-jobs-subtext"},
    )
    assert overflow_finding.defect_category == "overflow"

    # 2. Missing Visible Element Scenario
    missing_finding = InspectionFinding(
        defect_category=DefectCategory.MISSING_ELEMENT,
        severity=Severity.HIGH,
        description="Missing element: Self-heal trigger button not rendered in viewport",
        selector="#btn-trigger-self-heal",
        confidence=0.99,
        metadata={"telemetry_row": "status-badge-102"},
    )
    assert missing_finding.defect_category == "missing_element"

    # 3. Broken Image Scenario
    broken_image_finding = InspectionFinding(
        defect_category=DefectCategory.BROKEN_IMAGE,
        severity=Severity.MEDIUM,
        description="Broken image: Topology diagram returned HTTP 404",
        selector="#service-topology-image",
        confidence=0.94,
        metadata={"src": "assets/images/non-existent-broken-diagram.png"},
    )
    assert broken_image_finding.defect_category == "broken_image"
