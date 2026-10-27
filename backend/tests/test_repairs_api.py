"""Tests for the Self-Healing Locator Repair API endpoint (/api/v1/runs/{run_id}/repair).

Requirements verified:
- Endpoint success for valid missing-element repair.
- Invalid run_id format returns 400.
- Unknown run_id returns 404.
- Unknown finding_id returns 404.
- Unsupported finding category returns safe non-repaired result.
- Missing DOM evidence file returns safe non-repaired result with explanation.
- No valid/unresolvable candidate returns safe non-repaired result.
- GET and POST methods both supported.
"""

from __future__ import annotations

import shutil
from pathlib import Path
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.findings import EvidenceReferences, FindingResponse
from backend.app.schemas.runs import RunCreateRequest
from backend.app.services.run_store import run_store

SAMPLE_DOM_HTML = """<!DOCTYPE html>
<html>
<body>
  <div id="hero-actions-container">
    <button
      id="btn-trigger-self-heal"
      class="btn-primary cta-action-btn"
      type="button"
      data-testid="trigger-self-heal-cta"
      aria-label="Trigger Self-Healing Workflow"
    >
      <span class="btn-text">Trigger Self-Healing Job</span>
    </button>
  </div>
</body>
</html>
"""


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def setup_run_with_dom(tmp_path):
    """Fixture creating a run in run_store with sample DOM artifact on disk."""
    run_id = "run_test_repair_001"
    run_obj = run_store.create(RunCreateRequest(url="http://127.0.0.1:8080/index.html"))
    test_run_id = run_obj.run_id

    # Create artifact DOM file on disk
    artifact_dir = Path("artifacts") / test_run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    dom_file = artifact_dir / "dom.html"
    dom_file.write_text(SAMPLE_DOM_HTML, encoding="utf-8")

    yield test_run_id, str(dom_file)

    # Teardown
    run_store._runs.pop(test_run_id, None)
    run_store._findings.pop(test_run_id, None)
    run_store._repairs.pop(test_run_id, None)
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir, ignore_errors=True)


# ============================================================================
# 1. Endpoint Success Tests
# ============================================================================

def test_repair_endpoint_success(client: TestClient, setup_run_with_dom):
    """Verify successful repair suggestion via POST /api/v1/runs/{run_id}/repair."""
    run_id, dom_path = setup_run_with_dom
    finding = FindingResponse(
        finding_id="f_missing_01",
        category="missing_visible_element",
        severity="medium",
        confidence=0.85,
        description="Missing CTA button locator.",
        selector="#btn-trigger-self-heal",
        evidence=EvidenceReferences(dom_snapshot_path=dom_path),
        source="mock",
    )
    run_store.set_findings(run_id, [finding])

    resp = client.post(f"/api/v1/runs/{run_id}/repair")
    assert resp.status_code == 200
    data = resp.json()

    assert isinstance(data, list)
    assert len(data) == 1

    repair = data[0]
    assert repair["finding_id"] == "f_missing_01"
    assert repair["original_selector"] == "#btn-trigger-self-heal"
    assert repair["repaired"] is True
    assert repair["best_locator"] == '[data-testid="trigger-self-heal-cta"]'
    assert repair["strategy"] == "data_attribute"
    assert repair["confidence"] == 0.95
    assert repair["validation"]["is_valid"] is True
    assert repair["validation"]["matches"] == 1
    assert "Successfully repaired locator" in repair["reason"]


def test_repair_endpoint_specific_finding_id(client: TestClient, setup_run_with_dom):
    """Verify repairing a specific finding via query param or request body."""
    run_id, dom_path = setup_run_with_dom
    finding1 = FindingResponse(
        finding_id="f_target_01",
        category="missing_visible_element",
        severity="high",
        confidence=0.88,
        description="Target missing element",
        selector="#btn-trigger-self-heal",
        evidence=EvidenceReferences(dom_snapshot_path=dom_path),
    )
    finding2 = FindingResponse(
        finding_id="f_other_02",
        category="layout_overflow",
        severity="low",
        confidence=0.70,
        description="Overflow issue",
        selector="#panel",
    )
    run_store.set_findings(run_id, [finding1, finding2])

    # 1. Query parameter
    resp_query = client.post(f"/api/v1/runs/{run_id}/repair?finding_id=f_target_01")
    assert resp_query.status_code == 200
    data_query = resp_query.json()
    assert len(data_query) == 1
    assert data_query[0]["finding_id"] == "f_target_01"
    assert data_query[0]["repaired"] is True

    # 2. JSON Body
    resp_body = client.post(f"/api/v1/runs/{run_id}/repair", json={"finding_id": "f_target_01"})
    assert resp_body.status_code == 200
    data_body = resp_body.json()
    assert len(data_body) == 1
    assert data_body[0]["finding_id"] == "f_target_01"


def test_repair_endpoint_get_method(client: TestClient, setup_run_with_dom):
    """Verify GET /api/v1/runs/{run_id}/repair operates idempotently."""
    run_id, dom_path = setup_run_with_dom
    finding = FindingResponse(
        finding_id="f_get_01",
        category="missing_visible_element",
        severity="medium",
        confidence=0.85,
        description="Missing CTA button locator.",
        selector="#btn-trigger-self-heal",
        evidence=EvidenceReferences(dom_snapshot_path=dom_path),
    )
    run_store.set_findings(run_id, [finding])

    resp = client.get(f"/api/v1/runs/{run_id}/repair")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["repaired"] is True


# ============================================================================
# 2. Error and Edge Case Tests
# ============================================================================

def test_repair_endpoint_invalid_run_id_400(client: TestClient):
    """Verify empty or whitespace run_id returns 400 Bad Request."""
    resp = client.post("/api/v1/runs/%20/repair")
    assert resp.status_code == 400
    assert "Invalid run_id" in resp.json()["detail"]


def test_repair_endpoint_unknown_run_404(client: TestClient):
    """Verify unknown run_id returns 404 Not Found."""
    resp = client.post("/api/v1/runs/run_unknown_99999/repair")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_repair_endpoint_unknown_finding_404(client: TestClient, setup_run_with_dom):
    """Verify requesting non-existent finding_id on valid run returns 404 Not Found."""
    run_id, _ = setup_run_with_dom
    resp = client.post(f"/api/v1/runs/{run_id}/repair?finding_id=finding_does_not_exist")
    assert resp.status_code == 404
    assert "not found in run" in resp.json()["detail"].lower()


def test_repair_endpoint_unsupported_category_skips_safely(client: TestClient, setup_run_with_dom):
    """Verify unsupported categories (e.g. layout_overflow) return safe non-repaired result."""
    run_id, dom_path = setup_run_with_dom
    finding = FindingResponse(
        finding_id="f_overflow_01",
        category="layout_overflow",
        severity="high",
        confidence=0.90,
        description="Text overflows panel boundary.",
        selector="#overflow-panel",
        evidence=EvidenceReferences(dom_snapshot_path=dom_path),
    )
    run_store.set_findings(run_id, [finding])

    resp = client.post(f"/api/v1/runs/{run_id}/repair?finding_id=f_overflow_01")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["repaired"] is False
    assert "not a missing visible element" in data[0]["reason"]


def test_repair_endpoint_missing_evidence_fails_safely(client: TestClient, setup_run_with_dom):
    """Verify missing/non-existent DOM evidence returns safe non-repaired result with reason."""
    run_id, _ = setup_run_with_dom
    finding = FindingResponse(
        finding_id="f_no_dom_01",
        category="missing_visible_element",
        severity="medium",
        confidence=0.80,
        description="Missing button with absent DOM file.",
        selector="#btn-trigger-self-heal",
        evidence=EvidenceReferences(dom_snapshot_path="artifacts/fake_path/missing.html"),
    )
    run_store.set_findings(run_id, [finding])

    resp = client.post(f"/api/v1/runs/{run_id}/repair?finding_id=f_no_dom_01")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["repaired"] is False
    assert "not found on disk" in data[0]["reason"]


def test_repair_endpoint_no_valid_candidate_in_dom(client: TestClient, setup_run_with_dom):
    """Verify selector that cannot be resolved to any candidate in DOM snapshot returns safe result."""
    run_id, dom_path = setup_run_with_dom
    finding = FindingResponse(
        finding_id="f_unresolvable_01",
        category="missing_visible_element",
        severity="medium",
        confidence=0.80,
        description="Completely alien element.",
        selector="#completely-alien-element-xyz-987",
        evidence=EvidenceReferences(dom_snapshot_path=dom_path),
    )
    run_store.set_findings(run_id, [finding])

    resp = client.post(f"/api/v1/runs/{run_id}/repair?finding_id=f_unresolvable_01")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["repaired"] is False
    assert "No suitable replacement element" in data[0]["reason"]


# ============================================================================
# 3. Live Verification & VLM Config Tests
# ============================================================================

def test_vlm_config_endpoint_mock(client: TestClient, monkeypatch):
    """Verify GET /api/v1/runs/vlm/config reports readiness without leaking keys."""
    monkeypatch.setenv("VLM_PROVIDER", "mock")
    resp = client.get("/api/v1/runs/vlm/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "mock"
    assert data["is_configured"] is True
    assert data["api_key_status"] == "not_required"
    assert "Mock provider active" in data["message"]


def test_vlm_config_endpoint_gemini_missing_key(client: TestClient, monkeypatch):
    """Verify Gemini provider reports actionable missing key guidance without crashing."""
    monkeypatch.setenv("VLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    resp = client.get("/api/v1/runs/vlm/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "gemini"
    assert data["is_configured"] is False
    assert data["api_key_status"] == "missing"
    assert "GEMINI_API_KEY" in data["message"]


def test_vlm_config_endpoint_openai_masked_key(client: TestClient, monkeypatch):
    """Verify OpenAI provider masks API key and does not leak it."""
    monkeypatch.setenv("VLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proj-secretkey1234567890abcdef")
    resp = client.get("/api/v1/runs/vlm/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["provider"] == "openai"
    assert data["is_configured"] is True
    assert data["api_key_status"] == "...cdef"
    assert "secretkey" not in str(data)


def test_repair_endpoint_with_live_verification(client: TestClient, setup_run_with_dom, monkeypatch):
    """Verify POST /api/v1/runs/{run_id}/repair?verify_live=true calls live verification."""
    from self_healing.models import LiveVerificationResult
    import self_healing.repair_engine

    run_id, dom_path = setup_run_with_dom
    finding = FindingResponse(
        finding_id="f_live_01",
        category="missing_visible_element",
        severity="medium",
        confidence=0.85,
        description="Missing CTA button locator.",
        selector="#btn-trigger-self-heal",
        evidence=EvidenceReferences(dom_snapshot_path=dom_path),
        source="mock",
    )
    run_store.set_findings(run_id, [finding])

    # Mock verify_locator_on_live_page to return a live verification result
    def mock_verify_live(target_url, selector, **kwargs):
        return LiveVerificationResult(
            attempted=True,
            is_verified=True,
            matches=1,
            target_url=target_url,
            resolved_tag="BUTTON",
            validation_message=f"Selector '{selector}' verified uniquely on live page.",
        )

    monkeypatch.setattr(
        self_healing.repair_engine,
        "verify_locator_on_live_page",
        mock_verify_live,
    )

    resp = client.post(f"/api/v1/runs/{run_id}/repair?verify_live=true")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    repair = data[0]

    assert repair["repaired"] is True
    assert repair["snapshot_validation"]["is_valid"] is True
    assert repair["live_verification"] is not None
    assert repair["live_verification"]["attempted"] is True
    assert repair["live_verification"]["is_verified"] is True
    assert repair["live_verification"]["matches"] == 1
    assert "verified uniquely on live page" in repair["live_verification"]["validation_message"]
