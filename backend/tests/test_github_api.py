"""API Integration Tests for GitHub Integration, Proposals, and PR Workflow.

Requirements verified:
- GET /api/v1/github/config reports masked configuration without leaking tokens.
- POST /api/v1/runs/{run_id}/proposals converts verified repairs into structured proposals.
- GET /api/v1/runs/{run_id}/proposals retrieves cached proposals.
- POST /api/v1/runs/{run_id}/proposals/{prop_id}/patch generates minimal diffs safely.
- Patch endpoint strictly rejects traversal (400) and OmniSight internals (400).
- POST /api/v1/runs/{run_id}/proposals/{prop_id}/pull-request enforces human approval:
  * user_approved=False returns 403 Forbidden.
  * user_approved=True allows PR creation / simulation.
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
      class="btn-primary"
      type="button"
      data-testid="trigger-self-heal-cta"
    >
      <span>Trigger Self-Healing Job</span>
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
def run_with_repair(tmp_path: Path):
    """Fixture creating a run in run_store with sample DOM and an existing repaired finding."""
    run_obj = run_store.create(RunCreateRequest(url="http://127.0.0.1:8080/index.html"))
    test_run_id = run_obj.run_id

    # Create artifact DOM file on disk
    artifact_dir = Path("artifacts") / test_run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)
    dom_file = artifact_dir / "dom.html"
    dom_file.write_text(SAMPLE_DOM_HTML, encoding="utf-8")

    # Target test file in a temp project
    project_dir = tmp_path / "target_project"
    project_dir.mkdir()
    test_file = project_dir / "test_suite.py"
    test_file.write_text(
        'def test_cta():\n'
        '    page.locator("#btn-trigger-self-heal").click()\n',
        encoding="utf-8",
    )

    finding = FindingResponse(
        finding_id="f_missing_cta",
        category="missing_visible_element",
        severity="high",
        confidence=0.92,
        description="Missing CTA button locator.",
        selector="#btn-trigger-self-heal",
        evidence=EvidenceReferences(dom_snapshot_path=str(dom_file)),
        source="mock",
    )
    run_store.set_findings(test_run_id, [finding])

    yield {
        "run_id": test_run_id,
        "finding_id": "f_missing_cta",
        "project_dir": str(project_dir),
        "test_file_rel": "test_suite.py",
        "test_file_abs": str(test_file),
    }

    # Teardown
    run_store.clear()
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir, ignore_errors=True)


# =============================================================================
# 1. GitHub Config Endpoint Tests
# =============================================================================

def test_github_config_endpoint_masked(client: TestClient, monkeypatch):
    """Verify /api/v1/github/config returns masked token and does not leak secrets."""
    monkeypatch.setenv("GITHUB_ACCESS_TOKEN", "ghp_secretaccesstoken123456789")
    monkeypatch.setenv("GITHUB_REPO_OWNER", "org-alpha")
    monkeypatch.setenv("GITHUB_REPO_NAME", "repo-beta")

    resp = client.get("/api/v1/github/config")
    assert resp.status_code == 200
    data = resp.json()

    assert data["is_configured"] is True
    assert data["owner"] == "org-alpha"
    assert data["repo"] == "repo-beta"
    assert data["token_status"] == "...6789"
    assert "secretaccesstoken" not in resp.text
    assert data["approval_gate_required"] is True


def test_github_config_endpoint_unconfigured(client: TestClient, monkeypatch):
    monkeypatch.delenv("GITHUB_ACCESS_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_REPO_OWNER", raising=False)
    monkeypatch.delenv("GITHUB_REPO_NAME", raising=False)

    resp = client.get("/api/v1/github/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_configured"] is False
    assert data["token_status"] == "missing"


# =============================================================================
# 2. Proposal Generation & Retrieval Tests
# =============================================================================

def test_generate_and_get_proposals(client: TestClient, run_with_repair):
    run_id = run_with_repair["run_id"]

    # 1. POST proposals
    post_resp = client.post(
        f"/api/v1/runs/{run_id}/proposals",
        json={
            "target_file": run_with_repair["test_file_rel"],
            "workspace_root": run_with_repair["project_dir"],
        },
    )
    assert post_resp.status_code == 200
    proposals = post_resp.json()
    assert len(proposals) == 1

    prop = proposals[0]
    assert prop["run_id"] == run_id
    assert prop["finding_id"] == "f_missing_cta"
    assert prop["original_selector"] == "#btn-trigger-self-heal"
    assert prop["proposed_locator"] == '[data-testid="trigger-self-heal-cta"]'
    assert prop["patch"] is not None
    assert prop["patch"]["success"] is True
    assert prop["patch"]["diff"] is not None
    assert "+    page.locator(\"[data-testid=\"trigger-self-heal-cta\"]\").click()" in prop["patch"]["diff"]

    # 2. GET proposals returns cached proposals
    get_resp = client.get(f"/api/v1/runs/{run_id}/proposals")
    assert get_resp.status_code == 200
    cached = get_resp.json()
    assert len(cached) == 1
    assert cached[0]["proposal_id"] == prop["proposal_id"]


# =============================================================================
# 3. Patch Generation & Security Rejection Tests
# =============================================================================

def test_generate_patch_endpoint_security_rejections(client: TestClient, run_with_repair):
    run_id = run_with_repair["run_id"]
    prop_resp = client.post(f"/api/v1/runs/{run_id}/proposals")
    proposal_id = prop_resp.json()[0]["proposal_id"]

    # Path traversal rejection (400)
    res_traversal = client.post(
        f"/api/v1/runs/{run_id}/proposals/{proposal_id}/patch",
        json={"target_file": "../../etc/shadow"},
    )
    assert res_traversal.status_code == 400
    assert "traversal" in res_traversal.json()["detail"].lower()

    # OmniSight internal file rejection (400)
    res_internal = client.post(
        f"/api/v1/runs/{run_id}/proposals/{proposal_id}/patch",
        json={"target_file": "backend/app/main.py"},
    )
    assert res_internal.status_code == 400
    assert "refusing to generate patch targeting omnisight internal" in res_internal.json()["detail"].lower()


# =============================================================================
# 4. Pull Request Submission & Approval Gate Tests
# =============================================================================

def test_submit_pr_strictly_enforces_approval_gate(client: TestClient, run_with_repair):
    """Verify that user_approved=False returns 403 Forbidden."""
    run_id = run_with_repair["run_id"]
    prop_resp = client.post(f"/api/v1/runs/{run_id}/proposals")
    proposal_id = prop_resp.json()[0]["proposal_id"]

    # Attempt submission without approval (both simulate=False and simulate=True)
    res = client.post(
        f"/api/v1/runs/{run_id}/proposals/{proposal_id}/pull-request",
        json={"user_approved": False},
    )
    assert res.status_code == 403
    assert "user approval" in res.json()["detail"].lower()

    res_sim_unapproved = client.post(
        f"/api/v1/runs/{run_id}/proposals/{proposal_id}/pull-request",
        json={"user_approved": False, "simulate": True},
    )
    assert res_sim_unapproved.status_code == 403
    assert "user approval" in res_sim_unapproved.json()["detail"].lower()


def test_submit_pr_with_user_approval_simulated(client: TestClient, run_with_repair):
    """Verify that user_approved=True with simulate=True succeeds."""
    run_id = run_with_repair["run_id"]
    prop_resp = client.post(f"/api/v1/runs/{run_id}/proposals")
    proposal_id = prop_resp.json()[0]["proposal_id"]

    res = client.post(
        f"/api/v1/runs/{run_id}/proposals/{proposal_id}/pull-request",
        json={"user_approved": True, "simulate": True},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "simulated"
    assert data["simulated"] is True
    assert data["success"] is True
    assert data["pr_number"] is None
    assert data["pr_url"] is None
    assert "omnisight/heal-f-missing-cta" in data["branch_name"]

    # Verify proposal status updated to remotely_submitted (simulated)
    get_prop = client.get(f"/api/v1/runs/{run_id}/proposals")
    assert get_prop.status_code == 200
    updated_prop = get_prop.json()[0]
    assert updated_prop["status"] == "remotely_submitted"
    assert updated_prop["pr_url"] is None
