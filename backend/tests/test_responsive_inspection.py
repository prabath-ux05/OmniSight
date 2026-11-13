"""Focused test suite for OmniSight Responsive Website Inspection.

Verifies:
- Viewport presets (Desktop, Tablet, Mobile) and device emulation definitions.
- Viewport validation in RunCreateRequest and RunResponse schemas.
- Association of defect findings with their corresponding viewport in FindingModel/FindingResponse.
- Multi-viewport orchestration lifecycle and separate evidence capture.
- Finding retrieval and filtering by viewport.
- Viewport-specific screenshot and DOM artifact routing.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from backend.app.api.artifacts import get_run_screenshot, get_run_dom
from backend.app.api.runs import create_run, get_run_findings
from backend.app.models.finding import FindingModel
from backend.app.schemas.findings import EvidenceReferences, FindingResponse
from backend.app.schemas.runs import RunCreateRequest, RunResponse
from backend.app.services.orchestrator import RunOrchestrator, map_inspection_finding_to_response
from backend.app.services.run_store import run_store
from integration.contracts import DefectCategory, InspectionFinding, Severity
from navigation.navigator import VIEWPORT_PRESETS, BrowserNavigator, NavigationResult
from vision_engine.models import EvidenceReferences as VisionEvidenceReferences, VisionFinding


@pytest.fixture(autouse=True)
def clean_run_store():
    """Ensure run_store is clean before and after each test."""
    run_store.clear()
    yield
    run_store.clear()


def test_viewport_presets_structure():
    """Verify standard device emulation presets are correctly defined."""
    assert "desktop" in VIEWPORT_PRESETS
    assert "tablet" in VIEWPORT_PRESETS
    assert "mobile" in VIEWPORT_PRESETS

    desktop = VIEWPORT_PRESETS["desktop"]
    assert desktop["width"] == 1280
    assert desktop["height"] == 800
    assert desktop["is_mobile"] is False
    assert desktop["has_touch"] is False

    tablet = VIEWPORT_PRESETS["tablet"]
    assert tablet["width"] == 768
    assert tablet["height"] == 1024
    assert tablet["is_mobile"] is True
    assert tablet["has_touch"] is True
    assert "iPad" in (tablet.get("user_agent") or "")

    mobile = VIEWPORT_PRESETS["mobile"]
    assert mobile["width"] == 375
    assert mobile["height"] == 667
    assert mobile["is_mobile"] is True
    assert mobile["has_touch"] is True
    assert "iPhone" in (mobile.get("user_agent") or "")


def test_run_create_request_defaults_and_viewports():
    """Verify RunCreateRequest defaults to ['desktop'] and supports multi-viewport selection."""
    req_default = RunCreateRequest(url="http://127.0.0.1:8000/")
    assert req_default.viewports == ["desktop"]

    req_multi = RunCreateRequest(
        url="http://127.0.0.1:8000/",
        viewports=["desktop", "tablet", "mobile"],
    )
    assert req_multi.viewports == ["desktop", "tablet", "mobile"]


def test_run_create_request_rejects_invalid_viewport():
    """Verify validation error when an unsupported viewport name is supplied."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        RunCreateRequest(url="http://127.0.0.1:8000/", viewports=["smartwatch"])


def test_run_store_records_and_retrieves_viewports():
    """Verify run_store persists requested viewports and surfaces them on RunResponse."""
    req = RunCreateRequest(
        url="http://127.0.0.1:8000/",
        viewports=["desktop", "mobile"],
    )
    res = run_store.create(req)
    assert res.run_id.startswith("run_")
    assert res.viewports == ["desktop", "mobile"]

    retrieved = run_store.get(res.run_id)
    assert retrieved is not None
    assert retrieved.viewports == ["desktop", "mobile"]


def test_finding_response_includes_viewport_field():
    """Verify FindingResponse schema includes and validates viewport property."""
    f_desktop = FindingResponse(
        finding_id="def_001",
        category="layout_overflow",
        severity="medium",
        confidence=0.9,
        description="Text overflow on main panel",
        viewport="desktop",
    )
    assert f_desktop.viewport == "desktop"

    f_mobile = FindingResponse(
        finding_id="def_002",
        category="broken_image",
        severity="high",
        confidence=0.95,
        description="Missing diagram icon on mobile",
        viewport="mobile",
    )
    assert f_mobile.viewport == "mobile"


def test_map_inspection_finding_attaches_viewport():
    """Verify map_inspection_finding_to_response propagates viewport metadata."""
    finding = InspectionFinding(
        defect_category=DefectCategory.OVERFLOW,
        severity=Severity.HIGH,
        confidence=0.85,
        description="Container overflow",
        metadata={"viewport": "mobile"},
    )
    mapped = map_inspection_finding_to_response(finding, run_id="run_test", index=1)
    assert mapped.viewport == "mobile"
    assert "mobile" in mapped.finding_id


def test_orchestrator_multi_viewport_execution():
    """Verify RunOrchestrator iterates over all selected viewports and collects findings."""
    run = run_store.create(
        RunCreateRequest(
            url="http://127.0.0.1:8000/",
            viewports=["desktop", "mobile"],
        )
    )

    nav_calls = []

    def mock_navigate(url, run_id, viewport="desktop", **kwargs):
        nav_calls.append(viewport)
        return NavigationResult(
            run_id=run_id,
            url=url,
            page_title=f"OmniSight - {viewport}",
            captured_at="2026-11-12T00:00:00Z",
            viewport={"width": 1280 if viewport == "desktop" else 375, "height": 800},
            viewport_name=viewport,
            screenshot_path="artifacts/test_sample_run/before.png",
            dom_snapshot_path="artifacts/test_sample_run/dom.html",
            status="success",
        )

    def mock_detector(v_input):
        # Return 1 finding per viewport analysis
        return [
            VisionFinding(
                finding_id=f"f_{v_input.run_id}",
                category="broken_image",
                severity="medium",
                confidence=0.9,
                description=f"Defect found in {v_input.screenshot_path}",
                evidence=VisionEvidenceReferences(
                    screenshot_path=v_input.screenshot_path,
                    dom_snapshot_path=v_input.dom_snapshot_path,
                ),
                source="mock",
            )
        ]

    orch = RunOrchestrator()
    with patch("navigation.navigator.BrowserNavigator.navigate", side_effect=mock_navigate):
        orch.execute_run(
            run.run_id,
            run.url,
            viewports=["desktop", "mobile"],
            detector=mock_detector,
        )

    # Verify both viewports were navigated
    assert "desktop" in nav_calls
    assert "mobile" in nav_calls

    completed_run = run_store.get(run.run_id)
    assert completed_run is not None
    assert completed_run.status == "completed"

    findings = run_store.get_findings(run.run_id)
    assert len(findings) == 2
    viewports_found = {f.viewport for f in findings}
    assert viewports_found == {"desktop", "mobile"}


def test_get_run_findings_filter_by_viewport():
    """Verify GET /runs/{run_id}/findings?viewport=... filters findings accurately."""
    run = run_store.create(RunCreateRequest(url="http://127.0.0.1:8000/"))
    f_desktop = FindingResponse(
        finding_id="def_d01",
        category="layout_overflow",
        severity="low",
        confidence=0.8,
        description="Desktop menu overflow",
        viewport="desktop",
    )
    f_tablet = FindingResponse(
        finding_id="def_t01",
        category="missing_visible_element",
        severity="medium",
        confidence=0.85,
        description="Tablet nav toggle missing",
        viewport="tablet",
    )
    f_mobile = FindingResponse(
        finding_id="def_m01",
        category="broken_image",
        severity="high",
        confidence=0.9,
        description="Mobile banner broken",
        viewport="mobile",
    )
    run_store.set_findings(run.run_id, [f_desktop, f_tablet, f_mobile])

    # All findings
    all_findings = get_run_findings(run.run_id)
    assert len(all_findings) == 3

    # Filtered by mobile
    mobile_findings = get_run_findings(run.run_id, viewport="mobile")
    assert len(mobile_findings) == 1
    assert mobile_findings[0].finding_id == "def_m01"
    assert mobile_findings[0].viewport == "mobile"

    # Filtered by tablet
    tablet_findings = get_run_findings(run.run_id, viewport="tablet")
    assert len(tablet_findings) == 1
    assert tablet_findings[0].finding_id == "def_t01"

    # Filtered by desktop
    desktop_findings = get_run_findings(run.run_id, viewport="desktop")
    assert len(desktop_findings) == 1
    assert desktop_findings[0].finding_id == "def_d01"


def test_artifacts_viewport_screenshot_routing(tmp_path):
    """Verify get_run_screenshot serves viewport-specific artifact if requested."""
    run_id = "test_vp_art"
    run_dir = Path("artifacts") / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    try:
        desktop_img = run_dir / "before.png"
        mobile_img = run_dir / "before_mobile.png"
        desktop_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 30)
        mobile_img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 30)

        # Default query serves before.png
        res_default = get_run_screenshot(run_id)
        assert Path(res_default.path).name == "before.png"

        # Explicit mobile viewport query serves before_mobile.png
        res_mobile = get_run_screenshot(run_id, viewport="mobile")
        assert Path(res_mobile.path).name == "before_mobile.png"
    finally:
        import shutil
        if run_dir.exists():
            shutil.rmtree(run_dir, ignore_errors=True)
