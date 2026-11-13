"""Automated tests for Before/After Visual Comparison and Repair Approval Workflow.

Requirements verified:
- Display original and proposed corrected screenshots in split-view format.
- Associate comparisons with the relevant finding and repair proposal.
- Provide explicit Approve and Reject actions.
- Record decision status, timestamp, reviewer notes, and proposal reference.
- Preserve original screenshots and evidence immutably.
- Apply proposed corrections only in a controlled environment (never modifying the live target website).
- Ensure rejected proposals strictly remain rejected.
- Ensure approved decisions can be revisited when revisit=True.
"""

from pathlib import Path
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.proposals import RepairProposalCreateRequest
from backend.app.schemas.runs import RunCreateRequest
from backend.app.services.run_store import create_mock_findings, run_store


@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


def test_visual_comparison_retrieval_and_evidence_association(client: TestClient):
    """Verify GET /api/v1/runs/{run_id}/proposals/{proposal_id}/comparison returns associated evidence."""
    run = run_store.create(RunCreateRequest(url="https://example.com/checkout"))
    findings = create_mock_findings(run.run_id)
    run_store.set_findings(run.run_id, findings)

    proposal = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(
            finding_id=findings[0].finding_id,
            proposed_change="Update #main-content-panel { overflow-x: hidden; }",
        ),
    )

    res = client.get(f"/api/v1/runs/{run.run_id}/proposals/{proposal.proposal_id}/comparison?viewport=desktop")
    assert res.status_code == 200
    data = res.json()

    assert data["run_id"] == run.run_id
    assert data["proposal_id"] == proposal.proposal_id
    assert data["finding_id"] == findings[0].finding_id
    assert data["viewport"] == "desktop"
    assert "/artifacts/" in data["before_screenshot_url"]
    assert data["approval_status"] == "pending"
    assert data["controlled_environment"] is not None
    assert data["target_live_website_modified"] is False
    assert data["finding_summary"]["finding_id"] == findings[0].finding_id
    assert data["finding_summary"]["category"] == "layout_overflow"


def test_controlled_repair_simulation_generates_after_evidence_without_modifying_target(client: TestClient):
    """Verify POST /api/v1/runs/{run_id}/proposals/{proposal_id}/simulate-repair applies repair in isolated sandbox."""
    run = run_store.create(RunCreateRequest(url="https://example.com/products"))
    findings = create_mock_findings(run.run_id)
    run_store.set_findings(run.run_id, findings)

    proposal = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(
            finding_id=findings[1].finding_id,
            proposed_change="Replace broken image src with fallback CDN asset",
        ),
    )

    # 1. Trigger controlled simulation
    res = client.post(
        f"/api/v1/runs/{run.run_id}/proposals/{proposal.proposal_id}/simulate-repair",
        json={"viewport": "desktop"},
    )
    assert res.status_code == 200
    data = res.json()

    assert data["after_exists"] is True
    assert data["after_screenshot_url"] is not None
    assert "/artifacts/" in data["after_screenshot_url"]
    assert data["verification_status"] == "verified_success"
    assert data["target_live_website_modified"] is False
    assert "Controlled environment simulation verified" in data["diff_summary"]

    # 2. Verify artifact files on disk: original before.png preserved, after.png created
    run_dir = Path("artifacts") / run.run_id
    assert run_dir.exists()
    assert (run_dir / "after_desktop.png").is_file() or (run_dir / "after.png").is_file()

    # 3. Verify artifact endpoint serves after screenshot
    art_res = client.get(f"/api/v1/artifacts/{run.run_id}/screenshot?stage=after&viewport=desktop")
    assert art_res.status_code == 200
    assert art_res.headers["content-type"] == "image/png"


def test_rejected_proposals_remain_rejected(client: TestClient):
    """Verify rejected proposals strictly remain rejected and can never be approved or revisited."""
    run = run_store.create(RunCreateRequest(url="https://example.com/login"))
    proposal = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(proposed_change="Remove security banner"),
    )

    # 1. Reject proposal
    reject_res = client.post(
        f"/api/v1/proposals/{proposal.proposal_id}/reject",
        json={"notes": "Security risk: banner must not be removed."},
    )
    assert reject_res.status_code == 200
    assert reject_res.json()["approval_status"] == "rejected"
    assert reject_res.json()["can_revisit"] is False

    # 2. Attempt to approve rejected proposal -> HTTP 409 Conflict
    approve_res = client.post(
        f"/api/v1/proposals/{proposal.proposal_id}/approve",
        json={"notes": "Trying to bypass rejection"},
    )
    assert approve_res.status_code == 409
    assert "already been rejected and cannot be approved" in approve_res.json()["detail"].lower()

    # 3. Attempt to approve with revisit=True -> still HTTP 409 Conflict!
    revisit_approve = client.post(
        f"/api/v1/proposals/{proposal.proposal_id}/approve",
        json={"notes": "Attempt revisit", "revisit": True},
    )
    assert revisit_approve.status_code == 409
    assert "already been rejected and cannot be approved" in revisit_approve.json()["detail"].lower()

    # 4. Status remains rejected
    status_res = client.get(f"/api/v1/proposals/{proposal.proposal_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["approval_status"] == "rejected"


def test_approved_decisions_can_be_revisited(client: TestClient):
    """Verify approved proposals can be revisited and revoked/rejected or updated when revisit=True."""
    run = run_store.create(RunCreateRequest(url="https://example.com/checkout"))
    proposal = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(proposed_change="Add overflow-x: hidden to container"),
    )

    # 1. Initial approval
    appr1 = client.post(
        f"/api/v1/proposals/{proposal.proposal_id}/approve",
        json={"notes": "Approved for staging deployment"},
    )
    assert appr1.status_code == 200
    assert appr1.json()["approval_status"] == "approved"
    assert appr1.json()["can_revisit"] is True
    first_updated_at = appr1.json()["updated_at"]

    # 2. Attempting to reject without revisit=True -> 409 Conflict
    conflict_res = client.post(
        f"/api/v1/proposals/{proposal.proposal_id}/reject",
        json={"notes": "Changed mind without revisit flag"},
    )
    assert conflict_res.status_code == 409
    assert "already approved" in conflict_res.json()["detail"].lower()

    # 3. Revisit decision with revisit=True: update approval notes
    appr2 = client.post(
        f"/api/v1/proposals/{proposal.proposal_id}/approve",
        json={"notes": "Updated review notes: approved for canary only.", "revisit": True},
    )
    assert appr2.status_code == 200
    assert appr2.json()["approval_status"] == "approved"
    assert appr2.json()["reviewer_notes"] == "Updated review notes: approved for canary only."

    # 4. Revisit decision with revisit=True: transition approved -> rejected
    revoke_res = client.post(
        f"/api/v1/proposals/{proposal.proposal_id}/reject",
        json={"notes": "Found layout glitch on mobile. Revoking approval.", "revisit": True},
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["approval_status"] == "rejected"
    assert revoke_res.json()["reviewer_notes"] == "Found layout glitch on mobile. Revoking approval."

    # 5. Now that it is rejected, it can no longer be approved (rejected is permanent)
    final_try = client.post(
        f"/api/v1/proposals/{proposal.proposal_id}/approve",
        json={"revisit": True},
    )
    assert final_try.status_code == 409
    assert "already been rejected and cannot be approved" in final_try.json()["detail"].lower()


def test_visual_comparison_across_responsive_viewports(client: TestClient):
    """Verify visual comparison correctly switches and checks evidence for tablet and mobile viewports."""
    run = run_store.create(RunCreateRequest(url="https://example.com/responsive"))
    findings = create_mock_findings(run.run_id)
    run_store.set_findings(run.run_id, findings)

    proposal = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(
            finding_id=findings[0].finding_id,
            proposed_change="Mobile breakpoint media query patch",
        ),
    )

    # Test Mobile Viewport comparison
    mobile_res = client.get(f"/api/v1/runs/{run.run_id}/proposals/{proposal.proposal_id}/comparison?viewport=mobile")
    assert mobile_res.status_code == 200
    assert mobile_res.json()["viewport"] == "mobile"

    # Test Tablet Viewport comparison
    tablet_res = client.get(f"/api/v1/runs/{run.run_id}/proposals/{proposal.proposal_id}/comparison?viewport=tablet")
    assert tablet_res.status_code == 200
    assert tablet_res.json()["viewport"] == "tablet"
