"""Automated tests for OmniSight POST /api/v1/runs endpoint."""

import asyncio
import json
import pytest
from pydantic import ValidationError

from backend.app.api.runs import create_run
from backend.app.main import app
from backend.app.schemas.runs import RunCreateRequest, RunResponse
from backend.app.services.run_store import run_store


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


def test_runs_route_registered_in_openapi():
    """Verify POST /api/v1/runs is registered and documented in the OpenAPI schema."""
    paths = app.openapi().get("paths", {})
    assert "/api/v1/runs" in paths, "Expected /api/v1/runs in OpenAPI paths"
    assert "post" in paths["/api/v1/runs"], "Expected POST method for /api/v1/runs"


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
