"""Automated tests for OmniSight runs endpoints (POST and GET /api/v1/runs)."""

import asyncio
import json
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.app.api.runs import create_run, get_run, get_run_findings
from backend.app.main import app
from backend.app.schemas.findings import FindingResponse
from backend.app.schemas.runs import RunCreateRequest, RunResponse
from backend.app.services.run_store import create_mock_findings, run_store


@pytest.fixture(autouse=True)
def clean_run_store():
    """Ensure run_store is clean before and after each test."""
    run_store.clear()
    yield
    run_store.clear()


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
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
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


def test_runs_route_registered_in_openapi():
    """Verify runs routes are registered in OpenAPI schema."""
    paths = app.openapi().get("paths", {})
    assert "/api/v1/runs" in paths, "Expected /api/v1/runs in OpenAPI paths"
    assert "post" in paths["/api/v1/runs"], "Expected POST method for /api/v1/runs"
    assert "/api/v1/runs/{run_id}" in paths, "Expected /api/v1/runs/{run_id} in OpenAPI paths"
    assert "get" in paths["/api/v1/runs/{run_id}"], "Expected GET method for /api/v1/runs/{run_id}"
    assert "/api/v1/runs/{run_id}/findings" in paths, "Expected /api/v1/runs/{run_id}/findings in OpenAPI paths"
    assert "get" in paths["/api/v1/runs/{run_id}/findings"], "Expected GET method for findings"



def test_create_run_valid_unit():
    """Unit test: create_run with valid payload creates run in 'queued' status."""
    request = RunCreateRequest(url="http://127.0.0.1:8000/")
    response = create_run(request)

    assert isinstance(response, RunResponse)
    assert response.run_id.startswith("run_")
    assert response.url == "http://127.0.0.1:8000/"
    assert response.status == "queued"
    assert response.created_at is not None

    # Verify run is stored in the temporary repository
    stored = run_store.get(response.run_id)
    assert stored is not None
    assert stored.run_id == response.run_id


def test_create_run_valid_asgi():
    """Integration test: ASGI POST /api/v1/runs returns 201 and initial queued run."""
    status_code, data = asyncio.run(
        dispatch_asgi_post("/api/v1/runs", {"url": "http://127.0.0.1:8000/"})
    )

    assert status_code == 201
    assert "run_id" in data
    assert data["run_id"].startswith("run_")
    assert data["url"] == "http://127.0.0.1:8000/"
    assert data["status"] == "queued"
    assert "created_at" in data
    assert data["message"] == "Run created successfully and queued for inspection."


def test_create_run_invalid_missing_url():
    """Integration test: POST /api/v1/runs without URL returns 422 Unprocessable Entity."""
    status_code, data = asyncio.run(dispatch_asgi_post("/api/v1/runs", {}))

    assert status_code == 422
    assert "detail" in data
    errors = data["detail"]
    assert any(err.get("loc") == ["body", "url"] for err in errors)


def test_create_run_invalid_malformed_url():
    """Integration test: POST /api/v1/runs with malformed URL returns 422."""
    status_code, data = asyncio.run(
        dispatch_asgi_post("/api/v1/runs", {"url": "not-a-valid-http-url"})
    )

    assert status_code == 422
    assert "detail" in data
    errors = data["detail"]
    assert any("url" in str(err.get("loc")) for err in errors)


def test_create_run_generates_unique_run_ids():
    """Verify that multiple run creations produce distinct unique run_ids."""
    req1 = RunCreateRequest(url="http://127.0.0.1:8000/")
    req2 = RunCreateRequest(url="http://127.0.0.1:8000/")

    res1 = create_run(req1)
    res2 = create_run(req2)

    assert res1.run_id != res2.run_id
    assert len(run_store.list_all()) == 2


def test_get_run_existing_unit():
    """Unit test: get_run retrieves status and metadata for an existing run."""
    created = create_run(RunCreateRequest(url="http://127.0.0.1:8000/"))

    retrieved = get_run(created.run_id)

    assert isinstance(retrieved, RunResponse)
    assert retrieved.run_id == created.run_id
    assert retrieved.url == "http://127.0.0.1:8000/"
    assert retrieved.status == "queued"
    assert retrieved.created_at == created.created_at
    assert retrieved.error is None


def test_get_run_existing_asgi():
    """Integration test: GET /api/v1/runs/{run_id} returns 200 and run metadata."""
    # First create a run
    post_code, post_data = asyncio.run(
        dispatch_asgi_post("/api/v1/runs", {"url": "http://127.0.0.1:8000/"})
    )
    assert post_code == 201
    run_id = post_data["run_id"]

    # Now retrieve it
    get_code, get_data = asyncio.run(dispatch_asgi_get(f"/api/v1/runs/{run_id}"))

    assert get_code == 200
    assert get_data["run_id"] == run_id
    assert get_data["url"] == "http://127.0.0.1:8000/"
    assert get_data["status"] == "queued"
    assert get_data["created_at"] == post_data["created_at"]
    assert get_data["error"] is None


def test_get_run_unknown_unit():
    """Unit test: get_run raises HTTPException 404 for unknown run_id."""
    with pytest.raises(HTTPException) as exc_info:
        get_run("run_unknown_999")

    assert exc_info.value.status_code == 404
    assert "run_unknown_999" in exc_info.value.detail


def test_get_run_unknown_asgi():
    """Integration test: GET /api/v1/runs/{run_id} returns 404 for unknown run_id."""
    status_code, data = asyncio.run(dispatch_asgi_get("/api/v1/runs/run_nonexistent_xyz"))

    assert status_code == 404
    assert "detail" in data
    assert "run_nonexistent_xyz" in data["detail"]


def test_get_run_findings_empty_unit():
    """Unit test: get_run_findings returns empty list when no defects are detected."""
    created = create_run(RunCreateRequest(url="http://127.0.0.1:8000/"))

    findings = get_run_findings(created.run_id)

    assert findings == []
    assert isinstance(findings, list)


def test_get_run_findings_empty_asgi():
    """Integration test: GET /api/v1/runs/{run_id}/findings returns 200 and empty list."""
    post_code, post_data = asyncio.run(
        dispatch_asgi_post("/api/v1/runs", {"url": "http://127.0.0.1:8000/"})
    )
    assert post_code == 201
    run_id = post_data["run_id"]

    get_code, data = asyncio.run(dispatch_asgi_get(f"/api/v1/runs/{run_id}/findings"))

    assert get_code == 200
    assert data == []
    assert isinstance(data, list)


def test_get_run_findings_with_mock_data_unit():
    """Unit test: get_run_findings returns structured findings with mock labels."""
    created = create_run(RunCreateRequest(url="http://127.0.0.1:8000/"))
    mock_findings = create_mock_findings(created.run_id)
    run_store.set_findings(created.run_id, mock_findings)

    findings = get_run_findings(created.run_id)

    assert len(findings) == 2
    assert findings[0].category == "layout_overflow"
    assert findings[0].severity == "medium"
    assert findings[0].confidence == 0.92
    assert findings[0].source == "mock"
    assert "[MOCK]" in findings[0].description
    assert findings[0].evidence.screenshot_path is not None

    assert findings[1].category == "broken_image"
    assert findings[1].severity == "high"
    assert findings[1].source == "mock"


def test_get_run_findings_with_mock_data_asgi():
    """Integration test: GET /api/v1/runs/{run_id}/findings returns 200 and findings list."""
    post_code, post_data = asyncio.run(
        dispatch_asgi_post("/api/v1/runs", {"url": "http://127.0.0.1:8000/"})
    )
    assert post_code == 201
    run_id = post_data["run_id"]

    # Attach mock findings for early milestone testing
    mock_findings = create_mock_findings(run_id)
    run_store.set_findings(run_id, mock_findings)

    get_code, data = asyncio.run(dispatch_asgi_get(f"/api/v1/runs/{run_id}/findings"))

    assert get_code == 200
    assert len(data) == 2
    assert all(item["source"] == "mock" for item in data)
    assert data[0]["category"] == "layout_overflow"
    assert data[1]["category"] == "broken_image"


def test_get_run_findings_include_mock_query_param():
    """Verify that include_mock=True returns mock findings for development testing."""
    created = create_run(RunCreateRequest(url="http://127.0.0.1:8000/"))
    findings = get_run_findings(created.run_id, include_mock=True)
    assert len(findings) == 2
    assert all(item.source == "mock" for item in findings)
    assert all("[MOCK]" in item.description for item in findings)


def test_get_run_findings_unknown_run_unit():
    """Unit test: get_run_findings raises HTTPException 404 for unknown run_id."""
    with pytest.raises(HTTPException) as exc_info:
        get_run_findings("run_missing_999")

    assert exc_info.value.status_code == 404
    assert "run_missing_999" in exc_info.value.detail


def test_get_run_findings_unknown_run_asgi():
    """Integration test: GET /api/v1/runs/{run_id}/findings returns 404 for unknown run."""
    status_code, data = asyncio.run(
        dispatch_asgi_get("/api/v1/runs/run_unknown_findings_xyz/findings")
    )

    assert status_code == 404
    assert "detail" in data
    assert "run_unknown_findings_xyz" in data["detail"]


def test_create_run_url_strips_whitespace():
    """Verify that leading and trailing whitespace on URLs is cleanly stripped."""
    req = RunCreateRequest(url="   http://127.0.0.1:8000/   ")
    res = create_run(req)

    assert res.url == "http://127.0.0.1:8000/"


def test_create_run_unsupported_scheme():
    """Verify that unsupported URL schemes (like ftp://) are rejected with 422."""
    status_code, data = asyncio.run(
        dispatch_asgi_post("/api/v1/runs", {"url": "ftp://ftp.example.com/demo"})
    )

    assert status_code == 422
    assert "detail" in data
    assert any("url" in str(err.get("loc")) for err in data["detail"])


def test_create_run_oversized_url():
    """Verify that URLs exceeding 2048 characters are rejected with 422."""
    long_path = "a" * 2100
    status_code, data = asyncio.run(
        dispatch_asgi_post("/api/v1/runs", {"url": f"http://127.0.0.1:8000/{long_path}"})
    )

    assert status_code == 422
    assert "detail" in data


def test_get_run_whitespace_id_returns_400():
    """Verify that whitespace-only run_id returns 400 Bad Request."""
    status_code, data = asyncio.run(dispatch_asgi_get("/api/v1/runs/%20%20%20"))

    assert status_code == 400
    assert "detail" in data
    assert "must not be empty or whitespace" in data["detail"]


def test_get_run_findings_whitespace_id_returns_400():
    """Verify that whitespace-only run_id returns 400 Bad Request on findings endpoint."""
    status_code, data = asyncio.run(dispatch_asgi_get("/api/v1/runs/%20%20%20/findings"))

    assert status_code == 400
    assert "detail" in data
    assert "must not be empty or whitespace" in data["detail"]


def test_consistent_run_ids_and_lifecycle_status_values():
    """Verify consistent run ID formatting and valid lifecycle status values."""
    allowed_statuses = {
        "queued",
        "capturing",
        "analyzing",
        "repair_pending",
        "repairing",
        "verifying",
        "completed",
        "failed",
        "cancelled",
    }

    # 1. Create a run via POST
    post_code, post_data = asyncio.run(
        dispatch_asgi_post("/api/v1/runs", {"url": "http://127.0.0.1:8000/"})
    )
    assert post_code == 201
    created_id = post_data["run_id"]

    # Verify ID structure: must start with 'run_' and have non-empty alphanumeric suffix
    assert created_id.startswith("run_")
    assert len(created_id) > 4

    # Verify status is valid and initially 'queued'
    assert post_data["status"] in allowed_statuses
    assert post_data["status"] == "queued"

    # 2. Retrieve the run via GET and verify exact run_id and status consistency
    get_code, get_data = asyncio.run(dispatch_asgi_get(f"/api/v1/runs/{created_id}"))
    assert get_code == 200
    assert get_data["run_id"] == created_id
    assert get_data["status"] == post_data["status"]

    # 3. Attach findings and verify evidence paths preserve the consistent run_id
    mock_findings = create_mock_findings(created_id)
    run_store.set_findings(created_id, mock_findings)

    findings_code, findings_data = asyncio.run(
        dispatch_asgi_get(f"/api/v1/runs/{created_id}/findings")
    )
    assert findings_code == 200
    for finding in findings_data:
        assert created_id in finding["finding_id"]
        if finding["evidence"]["screenshot_path"]:
            assert created_id in finding["evidence"]["screenshot_path"]




