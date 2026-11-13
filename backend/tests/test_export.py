"""Unit and integration tests for OmniSight Inspection History Export (CSV & PDF)."""

import os
import pytest

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.schemas.runs import RunCreateRequest, RunResponse
from backend.app.schemas.findings import FindingResponse, EvidenceReferences
from backend.app.schemas.proposals import RepairProposalResponse
from backend.app.services.run_store import run_store
from backend.app.services.export_service import (
    sanitize_url_credentials,
    sanitize_secrets,
    compute_severity_counts,
    calculate_run_duration_seconds,
    generate_history_csv,
    generate_run_csv,
    generate_run_pdf,
    generate_history_pdf,
)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Ensure clean test isolation before and after each test."""
    run_store.clear()
    yield
    run_store.clear()


@pytest.fixture
def client():
    """FastAPI test client instance."""
    return TestClient(app)


# =============================================================================
# Unit Tests: Sanitization & Helpers
# =============================================================================


def test_sanitize_url_credentials_masks_userinfo_and_tokens():
    raw_url = "https://admin:superSecret123@internal.corp.com:8443/app?token=tok_secret_999&api_key=sk_live_12345&view=table"
    sanitized = sanitize_url_credentials(raw_url)

    assert "superSecret123" not in sanitized
    assert "tok_secret_999" not in sanitized
    assert "sk_live_12345" not in sanitized
    assert "view=table" in sanitized
    assert "***:***@internal.corp.com:8443" in sanitized


def test_sanitize_secrets_masks_sensitive_patterns_in_text():
    err_text = "Database connection failed for postgresql://app_user:dbPass99@db.internal:5432/main with Bearer eyJhbGciOiJIUzI1NiJ9"
    sanitized = sanitize_secrets(err_text)

    assert "dbPass99" not in sanitized
    assert "eyJhbGciOiJIUzI1NiJ9" not in sanitized
    assert "Bearer ***" in sanitized
    assert "***:***@db.internal:5432/main" in sanitized


def test_calculate_run_duration_seconds():
    d1 = calculate_run_duration_seconds("2026-11-13T10:00:00Z", "2026-11-13T10:00:04.5Z")
    assert d1 == 4.5

    d_none = calculate_run_duration_seconds("2026-11-13T10:00:00Z", None)
    assert d_none is None


def test_compute_severity_counts():
    findings = [
        FindingResponse(
            finding_id="f1",
            category="layout_overflow",
            severity="critical",
            confidence=0.9,
            description="Crit",
        ),
        FindingResponse(
            finding_id="f2",
            category="broken_image",
            severity="high",
            confidence=0.8,
            description="High",
        ),
        FindingResponse(
            finding_id="f3",
            category="missing_visible_element",
            severity="medium",
            confidence=0.7,
            description="Med",
        ),
        FindingResponse(
            finding_id="f4",
            category="layout_overflow",
            severity="low",
            confidence=0.6,
            description="Low",
        ),
    ]
    counts = compute_severity_counts(findings)
    assert counts == {"total": 4, "critical": 1, "high": 1, "medium": 1, "low": 1}


# =============================================================================
# Unit Tests: CSV Generation
# =============================================================================


def test_generate_history_csv_empty():
    csv_text = generate_history_csv([])
    lines = csv_text.strip().split("\n")
    assert len(lines) == 1
    assert "Run ID" in lines[0]
    assert "Target URL" in lines[0]
    assert "Critical Findings" in lines[0]


def test_generate_history_csv_with_runs():
    run = RunResponse(
        run_id="run_hist_001",
        url="http://user:secret@example.com/test?token=sensitive_token",
        status="completed",
        created_at="2026-11-13T10:00:00Z",
        completed_at="2026-11-13T10:00:03Z",
        message="Completed successfully",
        viewports=["desktop", "mobile"],
    )
    findings = [
        FindingResponse(
            finding_id="f_001",
            category="layout_overflow",
            severity="high",
            confidence=0.95,
            description="Layout break",
        )
    ]
    csv_text = generate_history_csv([run], {"run_hist_001": findings})

    assert "run_hist_001" in csv_text
    assert "COMPLETED" in csv_text
    assert "desktop, mobile" in csv_text
    # Secret must be redacted in target URL
    assert "secret" not in csv_text
    assert "sensitive_token" not in csv_text


def test_generate_run_csv_with_findings_and_proposals():
    run = RunResponse(
        run_id="run_single_001",
        url="https://site.example.com/page",
        status="completed",
        created_at="2026-11-13T12:00:00Z",
        completed_at="2026-11-13T12:00:08Z",
        message="Finished",
        viewports=["desktop"],
    )
    finding = FindingResponse(
        finding_id="f_single_1",
        category="broken_image",
        severity="critical",
        confidence=0.92,
        description="Missing asset banner",
        selector="#hero-image",
        viewport="desktop",
        evidence=EvidenceReferences(
            screenshot_path="artifacts/run_single_001/before.png",
            dom_snapshot_path="artifacts/run_single_001/dom.html",
        ),
    )
    proposal = RepairProposalResponse(
        proposal_id="prop_single_1",
        run_id="run_single_001",
        finding_id="f_single_1",
        proposed_change="Update src attribute with fallback",
        approval_status="approved",
        reviewer_notes="Approved fallback image patch",
        created_at="2026-11-13T12:01:00Z",
    )

    csv_text = generate_run_csv(run, [finding], [proposal])
    assert "run_single_001" in csv_text
    assert "f_single_1" in csv_text
    assert "CRITICAL" in csv_text
    assert "hero-image" in csv_text
    assert "prop_single_1" in csv_text
    assert "APPROVED" in csv_text
    assert "Approved fallback image patch" in csv_text


def test_generate_run_csv_clean_run():
    run = RunResponse(
        run_id="run_clean_001",
        url="https://clean.example.com",
        status="completed",
        created_at="2026-11-13T12:00:00Z",
        completed_at="2026-11-13T12:00:02Z",
        message="No defects detected",
        viewports=["desktop"],
    )
    csv_text = generate_run_csv(run, [])
    assert "run_clean_001" in csv_text
    assert "No defects detected" in csv_text


# =============================================================================
# Unit Tests: PDF Generation
# =============================================================================


def test_generate_run_pdf_returns_valid_pdf_bytes():
    run = RunResponse(
        run_id="run_pdf_001",
        url="https://user:pass123@app.example.com/dash?apiKey=secret_key_88",
        status="completed",
        created_at="2026-11-13T09:00:00Z",
        completed_at="2026-11-13T09:00:06Z",
        message="Inspection finished cleanly.",
        viewports=["desktop", "tablet"],
    )
    finding = FindingResponse(
        finding_id="f_pdf_1",
        category="layout_overflow",
        severity="medium",
        confidence=0.88,
        description="Container padding causes scrollbar",
        selector=".container-fluid > div.row",
        viewport="tablet",
    )
    proposal = RepairProposalResponse(
        proposal_id="prop_pdf_1",
        run_id="run_pdf_001",
        finding_id="f_pdf_1",
        proposed_change="box-sizing: border-box; overflow: hidden;",
        approval_status="pending",
        reviewer_notes="Awaiting QA validation",
        created_at="2026-11-13T09:01:00Z",
    )

    pdf_bytes = generate_run_pdf(run, [finding], [proposal])
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-")
    assert len(pdf_bytes) > 1000
    # Credentials must never be leaked
    assert b"pass123" not in pdf_bytes
    assert b"secret_key_88" not in pdf_bytes


def test_generate_run_pdf_handles_failed_run():
    failed_run = RunResponse(
        run_id="run_failed_001",
        url="https://failed.example.com",
        status="failed",
        created_at="2026-11-13T09:00:00Z",
        completed_at="2026-11-13T09:00:02Z",
        message="Inspection failed due to timeout.",
        error="Browser connection timeout after 30000ms. token=secret_bearer_token",
        viewports=["desktop"],
    )
    pdf_bytes = generate_run_pdf(failed_run, [])
    assert pdf_bytes.startswith(b"%PDF-")
    assert b"secret_bearer_token" not in pdf_bytes


def test_generate_history_pdf_valid():
    empty_pdf = generate_history_pdf([])
    assert empty_pdf.startswith(b"%PDF-")

    run = RunResponse(
        run_id="run_h_001",
        url="https://example.com",
        status="completed",
        created_at="2026-11-13T10:00:00Z",
        completed_at="2026-11-13T10:00:05Z",
        message="Completed",
        viewports=["desktop"],
    )
    populated_pdf = generate_history_pdf([run], {})
    assert populated_pdf.startswith(b"%PDF-")


# =============================================================================
# Integration Tests: FastAPI Endpoints
# =============================================================================


def test_api_export_history_csv_endpoint(client):
    # Populate a test run in store
    req = RunCreateRequest(url="https://demo.example.com/test", viewports=["desktop"])
    created = run_store.create(req)

    res = client.get("/api/v1/runs/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert "attachment;" in res.headers.get("content-disposition", "")
    assert created.run_id in res.text


def test_api_export_history_pdf_endpoint(client):
    req = RunCreateRequest(url="https://demo.example.com/test", viewports=["desktop"])
    run_store.create(req)

    res = client.get("/api/v1/runs/export/pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers.get("content-type", "")
    assert res.content.startswith(b"%PDF-")


def test_api_export_run_csv_endpoint(client):
    req = RunCreateRequest(url="https://demo.example.com/run-csv", viewports=["desktop", "mobile"])
    created = run_store.create(req)

    # 404 for nonexistent run
    res_404 = client.get("/api/v1/runs/nonexistent_run_999/export/csv")
    assert res_404.status_code == 404

    # 200 for created run
    res = client.get(f"/api/v1/runs/{created.run_id}/export/csv")
    assert res.status_code == 200
    assert "text/csv" in res.headers.get("content-type", "")
    assert created.run_id in res.text
    assert f"omnisight_run_{created.run_id}.csv" in res.headers.get("content-disposition", "")


def test_api_export_run_pdf_endpoint(client):
    req = RunCreateRequest(url="https://demo.example.com/run-pdf", viewports=["desktop"])
    created = run_store.create(req)

    # 404 for nonexistent run
    res_404 = client.get("/api/v1/runs/nonexistent_run_999/export/pdf")
    assert res_404.status_code == 404

    # 200 for created run
    res = client.get(f"/api/v1/runs/{created.run_id}/export/pdf")
    assert res.status_code == 200
    assert "application/pdf" in res.headers.get("content-type", "")
    assert res.content.startswith(b"%PDF-")
    assert f"omnisight_report_{created.run_id}.pdf" in res.headers.get("content-disposition", "")
