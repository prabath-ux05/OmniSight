"""Live End-to-End Integration Tests for OmniSight Pipeline.

Proves the complete real flow:
Demo Site (SUT) -> Playwright Browser Agent -> Evidence Capture ->
Integration Pipeline -> Vision Detector -> Backend RunStore ->
API Endpoints -> Frontend-consumable artifacts/findings.

Requirements verified:
- Live local demo site served via ThreadedHTTPServer.
- Real Playwright browser navigation (NO mocks for BrowserNavigator).
- Full run creation via POST /api/v1/runs?auto_execute=true across:
  * clean state
  * ?defect=overflow
  * ?defect=missing
  * ?defect=image
- Verification that before.png and dom.html are created, non-empty, and readable.
- Verification that findings returned by GET /api/v1/runs/{run_id}/findings conform to FindingResponse.
- Verification that GET /api/v1/artifacts/{run_id}/before.png serves the real image.
- Complete contract round-trip validation for categories, severities, confidence, and source.
- Clean resource and artifact teardown.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Generator
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.findings import EvidenceReferences, FindingResponse
from backend.app.schemas.runs import RunCreateRequest
from backend.app.services.orchestrator import (
    map_defect_category,
    map_inspection_finding_to_response,
    map_severity,
)
from backend.app.services.run_store import run_store
from integration.contracts import DefectCategory, InspectionFinding, Severity
from tests.test_demo_site import DEMO_SITE_DIR, ThreadedHTTPServer


@pytest.fixture(scope="module")
def live_demo_server() -> Generator[str, None, None]:
    """Spin up a real HTTP server serving demo_site/ on an ephemeral local port."""
    server = ThreadedHTTPServer(DEMO_SITE_DIR)
    server.start()
    base_url = f"http://127.0.0.1:{server.port}"
    try:
        yield base_url
    finally:
        server.stop()


@pytest.fixture
def api_client() -> Generator[TestClient, None, None]:
    """FastAPI test client instance."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(autouse=True)
def clean_store():
    """Ensure run store is clean before and after each test."""
    run_store.clear()
    yield
    run_store.clear()


@pytest.fixture
def run_cleanup() -> Generator[callable, None, None]:
    """Track run IDs and remove generated artifact folders upon test completion."""
    run_ids: list[str] = []

    def _register(run_id: str) -> str:
        run_ids.append(run_id)
        return run_id

    yield _register

    for rid in run_ids:
        artifact_dir = Path("artifacts") / rid
        if artifact_dir.exists():
            shutil.rmtree(artifact_dir, ignore_errors=True)


def poll_run_until_terminal(
    client: TestClient,
    run_id: str,
    timeout: float = 30.0,
) -> dict:
    """Poll GET /api/v1/runs/{run_id} until terminal state is reached."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        resp = client.get(f"/api/v1/runs/{run_id}")
        assert resp.status_code == 200, f"Lookup failed: {resp.text}"
        data = resp.json()
        if data["status"] in ("completed", "failed", "cancelled"):
            return data
        time.sleep(0.5)

    raise TimeoutError(f"Run '{run_id}' timed out waiting for terminal state after {timeout}s.")


# =============================================================================
# 1. Live E2E Tests Across Target States (Real Playwright Navigation)
# =============================================================================

def test_live_e2e_clean_state(live_demo_server: str, api_client: TestClient, run_cleanup):
    """Test full live inspection on clean state with real Playwright navigation."""
    target_url = f"{live_demo_server}/index.html"

    # 1. Initiate run with auto_execute=true
    resp = api_client.post("/api/v1/runs?auto_execute=true", json={"url": target_url})
    assert resp.status_code == 201
    run_data = resp.json()
    run_id = run_cleanup(run_data["run_id"])
    assert run_id.startswith("run_")

    # 2. Poll until terminal
    final_run = poll_run_until_terminal(api_client, run_id)
    assert final_run["status"] == "completed"
    assert final_run["error"] is None
    assert "Inspection complete" in final_run["message"]

    # 3. Verify real artifacts created on disk
    screenshot_file = Path("artifacts") / run_id / "before.png"
    dom_file = Path("artifacts") / run_id / "dom.html"

    assert screenshot_file.exists(), f"Missing screenshot artifact at {screenshot_file}"
    assert screenshot_file.is_file()
    assert screenshot_file.stat().st_size > 1000, "Screenshot file is unexpectedly small"

    assert dom_file.exists(), f"Missing DOM artifact at {dom_file}"
    assert dom_file.is_file()
    assert dom_file.stat().st_size > 500, "DOM snapshot is unexpectedly small"

    dom_content = dom_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in dom_content
    assert "NovaMetrics" in dom_content

    # 4. Verify findings endpoint response conforms to FindingResponse schema
    findings_resp = api_client.get(f"/api/v1/runs/{run_id}/findings")
    assert findings_resp.status_code == 200
    findings_data = findings_resp.json()
    assert isinstance(findings_data, list)

    for item in findings_data:
        # Validate against Pydantic schema
        validated = FindingResponse(**item)
        assert validated.category in ("layout_overflow", "missing_visible_element", "broken_image")
        assert validated.severity in ("low", "medium", "high", "critical")
        assert 0.0 <= validated.confidence <= 1.0
        assert validated.source in ("mock", "vlm")
        assert validated.evidence.screenshot_path is not None
        assert validated.evidence.dom_snapshot_path is not None

    # 5. Verify artifact endpoint serves before.png
    artifact_resp = api_client.get(f"/api/v1/artifacts/{run_id}/before.png")
    assert artifact_resp.status_code == 200
    assert artifact_resp.headers["content-type"] == "image/png"
    assert len(artifact_resp.content) == screenshot_file.stat().st_size
    assert artifact_resp.content.startswith(b"\x89PNG\r\n\x1a\n")

    # 6. Verify artifact endpoint serves dom.html
    dom_resp = api_client.get(f"/api/v1/artifacts/{run_id}/dom.html")
    assert dom_resp.status_code == 200
    assert "text/html" in dom_resp.headers["content-type"]
    assert len(dom_resp.content) == dom_file.stat().st_size


def test_live_e2e_defect_overflow(live_demo_server: str, api_client: TestClient, run_cleanup):
    """Test full live inspection on ?defect=overflow state with real Playwright."""
    target_url = f"{live_demo_server}/index.html?defect=overflow"

    resp = api_client.post("/api/v1/runs?auto_execute=true", json={"url": target_url})
    assert resp.status_code == 201
    run_id = run_cleanup(resp.json()["run_id"])

    final_run = poll_run_until_terminal(api_client, run_id)
    assert final_run["status"] == "completed"

    # Artifacts exist and readable
    screenshot_file = Path("artifacts") / run_id / "before.png"
    dom_file = Path("artifacts") / run_id / "dom.html"
    assert screenshot_file.is_file() and screenshot_file.stat().st_size > 1000
    assert dom_file.is_file() and dom_file.stat().st_size > 500

    # Defect state reflected in captured DOM
    dom_content = dom_file.read_text(encoding="utf-8")
    assert 'data-defect-overflow="true"' in dom_content

    # Artifact endpoint serves screenshot
    artifact_resp = api_client.get(f"/api/v1/artifacts/{run_id}/before.png")
    assert artifact_resp.status_code == 200
    assert artifact_resp.headers["content-type"] == "image/png"


def test_live_e2e_defect_missing_element(live_demo_server: str, api_client: TestClient, run_cleanup):
    """Test full live inspection on ?defect=missing state with real Playwright."""
    target_url = f"{live_demo_server}/index.html?defect=missing"

    resp = api_client.post("/api/v1/runs?auto_execute=true", json={"url": target_url})
    assert resp.status_code == 201
    run_id = run_cleanup(resp.json()["run_id"])

    final_run = poll_run_until_terminal(api_client, run_id)
    assert final_run["status"] == "completed"

    screenshot_file = Path("artifacts") / run_id / "before.png"
    dom_file = Path("artifacts") / run_id / "dom.html"
    assert screenshot_file.is_file() and screenshot_file.stat().st_size > 1000
    assert dom_file.is_file() and dom_file.stat().st_size > 500

    # Defect state reflected in captured DOM
    dom_content = dom_file.read_text(encoding="utf-8")
    assert 'data-defect-missing="true"' in dom_content

    artifact_resp = api_client.get(f"/api/v1/artifacts/{run_id}/before.png")
    assert artifact_resp.status_code == 200


def test_live_e2e_defect_broken_image(live_demo_server: str, api_client: TestClient, run_cleanup):
    """Test full live inspection on ?defect=image state with real Playwright."""
    target_url = f"{live_demo_server}/index.html?defect=image"

    resp = api_client.post("/api/v1/runs?auto_execute=true", json={"url": target_url})
    assert resp.status_code == 201
    run_id = run_cleanup(resp.json()["run_id"])

    final_run = poll_run_until_terminal(api_client, run_id)
    assert final_run["status"] == "completed"

    screenshot_file = Path("artifacts") / run_id / "before.png"
    dom_file = Path("artifacts") / run_id / "dom.html"
    assert screenshot_file.is_file() and screenshot_file.stat().st_size > 1000
    assert dom_file.is_file() and dom_file.stat().st_size > 500

    # Defect state reflected in captured DOM
    dom_content = dom_file.read_text(encoding="utf-8")
    assert 'data-defect-broken-image="true"' in dom_content

    artifact_resp = api_client.get(f"/api/v1/artifacts/{run_id}/before.png")
    assert artifact_resp.status_code == 200


def test_live_e2e_unreachable_target_fails_gracefully(api_client: TestClient, run_cleanup):
    """Test live pipeline failure handling when target URL is completely unreachable."""
    unreachable_url = "http://127.0.0.1:59998/nonexistent"

    resp = api_client.post("/api/v1/runs?auto_execute=true", json={"url": unreachable_url})
    assert resp.status_code == 201
    run_id = run_cleanup(resp.json()["run_id"])

    final_run = poll_run_until_terminal(api_client, run_id)
    assert final_run["status"] == "failed"
    assert final_run["error"] is not None


# =============================================================================
# 2. Complete Finding Round-Trip Contract Tests
# =============================================================================

@pytest.mark.parametrize(
    ("pipeline_category", "expected_backend_category"),
    [
        (DefectCategory.OVERFLOW, "layout_overflow"),
        ("overflow", "layout_overflow"),
        (DefectCategory.MISSING_ELEMENT, "missing_visible_element"),
        ("missing_element", "missing_visible_element"),
        (DefectCategory.BROKEN_IMAGE, "broken_image"),
        ("broken_image", "broken_image"),
    ],
)
def test_contract_roundtrip_category_mapping(pipeline_category, expected_backend_category, api_client: TestClient):
    """Verify complete category round-trip from pipeline contract through backend API."""
    run_id = "run_roundtrip_cat"
    finding = InspectionFinding(
        defect_category=pipeline_category,
        severity=Severity.MEDIUM,
        description=f"Round-trip test for {pipeline_category}",
        selector="#target",
        confidence=0.88,
        metadata={"finding_id": f"finding_{expected_backend_category}", "source": "mock"},
    )

    defaults = EvidenceReferences(
        screenshot_path=f"artifacts/{run_id}/before.png",
        dom_snapshot_path=f"artifacts/{run_id}/dom.html",
    )

    # 1. Map to FindingResponse
    response_obj = map_inspection_finding_to_response(finding, run_id=run_id, default_evidence=defaults)
    assert response_obj.category == expected_backend_category

    # 2. Store in run_store and query via API
    run_obj = run_store.create(RunCreateRequest(url="http://test.local"))
    test_run_id = run_obj.run_id
    response_obj = map_inspection_finding_to_response(finding, run_id=test_run_id, default_evidence=defaults)
    run_store.set_findings(test_run_id, [response_obj])
    try:
        api_resp = api_client.get(f"/api/v1/runs/{test_run_id}/findings")
        assert api_resp.status_code == 200
        stored_findings = api_resp.json()
        assert len(stored_findings) == 1
        assert stored_findings[0]["category"] == expected_backend_category
    finally:
        run_store._runs.pop(test_run_id, None)
        run_store._findings.pop(test_run_id, None)


@pytest.mark.parametrize(
    "valid_severity",
    [Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL],
)
def test_contract_roundtrip_valid_severities(valid_severity, api_client: TestClient):
    """Verify severities survive round-trip without corruption."""
    run_id = f"run_sev_{valid_severity.value}"
    finding = InspectionFinding(
        defect_category=DefectCategory.BROKEN_IMAGE,
        severity=valid_severity,
        description="Severity roundtrip",
        confidence=0.75,
    )

    response_obj = map_inspection_finding_to_response(finding, run_id=run_id)
    assert response_obj.severity == valid_severity.value


def test_contract_roundtrip_info_severity_raises_error():
    """Verify 'info' severity cannot round-trip to backend FindingResponse schema."""
    with pytest.raises(ValueError, match="not permitted by the backend FindingResponse schema"):
        map_severity(Severity.INFO)


def test_contract_roundtrip_exact_confidence_preserved(api_client: TestClient):
    """Verify detector confidence score is exact and never fabricated or altered."""
    test_confidences = [0.0, 0.5, 0.7, 0.85, 0.99, 1.0]
    for conf in test_confidences:
        finding = InspectionFinding(
            defect_category=DefectCategory.OVERFLOW,
            severity=Severity.HIGH,
            description="Confidence precision check",
            confidence=conf,
        )
        response_obj = map_inspection_finding_to_response(finding, run_id="run_conf")
        assert response_obj.confidence == conf


def test_contract_roundtrip_source_preservation(api_client: TestClient):
    """Verify finding source never falsely becomes 'vlm' when detector is mocked."""
    # 1. Mock source
    mock_finding = InspectionFinding(
        defect_category=DefectCategory.OVERFLOW,
        severity=Severity.LOW,
        description="Mock source finding",
        confidence=0.8,
        metadata={"source": "mock"},
    )
    mock_resp = map_inspection_finding_to_response(mock_finding, run_id="run_src_mock")
    assert mock_resp.source == "mock"

    # 2. VLM source (only when explicitly declared)
    vlm_finding = InspectionFinding(
        defect_category=DefectCategory.OVERFLOW,
        severity=Severity.HIGH,
        description="VLM source finding",
        confidence=0.95,
        metadata={"source": "vlm"},
    )
    vlm_resp = map_inspection_finding_to_response(vlm_finding, run_id="run_src_vlm")
    assert vlm_resp.source == "vlm"

    # 3. Default/unspecified source must default to 'mock', never falsely 'vlm'
    default_finding = InspectionFinding(
        defect_category=DefectCategory.OVERFLOW,
        severity=Severity.LOW,
        description="Default source finding",
        confidence=0.8,
        metadata={},
    )
    default_resp = map_inspection_finding_to_response(default_finding, run_id="run_src_default")
    assert default_resp.source == "mock"
