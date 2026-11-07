"""Focused test suite for OmniSight Integration Pipeline Adapter.

Tests PipelineResult container, finding collection, detection status,
serialization, deserialization, and IntegrationPipelineAdapter execution.
"""

from __future__ import annotations

import json
import pytest

from integration.contracts import (
    DefectCategory,
    InspectionFinding,
    InspectionRequest,
    InspectionState,
    Severity,
)
from integration.pipeline import (
    InspectionPipelineAdapter,
    InspectionPipelineResult,
    IntegrationPipelineAdapter,
    PipelineAdapter,
    PipelineResult,
)


# ============================================================================
# PipelineResult - Request Acceptance and Validation Tests
# ============================================================================

def test_pipeline_result_accepts_inspection_request():
    """Verify PipelineResult accepts an initialized InspectionRequest."""
    req = InspectionRequest(target_url="http://localhost:8000/demo", state=InspectionState.CLEAN)
    result = PipelineResult(request=req)

    assert result.request is req
    assert result.request.target_url == "http://localhost:8000/demo"
    assert result.request.state is InspectionState.CLEAN
    assert result.findings == []
    assert result.success is True
    assert result.metadata == {}


def test_pipeline_result_accepts_request_as_string_url():
    """Verify PipelineResult converts a string URL into an InspectionRequest."""
    result = PipelineResult(request="http://localhost:8000/demo?defect=overflow")

    assert isinstance(result.request, InspectionRequest)
    assert result.request.target_url == "http://localhost:8000/demo?defect=overflow"
    assert result.request.state is InspectionState.CLEAN


def test_pipeline_result_accepts_request_as_dict():
    """Verify PipelineResult normalizes a raw dictionary into an InspectionRequest."""
    req_dict = {
        "target_url": "http://localhost:8000/demo",
        "state": "missing",
        "timeout": 10.0,
        "metadata": {"run_id": "test-123"},
    }
    result = PipelineResult(request=req_dict)

    assert isinstance(result.request, InspectionRequest)
    assert result.request.target_url == "http://localhost:8000/demo"
    assert result.request.state is InspectionState.MISSING
    assert result.request.timeout == 10.0
    assert result.request.metadata == {"run_id": "test-123"}


def test_pipeline_result_rejects_invalid_request():
    """Verify PipelineResult raises TypeError for invalid request types."""
    with pytest.raises(TypeError, match="request must be an InspectionRequest, dict, or str"):
        PipelineResult(request=12345)  # type: ignore[arg-type]


# ============================================================================
# PipelineResult - Finding Collection Tests
# ============================================================================

def test_pipeline_result_zero_findings_by_default():
    """Verify PipelineResult correctly handles zero findings."""
    req = InspectionRequest(target_url="http://localhost:8000")
    result = PipelineResult(request=req)

    assert result.findings == []
    assert len(result) == 0
    assert result.findings_count == 0
    assert result.has_findings is False
    assert result.findings_detected is False


def test_pipeline_result_collects_findings_on_init():
    """Verify PipelineResult accepts initial findings as objects or dicts."""
    req = InspectionRequest(target_url="http://localhost:8000")
    finding1 = InspectionFinding(
        defect_category=DefectCategory.OVERFLOW,
        severity=Severity.HIGH,
        description="Layout overflow in header",
        selector="#header",
    )
    finding2_dict = {
        "defect_category": "broken_image",
        "severity": "medium",
        "description": "Missing avatar graphic",
        "confidence": 0.95,
    }

    result = PipelineResult(request=req, findings=[finding1, finding2_dict])

    assert len(result.findings) == 2
    assert result.findings[0] is finding1
    assert isinstance(result.findings[1], InspectionFinding)
    assert result.findings[1].defect_category is DefectCategory.BROKEN_IMAGE
    assert result.findings[1].severity is Severity.MEDIUM
    assert result.findings[1].confidence == 0.95
    assert result.has_findings is True
    assert result.findings_detected is True
    assert result.findings_count == 2


def test_pipeline_result_add_finding_and_add_findings():
    """Verify add_finding and add_findings incrementally append normalized findings."""
    req = InspectionRequest(target_url="http://localhost:8000")
    result = PipelineResult(request=req)

    assert result.has_findings is False

    # Add single object
    f1 = InspectionFinding(
        defect_category=DefectCategory.MISSING_ELEMENT,
        severity=Severity.CRITICAL,
        description="Primary checkout button not rendered",
        selector="#checkout-btn",
    )
    added1 = result.add_finding(f1)
    assert added1 is f1
    assert result.has_findings is True
    assert result.findings_count == 1

    # Add single dict
    f2_dict = {
        "defect_category": "overflow",
        "severity": "low",
        "description": "Minor margin bleed",
    }
    added2 = result.add_finding(f2_dict)
    assert isinstance(added2, InspectionFinding)
    assert added2.defect_category is DefectCategory.OVERFLOW
    assert result.findings_count == 2

    # Add multiple via add_findings
    f3 = InspectionFinding(
        defect_category=DefectCategory.OTHER,
        severity=Severity.INFO,
        description="Styling anomaly",
    )
    f4_dict = {
        "defect_category": "broken_image",
        "severity": "high",
        "description": "Hero banner 404",
    }
    added_multi = result.add_findings([f3, f4_dict])
    assert len(added_multi) == 2
    assert result.findings_count == 4
    assert result.has_findings is True
    assert result.findings_detected is True


def test_pipeline_result_rejects_invalid_findings():
    """Verify PipelineResult raises TypeError for invalid finding items."""
    req = InspectionRequest(target_url="http://localhost:8000")
    with pytest.raises(TypeError, match="Finding item must be an InspectionFinding or dict"):
        PipelineResult(request=req, findings=["not-a-finding"])  # type: ignore[list-item]

    result = PipelineResult(request=req)
    with pytest.raises(TypeError, match="finding must be an InspectionFinding or dict"):
        result.add_finding(999)  # type: ignore[arg-type]


# ============================================================================
# PipelineResult - Finding Querying and Python Protocol Tests
# ============================================================================

def test_pipeline_result_filtering_by_severity_and_category():
    """Verify filtering findings by severity and defect category."""
    req = InspectionRequest(target_url="http://localhost:8000")
    result = PipelineResult(request=req)
    result.add_findings(
        [
            {
                "defect_category": "overflow",
                "severity": "critical",
                "description": "Overflow 1",
            },
            {
                "defect_category": "overflow",
                "severity": "low",
                "description": "Overflow 2",
            },
            {
                "defect_category": "missing_element",
                "severity": "critical",
                "description": "Missing 1",
            },
        ]
    )

    critical_findings = result.get_findings_by_severity(Severity.CRITICAL)
    assert len(critical_findings) == 2
    assert all(f.severity is Severity.CRITICAL for f in critical_findings)

    # String filtering
    low_findings = result.get_findings_by_severity("low")
    assert len(low_findings) == 1
    assert low_findings[0].description == "Overflow 2"

    # Category filtering
    overflows = result.get_findings_by_category(DefectCategory.OVERFLOW)
    assert len(overflows) == 2
    assert all(f.defect_category is DefectCategory.OVERFLOW for f in overflows)

    missing = result.get_findings_by_category("missing")
    assert len(missing) == 1
    assert missing[0].defect_category is DefectCategory.MISSING_ELEMENT


def test_pipeline_result_iteration_and_indexing():
    """Verify PipelineResult supports len, iter, and getitem protocols."""
    req = InspectionRequest(target_url="http://localhost:8000")
    result = PipelineResult(request=req)
    f1 = InspectionFinding(
        defect_category=DefectCategory.OVERFLOW,
        severity=Severity.HIGH,
        description="Overflow",
    )
    f2 = InspectionFinding(
        defect_category=DefectCategory.BROKEN_IMAGE,
        severity=Severity.LOW,
        description="Broken image",
    )
    result.add_findings([f1, f2])

    assert len(result) == 2
    assert result[0] is f1
    assert result[1] is f2
    assert list(result) == [f1, f2]


def test_pipeline_result_boolean_evaluation():
    """Verify PipelineResult boolean truthiness is driven by success state."""
    req = InspectionRequest(target_url="http://localhost:8000")
    clean_result = PipelineResult(request=req, findings=[], success=True)
    assert bool(clean_result) is True  # True even with 0 findings!

    failed_result = PipelineResult(request=req, findings=[], success=False)
    assert bool(failed_result) is False


# ============================================================================
# PipelineResult - Serialization and Deserialization Tests
# ============================================================================

def test_pipeline_result_to_dict_empty_findings():
    """Verify to_dict representation with zero findings."""
    req = InspectionRequest(
        target_url="http://localhost:8000/demo",
        state=InspectionState.CLEAN,
        timeout=8.0,
        metadata={"client": "test"},
    )
    result = PipelineResult(request=req, success=True, metadata={"trace_id": "tr-001"})
    data = result.to_dict()

    assert data["request"]["target_url"] == "http://localhost:8000/demo"
    assert data["request"]["state"] == "clean"
    assert data["request"]["timeout"] == 8.0
    assert data["findings"] == []
    assert data["has_findings"] is False
    assert data["findings_count"] == 0
    assert data["success"] is True
    assert data["metadata"] == {"trace_id": "tr-001"}


def test_pipeline_result_to_dict_with_findings():
    """Verify to_dict representation with multiple findings."""
    req = InspectionRequest(target_url="http://localhost:8000/demo")
    finding = InspectionFinding(
        defect_category=DefectCategory.OVERFLOW,
        severity=Severity.HIGH,
        description="Layout overflow",
        selector="#card-container",
        confidence=0.88,
        metadata={"node": "div.card"},
    )
    result = PipelineResult(request=req, findings=[finding])
    data = result.to_dict()

    assert data["has_findings"] is True
    assert data["findings_count"] == 1
    assert len(data["findings"]) == 1
    f_dict = data["findings"][0]
    assert f_dict["defect_category"] == "overflow"
    assert f_dict["severity"] == "high"
    assert f_dict["description"] == "Layout overflow"
    assert f_dict["selector"] == "#card-container"
    assert f_dict["confidence"] == 0.88
    assert f_dict["metadata"] == {"node": "div.card"}


def test_pipeline_result_json_roundtrip():
    """Verify to_json and from_json serialize and deserialize accurately."""
    req = InspectionRequest(
        target_url="http://localhost:8000/demo",
        state=InspectionState.ALL,
        timeout=12.5,
        metadata={"env": "staging"},
    )
    findings = [
        InspectionFinding(
            defect_category=DefectCategory.OVERFLOW,
            severity=Severity.HIGH,
            description="Card container text blowout",
            selector="#metric-card",
            confidence=0.92,
        ),
        InspectionFinding(
            defect_category=DefectCategory.BROKEN_IMAGE,
            severity=Severity.MEDIUM,
            description="SVG missing src attribute",
            selector="img#hero",
            confidence=0.87,
        ),
    ]
    original = PipelineResult(
        request=req,
        findings=findings,
        success=True,
        metadata={"run_duration_ms": 420},
    )

    json_str = original.to_json(indent=2)
    assert isinstance(json_str, str)

    parsed = json.loads(json_str)
    assert parsed["has_findings"] is True
    assert parsed["findings_count"] == 2

    restored = PipelineResult.from_json(json_str)
    assert isinstance(restored, PipelineResult)
    assert isinstance(restored.request, InspectionRequest)
    assert restored.request.target_url == "http://localhost:8000/demo"
    assert restored.request.state is InspectionState.ALL
    assert restored.request.timeout == 12.5
    assert len(restored.findings) == 2
    assert restored.findings[0].defect_category is DefectCategory.OVERFLOW
    assert restored.findings[1].defect_category is DefectCategory.BROKEN_IMAGE
    assert restored.has_findings is True
    assert restored.findings_count == 2
    assert restored.success is True
    assert restored.metadata == {"run_duration_ms": 420}


def test_pipeline_result_from_dict_validation_errors():
    """Verify from_dict raises errors on missing or invalid fields."""
    with pytest.raises(TypeError, match="Expected dict"):
        PipelineResult.from_dict("not-a-dict")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Dictionary missing 'request'"):
        PipelineResult.from_dict({})

    with pytest.raises(TypeError, match="findings must be a list or tuple"):
        PipelineResult.from_dict({
            "request": {"target_url": "http://localhost:8000"},
            "findings": "invalid",
        })


# ============================================================================
# IntegrationPipelineAdapter Tests
# ============================================================================

def test_integration_pipeline_adapter_defaults():
    """Verify adapter initializes with defaults and exposes expected aliases."""
    adapter = IntegrationPipelineAdapter()
    assert adapter.name == "default_integration_pipeline"
    assert adapter.default_timeout == 5.0
    assert adapter.metadata == {}

    # Alias checks
    assert InspectionPipelineAdapter is IntegrationPipelineAdapter
    assert PipelineAdapter is IntegrationPipelineAdapter
    assert InspectionPipelineResult is PipelineResult


def test_integration_pipeline_adapter_run_clean():
    """Verify adapter run returns a clean PipelineResult when no defects are detected."""
    adapter = IntegrationPipelineAdapter(name="test_adapter")
    req = InspectionRequest(target_url="http://localhost:8000/demo", state=InspectionState.CLEAN)

    result = adapter.run(req)

    assert isinstance(result, PipelineResult)
    assert result.request is req
    assert result.has_findings is False
    assert result.findings_count == 0
    assert result.success is True


def test_integration_pipeline_adapter_run_with_predefined_findings():
    """Verify adapter run attaches pre-collected findings."""
    adapter = IntegrationPipelineAdapter()
    findings = [
        InspectionFinding(
            defect_category=DefectCategory.OVERFLOW,
            severity=Severity.HIGH,
            description="Text overflow detected",
        )
    ]
    result = adapter.run(
        request="http://localhost:8000/demo",
        findings=findings,
        metadata={"execution": "batch"},
    )

    assert result.request.target_url == "http://localhost:8000/demo"
    assert result.has_findings is True
    assert result.findings_count == 1
    assert result.findings[0].defect_category is DefectCategory.OVERFLOW
    assert result.metadata["execution"] == "batch"


def test_integration_pipeline_adapter_run_with_collector_callback():
    """Verify adapter invokes finding collector callback and attaches collected findings."""
    adapter = IntegrationPipelineAdapter(name="collector_adapter")

    def mock_defect_detector(req: InspectionRequest):
        assert req.target_url == "http://localhost:8000/demo"
        return [
            {
                "defect_category": "missing_element",
                "severity": "critical",
                "description": "Navbar element not found",
                "selector": "#nav-main",
            }
        ]

    result = adapter.run(
        request={"target_url": "http://localhost:8000/demo", "state": "missing"},
        collector=mock_defect_detector,
    )

    assert result.request.state is InspectionState.MISSING
    assert result.has_findings is True
    assert result.findings_count == 1
    assert result.findings[0].defect_category is DefectCategory.MISSING_ELEMENT
    assert result.findings[0].severity is Severity.CRITICAL


def test_integration_pipeline_adapter_aliases_execute_and_create_result():
    """Verify execute and create_result work interchangeably with run."""
    adapter = IntegrationPipelineAdapter()
    req = InspectionRequest(target_url="http://localhost:8000")

    res_run = adapter.run(req)
    res_exec = adapter.execute(req)
    res_create = adapter.create_result(req)

    assert isinstance(res_run, PipelineResult)
    assert isinstance(res_exec, PipelineResult)
    assert isinstance(res_create, PipelineResult)


def test_integration_pipeline_adapter_collector_error_handling():
    """Verify adapter raises TypeError when collector is not callable."""
    adapter = IntegrationPipelineAdapter()
    with pytest.raises(TypeError, match="collector must be callable"):
        adapter.run("http://localhost:8000", collector="not-callable")  # type: ignore[arg-type]


def test_integration_pipeline_adapter_invalid_request_handling():
    """Verify adapter raises TypeError when request is invalid."""
    adapter = IntegrationPipelineAdapter()
    with pytest.raises(TypeError, match="request must be an InspectionRequest, dict, or str"):
        adapter.run(None)  # type: ignore[arg-type]
