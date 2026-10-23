"""Focused end-to-end integration test suite.

Validates the full multimodal inspection pipeline flow:
Demo Site (SUT) -> Browser Agent (navigation & evidence capture)
-> Vision Engine (evidence validation & defect detection)
-> Structured findings (PipelineResult & InspectionFindings).
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Generator
import pytest

from browser_agent.navigation.navigator import BrowserNavigator, NavigationResult
from integration.contracts import (
    DefectCategory,
    InspectionFinding,
    InspectionRequest,
    InspectionState,
    Severity,
)
from integration.pipeline import (
    IntegrationPipelineAdapter,
    PipelineResult,
    execute_inspection,
    execute_inspection_flow,
    vision_finding_to_inspection_finding,
)
from tests.test_demo_site import DEMO_SITE_DIR, ThreadedHTTPServer
from vision_engine.detection.dom_detector import detect_dom_issues
from vision_engine.detection.mock_detector import detect_mock
from vision_engine.models import (
    BoundingBox,
    EvidenceReferences,
    VisionFinding,
    VisionInput,
)


@pytest.fixture(scope="module")
def demo_server() -> Generator[str, None, None]:
    """Spin up local ThreadedHTTPServer serving demo_site/."""
    server = ThreadedHTTPServer(DEMO_SITE_DIR)
    server.start()
    base_url = f"http://127.0.0.1:{server.port}"
    try:
        yield base_url
    finally:
        server.stop()


@pytest.fixture
def run_cleanup():
    """Track run_ids to clean up generated artifact directories after tests."""
    run_ids: list[str] = []

    def _register(run_id: str) -> str:
        run_ids.append(run_id)
        return run_id

    yield _register

    for rid in run_ids:
        artifact_dir = Path("artifacts") / rid
        if artifact_dir.exists():
            shutil.rmtree(artifact_dir, ignore_errors=True)


def test_e2e_clean_state_inspection(demo_server: str, run_cleanup):
    """Verify clean state flow: Demo Site -> Browser Agent -> Vision Engine -> 0 findings."""
    run_id = run_cleanup("e2e_test_clean_001")

    request = InspectionRequest(
        target_url=f"{demo_server}/index.html",
        state=InspectionState.CLEAN,
        timeout=10.0,
    )

    result = execute_inspection_flow(request, run_id=run_id)

    assert isinstance(result, PipelineResult)
    assert result.success is True
    assert result.has_findings is False
    assert result.findings_count == 0
    assert result.findings == []

    # Verify metadata captured from Browser Agent
    assert result.metadata["run_id"] == run_id
    assert "OmniSight" in result.metadata["page_title"]
    assert Path(result.metadata["screenshot_path"]).is_file()
    assert Path(result.metadata["dom_snapshot_path"]).is_file()
    assert Path(result.metadata["screenshot_path"]).stat().st_size > 0
    assert Path(result.metadata["dom_snapshot_path"]).stat().st_size > 0


def test_e2e_defect_state_overflow_inspection(demo_server: str, run_cleanup):
    """Verify defect state flow: Demo Site -> Browser Agent -> Vision Engine -> structured findings."""
    run_id = run_cleanup("e2e_test_overflow_002")

    request = InspectionRequest(
        target_url=f"{demo_server}/index.html",
        state=InspectionState.OVERFLOW,
        timeout=10.0,
    )

    result = execute_inspection_flow(request, run_id=run_id)

    assert isinstance(result, PipelineResult)
    assert result.success is True
    assert result.has_findings is True
    assert result.findings_count == 2

    # Verify findings are structured InspectionFinding instances
    overflow_findings = result.get_findings_by_category(DefectCategory.OVERFLOW)
    image_findings = result.get_findings_by_category(DefectCategory.BROKEN_IMAGE)

    assert len(overflow_findings) == 1
    assert len(image_findings) == 1

    finding_1 = overflow_findings[0]
    assert isinstance(finding_1, InspectionFinding)
    assert finding_1.defect_category == DefectCategory.OVERFLOW
    assert finding_1.severity == Severity.MEDIUM
    assert finding_1.confidence == 0.90
    assert "layout overflow" in finding_1.description
    assert finding_1.metadata["source"] == "mock"
    assert finding_1.metadata["evidence"]["screenshot_path"] == result.metadata["screenshot_path"]
    assert finding_1.metadata["evidence"]["dom_snapshot_path"] == result.metadata["dom_snapshot_path"]

    finding_2 = image_findings[0]
    assert finding_2.defect_category == DefectCategory.BROKEN_IMAGE
    assert finding_2.severity == Severity.LOW
    assert finding_2.confidence == 0.85


def test_e2e_dom_detector_with_live_captured_dom(demo_server: str, run_cleanup):
    """Verify live captured DOM evidence can be analyzed by Vision Engine's DOM issue detector."""
    run_id = run_cleanup("e2e_test_dom_003")

    request = InspectionRequest(
        target_url=f"{demo_server}/index.html",
        state=InspectionState.CLEAN,
        timeout=10.0,
    )

    # Supply detect_dom_issues as the detector callable
    result = execute_inspection_flow(
        request,
        detector=detect_dom_issues,
        run_id=run_id,
    )

    assert result.success is True
    assert result.has_findings is True

    # Check that heuristic DOM findings are properly normalized
    missing_elem_findings = result.get_findings_by_category(DefectCategory.MISSING_ELEMENT)
    assert len(missing_elem_findings) >= 1

    selectors = [f.selector for f in missing_elem_findings]
    assert "#nav-search-input" in selectors


def test_pipeline_adapter_execute_inspection_method(demo_server: str, run_cleanup):
    """Verify IntegrationPipelineAdapter.execute_inspection convenience method."""
    run_id = run_cleanup("e2e_test_adapter_004")

    adapter = IntegrationPipelineAdapter(name="custom_e2e_adapter", metadata={"pipeline_env": "integration_ci"})

    request = InspectionRequest(
        target_url=f"{demo_server}/index.html",
        state=InspectionState.OVERFLOW,
        timeout=10.0,
    )

    result = adapter.execute_inspection(request, run_id=run_id)

    assert result.success is True
    assert result.has_findings is True
    assert result.metadata["pipeline_env"] == "integration_ci"
    assert result.metadata["run_id"] == run_id


def test_vision_finding_to_inspection_finding_mapping():
    """Verify translation of VisionFinding model to shared InspectionFinding."""
    evidence = EvidenceReferences(
        screenshot_path="artifacts/r1/before.png",
        dom_snapshot_path="artifacts/r1/dom.html",
    )
    bbox = BoundingBox(x=10.0, y=20.0, width=100.0, height=50.0)

    # 1. layout_overflow -> DefectCategory.OVERFLOW
    vf1 = VisionFinding(
        finding_id="f-001",
        category="layout_overflow",
        severity="high",
        confidence=0.95,
        description="Text overflowing container boundary",
        selector="#metric-card",
        bounding_box=bbox,
        evidence=evidence,
        source="mock",
    )
    inf1 = vision_finding_to_inspection_finding(vf1)
    assert inf1.defect_category == DefectCategory.OVERFLOW
    assert inf1.severity == Severity.HIGH
    assert inf1.confidence == 0.95
    assert inf1.selector == "#metric-card"
    assert inf1.metadata["bounding_box"] == {"x": 10.0, "y": 20.0, "width": 100.0, "height": 50.0}
    assert inf1.metadata["finding_id"] == "f-001"

    # 2. missing_visible_element -> DefectCategory.MISSING_ELEMENT
    vf2 = VisionFinding(
        finding_id="f-002",
        category="missing_visible_element",
        severity="medium",
        confidence=0.88,
        description="Button #btn-heal missing from DOM",
        selector="#btn-heal",
        evidence=evidence,
    )
    inf2 = vision_finding_to_inspection_finding(vf2)
    assert inf2.defect_category == DefectCategory.MISSING_ELEMENT
    assert inf2.severity == Severity.MEDIUM

    # 3. broken_image -> DefectCategory.BROKEN_IMAGE
    vf3 = VisionFinding(
        finding_id="f-003",
        category="broken_image",
        severity="low",
        confidence=0.75,
        description="Broken image 404",
        selector="#topo-img",
        evidence=evidence,
    )
    inf3 = vision_finding_to_inspection_finding(vf3)
    assert inf3.defect_category == DefectCategory.BROKEN_IMAGE
    assert inf3.severity == Severity.LOW


def test_navigation_failure_handling():
    """Verify graceful failure handling when target URL is invalid or unreachable."""
    request = InspectionRequest(
        target_url="http://127.0.0.1:59999/unreachable",
        state=InspectionState.CLEAN,
        timeout=1.0,
    )

    # Use a small timeout so the test runs quickly
    result = execute_inspection_flow(request, run_id="failed_nav_run")

    assert result.success is False
    assert result.has_findings is False
    assert "error" in result.metadata


def test_missing_evidence_validation_handling(run_cleanup):
    """Verify that if browser navigation reports success but files are missing, evidence validator catches it."""
    run_id = run_cleanup("missing_evidence_run")

    class MockMissingFileNavigator:
        def navigate(self, url: str, run_id: str) -> NavigationResult:
            return NavigationResult(
                status="success",
                run_id=run_id,
                url=url,
                page_title="Dummy Page",
                captured_at="2026-10-23T00:00:00Z",
                viewport={"width": 1280, "height": 720},
                screenshot_path="artifacts/missing_dir/non_existent.png",
                dom_snapshot_path="artifacts/missing_dir/non_existent.html",
            )

    request = InspectionRequest(
        target_url="http://127.0.0.1:8080/index.html",
        state=InspectionState.CLEAN,
    )

    result = execute_inspection_flow(
        request,
        navigator=MockMissingFileNavigator(),
        run_id=run_id,
    )

    assert result.success is False
    assert result.has_findings is False
    assert "Evidence validation failed" in result.metadata["error"]
    assert "validation_errors" in result.metadata
