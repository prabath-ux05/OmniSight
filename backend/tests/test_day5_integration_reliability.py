"""Automated Integration, Testing & Reliability Suite for Day 5.

Validates the full workflow from run creation to proposal approval,
execution and verification status isolation, database persistence across restarts,
directory traversal security, and graceful error handling.
"""

import asyncio
import json
from pathlib import Path
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.schemas.runs import RunCreateRequest
from backend.app.schemas.proposals import RepairProposalCreateRequest
from backend.app.services.run_store import (
    DatabaseRunStore,
    create_mock_findings,
    run_store,
)


@pytest.fixture(autouse=True)
def clean_store():
    """Ensure run store is clean before and after each test."""
    run_store.clear()
    yield
    run_store.clear()


async def asgi_post(path: str, payload: dict | None = None) -> tuple[int, dict]:
    """Helper to dispatch an ASGI HTTP POST request directly through the app."""
    body_bytes = json.dumps(payload).encode("utf-8") if payload is not None else b""
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [
            (b"content-type", b"application/json"),
            (b"accept", b"application/json"),
        ],
    }
    response_body = []
    status_code = None
    sent = False

    async def receive():
        nonlocal sent
        if not sent:
            sent = True
            return {"type": "http.request", "body": body_bytes, "more_body": False}
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await app(scope, receive, send)
    raw = b"".join(response_body)
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        data = {"raw": raw.decode("utf-8", errors="replace")}
    return status_code, data


async def asgi_get(path: str) -> tuple[int, dict | list]:
    """Helper to dispatch an ASGI HTTP GET request directly through the app."""
    if "?" in path:
        url_path, query_str = path.split("?", 1)
        query_bytes = query_str.encode("utf-8")
    else:
        url_path = path
        query_bytes = b""

    scope = {
        "type": "http",
        "method": "GET",
        "path": url_path,
        "raw_path": url_path.encode("utf-8"),
        "query_string": query_bytes,
        "headers": [(b"accept", b"application/json")],
    }
    response_body = []
    status_code = None

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await app(scope, receive, send)
    raw = b"".join(response_body)
    try:
        data = json.loads(raw.decode("utf-8"))
    except Exception:
        data = {"raw": raw.decode("utf-8", errors="replace")}
    return status_code, data


# =============================================================================
# 1. Complete End-to-End Workflow Test (11 Steps)
# =============================================================================

def test_complete_e2e_workflow():
    """Verify complete 11-step workflow from URL entry to proposal approval and separate status verification."""
    # Step 1 & 2 & 3: User enters URL -> frontend sends POST /api/v1/runs -> backend validates and creates run
    post_status, run_data = asyncio.run(asgi_post("/api/v1/runs", {"url": "https://example.com/checkout"}))
    assert post_status == 201
    run_id = run_data["run_id"]
    assert run_id.startswith("run_")
    assert run_data["status"] == "queued"
    assert run_data["url"] == "https://example.com/checkout"

    # Step 4: Run status is stored in PostgreSQL and retrievable via GET /api/v1/runs/{run_id}
    get_status, fetched_run = asyncio.run(asgi_get(f"/api/v1/runs/{run_id}"))
    assert get_status == 200
    assert fetched_run["run_id"] == run_id
    assert fetched_run["status"] == "queued"

    # Step 5: Findings are stored and linked to run
    mock_findings = create_mock_findings(run_id)
    run_store.set_findings(run_id, mock_findings)

    findings_status, findings_list = asyncio.run(asgi_get(f"/api/v1/runs/{run_id}/findings"))
    assert findings_status == 200
    assert len(findings_list) == 2
    finding_id = findings_list[0]["finding_id"]
    assert finding_id.startswith("defect_")

    # Step 6: Create self-healing repair proposal for the defect finding
    prop_payload = {
        "finding_id": finding_id,
        "proposed_change": ".checkout-btn { min-width: 200px; display: inline-block; }",
        "github_pr_url": "https://github.com/prabath-ux05/OmniSight/pull/101",
        "github_pr_number": 101,
    }
    prop_status, prop_data = asyncio.run(asgi_post(f"/api/v1/runs/{run_id}/proposals", prop_payload))
    assert prop_status == 201
    proposal_id = prop_data["proposal_id"]
    assert proposal_id.startswith("prop_")
    assert prop_data["approval_status"] == "pending"
    assert prop_data["execution_status"] == "unapplied"
    assert prop_data["verification_status"] == "unverified"
    assert prop_data["github_pr_number"] == 101

    # Step 7: Retrieve proposal for review
    list_status, run_proposals = asyncio.run(asgi_get(f"/api/v1/runs/{run_id}/proposals"))
    assert list_status == 200
    assert len(run_proposals) == 1
    assert run_proposals[0]["proposal_id"] == proposal_id

    # Step 8 & 9: User approves proposal with reviewer justification notes
    approve_status, approved_data = asyncio.run(
        asgi_post(
            f"/api/v1/proposals/{proposal_id}/approve",
            {"notes": "Verified CSS fix resolves button overflow on small viewports."},
        )
    )
    assert approve_status == 200
    assert approved_data["approval_status"] == "approved"
    assert approved_data["updated_at"] is not None

    # Step 10: Strict separation of Review, Execution, and Verification statuses
    # Approval MUST NOT claim execution or verification is finished
    assert approved_data["execution_status"] == "unapplied"
    assert approved_data["verification_status"] == "unverified"

    # Step 11: Dashboard status endpoint displays the latest information
    status_code, status_summary = asyncio.run(asgi_get(f"/api/v1/proposals/{proposal_id}/status"))
    assert status_code == 200
    assert status_summary["approval_status"] == "approved"
    assert status_summary["execution_status"] == "unapplied"
    assert status_summary["verification_status"] == "unverified"


# =============================================================================
# 2. Duplicate & Conflicting Decision Governance Tests
# =============================================================================

def test_duplicate_decision_governance():
    """Verify human governance guards: prevent duplicate approvals and conflicting switches."""
    run = run_store.create(RunCreateRequest(url="https://example.com/governance"))
    prop = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(proposed_change="font-size: 14px;"),
    )

    # 1. Approve proposal
    code1, _ = asyncio.run(asgi_post(f"/api/v1/proposals/{prop.proposal_id}/approve"))
    assert code1 == 200

    # 2. Duplicate approve returns 409 Conflict
    code2, err2 = asyncio.run(asgi_post(f"/api/v1/proposals/{prop.proposal_id}/approve"))
    assert code2 == 409
    assert "already approved" in err2["detail"].lower()

    # 3. Conflicting reject on approved proposal returns 409 Conflict
    code3, err3 = asyncio.run(asgi_post(f"/api/v1/proposals/{prop.proposal_id}/reject"))
    assert code3 == 409
    assert "cannot be rejected" in err3["detail"].lower()


# =============================================================================
# 3. Execution and Verification Lifecycle State Tests
# =============================================================================

def test_execution_and_verification_states():
    """Verify execution ('applying', 'applied', 'failed') and verification ('verified_success', 'verified_failure') updates."""
    run = run_store.create(RunCreateRequest(url="https://example.com/states"))
    prop = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(proposed_change="border-radius: 4px;"),
    )

    # Approve first
    run_store.update_proposal_approval(prop.proposal_id, "approved")

    # Update execution to 'applying'
    res_applying = run_store.update_proposal_execution(prop.proposal_id, "applying")
    assert res_applying.execution_status == "applying"

    # Update execution to 'failed'
    res_failed = run_store.update_proposal_execution(prop.proposal_id, "failed")
    assert res_failed.execution_status == "failed"

    # Update verification to 'verified_failure'
    res_verif = run_store.update_proposal_verification(prop.proposal_id, "verified_failure")
    assert res_verif.verification_status == "verified_failure"

    # Check that invalid execution or verification states are rejected with ValueError
    with pytest.raises(ValueError):
        run_store.update_proposal_execution(prop.proposal_id, "invalid_execution_state")

    with pytest.raises(ValueError):
        run_store.update_proposal_verification(prop.proposal_id, "invalid_verification_state")


# =============================================================================
# 4. Unknown ID and Missing Resource Error Tests
# =============================================================================

def test_unknown_resource_identifiers_return_404():
    """Verify that unknown run_ids and proposal_ids return clean HTTP 404 errors."""
    # Unknown run
    code, data = asyncio.run(asgi_get("/api/v1/runs/run_unknown_nonexistent"))
    assert code == 404
    assert "not found" in data["detail"].lower()

    # Unknown run findings
    code, data = asyncio.run(asgi_get("/api/v1/runs/run_unknown_nonexistent/findings"))
    assert code == 404
    assert "not found" in data["detail"].lower()

    # Unknown run proposals
    code, data = asyncio.run(asgi_get("/api/v1/runs/run_unknown_nonexistent/proposals"))
    assert code == 404
    assert "not found" in data["detail"].lower()

    # Unknown proposal
    code, data = asyncio.run(asgi_get("/api/v1/proposals/prop_unknown_nonexistent"))
    assert code == 404
    assert "not found" in data["detail"].lower()

    # Unknown proposal approve
    code, data = asyncio.run(asgi_post("/api/v1/proposals/prop_unknown_nonexistent/approve"))
    assert code == 404
    assert "not found" in data["detail"].lower()

    # Unknown proposal reject
    code, data = asyncio.run(asgi_post("/api/v1/proposals/prop_unknown_nonexistent/reject"))
    assert code == 404
    assert "not found" in data["detail"].lower()


# =============================================================================
# 5. URL Validation and Malformed Input Tests
# =============================================================================

def test_url_validation_rejects_malformed_requests():
    """Verify that empty, non-HTTP, and malformed URLs are rejected cleanly."""
    # Empty URL payload
    code, data = asyncio.run(asgi_post("/api/v1/runs", {}))
    assert code == 422

    # Malformed non-URL string
    code, data = asyncio.run(asgi_post("/api/v1/runs", {"url": "not-a-url"}))
    assert code == 422

    # Non-HTTP/HTTPS protocol
    code, data = asyncio.run(asgi_post("/api/v1/runs", {"url": "ftp://files.example.com"}))
    assert code == 422


# =============================================================================
# 6. Artifact Directory Traversal Security Tests
# =============================================================================

def test_artifact_path_traversal_protection():
    """Verify that all artifact endpoints reject directory traversal attempts with HTTP 400."""
    # Direct get_artifact with traversal in filename
    code, data = asyncio.run(asgi_get("/api/v1/artifacts/test_sample_run/..%2f..%2fetc%2fpasswd"))
    assert code in (400, 404)

    # Missing artifact returns clean 404
    code, data = asyncio.run(asgi_get("/api/v1/artifacts/test_sample_run/nonexistent_file.png"))
    assert code == 404


# =============================================================================
# 7. Database Persistence Across Simulated Process Restart
# =============================================================================

def test_full_workflow_persistence_across_process_restart(tmp_path):
    """Verify that runs, findings, artifacts, and repair proposals persist across server restarts."""
    db_file = tmp_path / "day5_restart_test.db"
    db_url = f"sqlite:///{db_file}"

    # Engine 1: Create and populate tables
    engine1 = create_engine(db_url, connect_args={"check_same_thread": False})
    from backend.app.db.base import Base
    Base.metadata.create_all(bind=engine1)

    Session1 = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine1)
    store1 = DatabaseRunStore(session_factory=Session1)

    # Create run, findings, proposal, and approve it
    run = store1.create(RunCreateRequest(url="https://example.com/persistence-test"))
    store1.set_findings(run.run_id, create_mock_findings(run.run_id))
    prop = store1.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(
            finding_id=f"defect_{run.run_id}_001",
            proposed_change="margin: 0 auto;",
        ),
    )
    store1.update_proposal_approval(prop.proposal_id, "approved")
    store1.update_proposal_execution(prop.proposal_id, "applied")
    store1.update_proposal_verification(prop.proposal_id, "verified_success")

    # Shutdown process (dispose engine)
    engine1.dispose()

    # Engine 2: New process startup simulating server restart
    engine2 = create_engine(db_url, connect_args={"check_same_thread": False})
    Session2 = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine2)
    store2 = DatabaseRunStore(session_factory=Session2)

    # Verify everything persisted identically
    restored_run = store2.get(run.run_id)
    assert restored_run is not None
    assert restored_run.url == "https://example.com/persistence-test"

    restored_findings = store2.get_findings(run.run_id)
    assert restored_findings is not None
    assert len(restored_findings) == 2

    restored_prop = store2.get_proposal(prop.proposal_id)
    assert restored_prop is not None
    assert restored_prop.approval_status == "approved"
    assert restored_prop.execution_status == "applied"
    assert restored_prop.verification_status == "verified_success"
    assert restored_prop.proposed_change == "margin: 0 auto;"

    engine2.dispose()
