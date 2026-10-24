"""Automated test suite for OmniSight Backend health check endpoint."""

import asyncio
import json
import pytest

from backend.app.api.health import get_health
from backend.app.main import app
from backend.app.schemas.health import HealthResponse


def test_health_route_is_registered_on_app():
    """Verify that GET /health route is properly exposed in OpenAPI specification."""
    openapi_schema = app.openapi()
    paths = openapi_schema.get("paths", {})
    assert "/health" in paths, "Expected /health endpoint to be present in OpenAPI schema."
    assert "get" in paths["health" if "health" in paths else "/health"], "Expected /health to support HTTP GET."


def test_health_endpoint_unit():
    """Unit test: get_health returns expected HealthResponse model."""
    response = get_health()

    assert isinstance(response, HealthResponse)
    assert response.status == "ok"
    assert response.app == "OmniSight Backend"
    assert response.version == "0.1.0"

    dumped = response.model_dump()
    assert dumped == {
        "status": "ok",
        "app": "OmniSight Backend",
        "version": "0.1.0",
    }
    # Verify no unverified module claims
    assert "browser_agent" not in dumped
    assert "vision_engine" not in dumped


def test_health_endpoint_asgi_dispatch():
    """Integration test: dispatch a raw ASGI GET /health request through the app."""
    async def run_asgi_request():
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "raw_path": b"/health",
            "query_string": b"",
            "headers": [(b"accept", b"application/json")],
        }
        body_chunks = []
        status_code = None

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                body_chunks.append(message.get("body", b""))

        await app(scope, receive, send)
        body = json.loads(b"".join(body_chunks).decode("utf-8"))
        return status_code, body

    status_code, body = asyncio.run(run_asgi_request())

    assert status_code == 200
    assert body["status"] == "ok"
    assert body["app"] == "OmniSight Backend"
    assert body["version"] == "0.1.0"
