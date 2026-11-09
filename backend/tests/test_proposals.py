"""Automated tests for OmniSight self-healing repair proposal APIs and review lifecycle."""

import asyncio
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.main import app
from backend.app.schemas.proposals import RepairProposalCreateRequest
from backend.app.schemas.runs import RunCreateRequest
from backend.app.services.run_store import DatabaseRunStore, create_mock_findings, run_store


async def dispatch_asgi_post(path: str, payload: dict | None = None) -> tuple[int, dict]:
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
    data = json.loads(b"".join(response_body).decode("utf-8"))
    return status_code, data


async def dispatch_asgi_get(path: str) -> tuple[int, dict]:
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
    data = json.loads(b"".join(response_body).decode("utf-8"))
    return status_code, data


# =============================================================================
# Proposal Creation Tests
# =============================================================================

def test_create_repair_proposal_success():
    """Verify POST /api/v1/runs/{run_id}/proposals creates proposal in 'pending' status."""
    run = run_store.create(RunCreateRequest(url="https://example.com/checkout"))
    findings = create_mock_findings(run.run_id)
    run_store.set_findings(run.run_id, findings)

    payload = {
        "finding_id": findings[0].finding_id,
        "proposed_change": "Add overflow-x: hidden to #checkout-panel",
        "github_pr_url": "https://github.com/prabath-ux05/OmniSight/pull/10",
        "github_pr_number": 10,
    }

    status_code, data = asyncio.run(
        dispatch_asgi_post(f"/api/v1/runs/{run.run_id}/proposals", payload)
    )

    assert status_code == 201
    assert data["proposal_id"].startswith("prop_")
    assert data["run_id"] == run.run_id
    assert data["finding_id"] == findings[0].finding_id
    assert data["approval_status"] == "pending"
    assert data["execution_status"] == "unapplied"
    assert data["verification_status"] == "unverified"
    assert data["github_pr_number"] == 10
    assert data["created_at"] is not None


def test_create_repair_proposal_unknown_run_returns_404():
    """Verify creating proposal for nonexistent run returns 404 Not Found."""
    status_code, data = asyncio.run(
        dispatch_asgi_post(
            "/api/v1/runs/run_unknown_xyz/proposals",
            {"proposed_change": "Fix CSS container"},
        )
    )
    assert status_code == 404
    assert "not found" in data["detail"].lower()


def test_create_repair_proposal_invalid_empty_change_returns_422():
    """Verify creating proposal with empty proposed_change returns 422 Unprocessable Entity."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    status_code, data = asyncio.run(
        dispatch_asgi_post(
            f"/api/v1/runs/{run.run_id}/proposals",
            {"proposed_change": ""},
        )
    )
    assert status_code == 422


# =============================================================================
# Proposal Retrieval Tests
# =============================================================================

def test_list_run_proposals_and_filter():
    """Verify GET /api/v1/runs/{run_id}/proposals lists and filters proposals."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    findings = create_mock_findings(run.run_id)
    run_store.set_findings(run.run_id, findings)

    run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(
            finding_id=findings[0].finding_id,
            proposed_change="Patch CSS layout",
        ),
    )
    run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(
            finding_id=findings[1].finding_id,
            proposed_change="Fix image src link",
        ),
    )

    # List all proposals for run
    status_code, data = asyncio.run(dispatch_asgi_get(f"/api/v1/runs/{run.run_id}/proposals"))
    assert status_code == 200
    assert len(data) == 2

    # Filter by finding_id
    filter_code, filter_data = asyncio.run(
        dispatch_asgi_get(f"/api/v1/runs/{run.run_id}/proposals?finding_id={findings[0].finding_id}")
    )
    assert filter_code == 200
    assert len(filter_data) == 1
    assert filter_data[0]["finding_id"] == findings[0].finding_id


def test_get_repair_proposal_by_id_success():
    """Verify GET /api/v1/proposals/{proposal_id} retrieves proposal."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    prop = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(proposed_change="Fix button contrast"),
    )

    status_code, data = asyncio.run(dispatch_asgi_get(f"/api/v1/proposals/{prop.proposal_id}"))
    assert status_code == 200
    assert data["proposal_id"] == prop.proposal_id
    assert data["proposed_change"] == "Fix button contrast"


def test_get_repair_proposal_by_id_unknown_returns_404():
    """Verify retrieving unknown proposal returns 404."""
    status_code, data = asyncio.run(dispatch_asgi_get("/api/v1/proposals/prop_nonexistent_xyz"))
    assert status_code == 404
    assert "not found" in data["detail"].lower()


# =============================================================================
# Proposal Approval & Rejection Lifecycle Tests
# =============================================================================

def test_approve_repair_proposal_success():
    """Verify POST /api/v1/proposals/{proposal_id}/approve transitions status to approved."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    prop = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(proposed_change="Fix contrast"),
    )
    assert prop.approval_status == "pending"

    status_code, data = asyncio.run(
        dispatch_asgi_post(
            f"/api/v1/proposals/{prop.proposal_id}/approve",
            {"notes": "Approved for staging deployment"},
        )
    )

    assert status_code == 200
    assert data["proposal_id"] == prop.proposal_id
    assert data["approval_status"] == "approved"
    assert data["execution_status"] == "unapplied"  # Approval does not mean applied!
    assert data["updated_at"] is not None


def test_reject_repair_proposal_success():
    """Verify POST /api/v1/proposals/{proposal_id}/reject transitions status to rejected."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    prop = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(proposed_change="Remove navigation bar"),
    )

    status_code, data = asyncio.run(
        dispatch_asgi_post(
            f"/api/v1/proposals/{prop.proposal_id}/reject",
            {"notes": "Rejected: would break site navigation"},
        )
    )

    assert status_code == 200
    assert data["proposal_id"] == prop.proposal_id
    assert data["approval_status"] == "rejected"
    assert data["updated_at"] is not None


def test_duplicate_and_conflicting_approval_decisions_raise_409():
    """Verify attempting to re-decide an already approved or rejected proposal raises HTTP 409 Conflict."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    prop = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(proposed_change="Update button padding"),
    )

    # 1. First approve succeeds
    code1, _ = asyncio.run(dispatch_asgi_post(f"/api/v1/proposals/{prop.proposal_id}/approve"))
    assert code1 == 200

    # 2. Duplicate approve -> 409 Conflict
    code2, data2 = asyncio.run(dispatch_asgi_post(f"/api/v1/proposals/{prop.proposal_id}/approve"))
    assert code2 == 409
    assert "already approved" in data2["detail"].lower()

    # 3. Rejecting an approved proposal -> 409 Conflict
    code3, data3 = asyncio.run(dispatch_asgi_post(f"/api/v1/proposals/{prop.proposal_id}/reject"))
    assert code3 == 409
    assert "already approved and cannot be rejected" in data3["detail"].lower()


def test_proposal_status_summary_endpoint():
    """Verify GET /api/v1/proposals/{proposal_id}/status returns summary."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    prop = run_store.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(proposed_change="Fix flex layout"),
    )

    status_code, data = asyncio.run(dispatch_asgi_get(f"/api/v1/proposals/{prop.proposal_id}/status"))
    assert status_code == 200
    assert data["proposal_id"] == prop.proposal_id
    assert data["approval_status"] == "pending"
    assert data["execution_status"] == "unapplied"
    assert data["verification_status"] == "unverified"


def test_proposal_persistence_across_simulated_backend_restart(tmp_path):
    """Verify repair proposals remain persisted in database across server restarts."""
    db_file = tmp_path / "restart_proposal_test.db"
    restart_db_url = f"sqlite:///{db_file}"

    restart_engine = create_engine(restart_db_url, connect_args={"check_same_thread": False})
    from backend.app.db.base import Base
    Base.metadata.create_all(bind=restart_engine)

    Session1 = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=restart_engine)
    store1 = DatabaseRunStore(session_factory=Session1)

    # 1. Create run and proposal before shutdown
    run = store1.create(RunCreateRequest(url="https://example.com/persisted"))
    prop = store1.create_proposal(
        run.run_id,
        RepairProposalCreateRequest(proposed_change="Update container margin"),
    )
    store1.update_proposal_approval(prop.proposal_id, "approved")

    # 2. Simulate complete server shutdown & restart
    restart_engine.dispose()

    reopened_engine = create_engine(restart_db_url, connect_args={"check_same_thread": False})
    Session2 = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=reopened_engine)
    store2 = DatabaseRunStore(session_factory=Session2)

    # 3. Verify proposal still exists and preserved 'approved' status
    reopened_prop = store2.get_proposal(prop.proposal_id)
    assert reopened_prop is not None
    assert reopened_prop.proposal_id == prop.proposal_id
    assert reopened_prop.approval_status == "approved"
    assert reopened_prop.proposed_change == "Update container margin"

    reopened_engine.dispose()
