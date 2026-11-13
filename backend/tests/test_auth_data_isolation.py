"""Integration tests for OmniSight user data isolation and authorization enforcement.

Verifies:
- Authenticated users own their inspection runs.
- Users cannot access or modify another user's private runs, findings, artifacts, proposals, or exports (403 Forbidden).
- Unauthenticated callers cannot access private runs (401 Unauthorized).
- Guest runs remain accessible without authentication (preserving guest experience).
- User run lists are properly partitioned and never leak private runs across users or to guests.
"""

import asyncio
import json
import pytest
from backend.app.api.preview import stream_preview_events
from backend.app.db.session import SessionLocal
from backend.app.main import app
from backend.app.models.user import UserModel
from backend.app.schemas.auth import RegisterRequest
from backend.app.schemas.proposals import RepairProposalCreateRequest
from backend.app.schemas.runs import RunCreateRequest
from backend.app.services.auth_service import auth_service
from backend.app.services.preview_service import preview_service
from backend.app.services.run_store import run_store


async def dispatch_asgi_request(
    method: str,
    path: str,
    payload: dict | None = None,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> tuple[int, dict, dict]:
    """Helper to dispatch an ASGI HTTP request through the FastAPI app."""
    body_bytes = json.dumps(payload).encode("utf-8") if payload is not None else b""
    req_headers = [
        (b"accept", b"application/json"),
    ]
    if payload is not None:
        req_headers.append((b"content-type", b"application/json"))
    if headers:
        req_headers.extend(headers)

    query_bytes = b""
    if "?" in path:
        url_path, query_str = path.split("?", 1)
        query_bytes = query_str.encode("utf-8")
    else:
        url_path = path

    scope = {
        "type": "http",
        "method": method,
        "path": url_path,
        "raw_path": url_path.encode("utf-8"),
        "query_string": query_bytes,
        "headers": req_headers,
    }
    response_body = []
    response_headers = {}
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
            for k, v in message.get("headers", []):
                response_headers[k.decode("utf-8").lower()] = v.decode("utf-8")
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await app(scope, receive, send)
    joined_bytes = b"".join(response_body)
    try:
        raw_str = joined_bytes.decode("utf-8")
        data = json.loads(raw_str)
    except Exception:
        data = {"raw": joined_bytes}
    return status_code, data, response_headers


def create_test_user_and_session(email: str, full_name: str) -> tuple[UserModel, str]:
    """Helper to provision a user and active session in the test database."""
    db = SessionLocal()
    try:
        normalized_email = email.strip().lower()
        user = db.query(UserModel).filter(UserModel.email == normalized_email).first()
        if not user:
            user = auth_service.register_user(
                db=db,
                request=RegisterRequest(
                    email=email,
                    password="StrongPassword123!",
                    full_name=full_name,
                ),
            )
        session, raw_token = auth_service.create_session(
            db=db,
            user=user,
            user_agent="pytest-client",
            ip_address="127.0.0.1",
        )
        return user, raw_token
    finally:
        db.close()


def test_authenticated_user_creates_private_run():
    """Verify that a run created by an authenticated user has user_id set and is accessible by owner."""
    user_a, token_a = create_test_user_and_session("alice@example.com", "Alice Tester")
    headers_a = [(b"authorization", f"Bearer {token_a}".encode("utf-8"))]

    # Create run as User A
    status, data, _ = asyncio.run(
        dispatch_asgi_request(
            "POST",
            "/api/v1/runs",
            {"url": "https://alice.example.com", "viewports": ["desktop"]},
            headers=headers_a,
        )
    )
    assert status == 201
    run_id = data["run_id"]
    assert data["user_id"] == user_a.id

    # User A can retrieve their own run
    status_get, data_get, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_id}", headers=headers_a)
    )
    assert status_get == 200
    assert data_get["run_id"] == run_id
    assert data_get["user_id"] == user_a.id


def test_unauthenticated_user_cannot_access_private_run():
    """Verify that an unauthenticated caller receives 401 when trying to access a private run."""
    _, token_a = create_test_user_and_session("alice2@example.com", "Alice 2")
    headers_a = [(b"authorization", f"Bearer {token_a}".encode("utf-8"))]

    status, data, _ = asyncio.run(
        dispatch_asgi_request(
            "POST",
            "/api/v1/runs",
            {"url": "https://private.example.com"},
            headers=headers_a,
        )
    )
    assert status == 201
    run_id = data["run_id"]

    # Unauthenticated GET /runs/{run_id} -> 401
    status_unauth, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_id}")
    )
    assert status_unauth == 401

    # Unauthenticated GET /runs/{run_id}/findings -> 401
    status_find, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_id}/findings")
    )
    assert status_find == 401

    # Unauthenticated GET /runs/{run_id}/artifacts -> 401
    status_art, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_id}/artifacts")
    )
    assert status_art == 401


def test_cross_user_access_blocked_with_403_forbidden():
    """Verify that User B cannot access or modify User A's private run (403 Forbidden)."""
    _, token_a = create_test_user_and_session("alice3@example.com", "Alice 3")
    _, token_b = create_test_user_and_session("bob3@example.com", "Bob 3")

    headers_a = [(b"authorization", f"Bearer {token_a}".encode("utf-8"))]
    headers_b = [(b"authorization", f"Bearer {token_b}".encode("utf-8"))]

    # Alice creates run
    status, data, _ = asyncio.run(
        dispatch_asgi_request(
            "POST",
            "/api/v1/runs",
            {"url": "https://alice-secret.example.com"},
            headers=headers_a,
        )
    )
    assert status == 201
    run_id = data["run_id"]

    # Bob attempts GET /runs/{run_id} -> 403
    status_bob, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_id}", headers=headers_b)
    )
    assert status_bob == 403

    # Bob attempts GET /runs/{run_id}/findings -> 403
    status_bob_find, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_id}/findings", headers=headers_b)
    )
    assert status_bob_find == 403

    # Bob attempts to create a proposal on Alice's run -> 403
    status_bob_prop, _, _ = asyncio.run(
        dispatch_asgi_request(
            "POST",
            f"/api/v1/runs/{run_id}/proposals",
            {"finding_id": "find_1", "suggested_patch": "div { color: red; }"},
            headers=headers_b,
        )
    )
    assert status_bob_prop == 403


def test_guest_run_accessible_to_everyone():
    """Verify guest inspection (user_id=None) works without auth and is accessible to all."""
    # Create guest run without authorization header
    status, data, _ = asyncio.run(
        dispatch_asgi_request("POST", "/api/v1/runs", {"url": "https://guest.example.com"})
    )
    assert status == 201
    run_id = data["run_id"]
    assert data["user_id"] is None

    # Unauthenticated guest can access
    status_guest, data_guest, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_id}")
    )
    assert status_guest == 200
    assert data_guest["run_id"] == run_id

    # Authenticated user can also access guest run
    _, token_a = create_test_user_and_session("alice4@example.com", "Alice 4")
    headers_a = [(b"authorization", f"Bearer {token_a}".encode("utf-8"))]
    status_user, data_user, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_id}", headers=headers_a)
    )
    assert status_user == 200
    assert data_user["run_id"] == run_id


def test_list_runs_data_isolation():
    """Verify that listing runs does not leak private runs between users or to guests."""
    user_a, token_a = create_test_user_and_session("alice5@example.com", "Alice 5")
    user_b, token_b = create_test_user_and_session("bob5@example.com", "Bob 5")

    headers_a = [(b"authorization", f"Bearer {token_a}".encode("utf-8"))]
    headers_b = [(b"authorization", f"Bearer {token_b}".encode("utf-8"))]

    # Alice creates Run A
    s_a, d_a, _ = asyncio.run(
        dispatch_asgi_request("POST", "/api/v1/runs", {"url": "https://alice-site.org"}, headers=headers_a)
    )
    assert s_a == 201
    run_a_id = d_a["run_id"]

    # Bob creates Run B
    s_b, d_b, _ = asyncio.run(
        dispatch_asgi_request("POST", "/api/v1/runs", {"url": "https://bob-site.org"}, headers=headers_b)
    )
    assert s_b == 201
    run_b_id = d_b["run_id"]

    # Guest creates Run G
    s_g, d_g, _ = asyncio.run(
        dispatch_asgi_request("POST", "/api/v1/runs", {"url": "https://guest-site.org"})
    )
    assert s_g == 201
    run_g_id = d_g["run_id"]

    # Alice lists runs: must see run_a_id, run_g_id (if include_guest), but NEVER run_b_id
    status_list_a, list_a, _ = asyncio.run(
        dispatch_asgi_request("GET", "/api/v1/runs?include_guest=true", headers=headers_a)
    )
    assert status_list_a == 200
    ids_a = [r["run_id"] for r in list_a]
    assert run_a_id in ids_a
    assert run_g_id in ids_a
    assert run_b_id not in ids_a, "Alice must not see Bob's private run!"

    # Bob lists runs: must see run_b_id, run_g_id, but NEVER run_a_id
    status_list_b, list_b, _ = asyncio.run(
        dispatch_asgi_request("GET", "/api/v1/runs?include_guest=true", headers=headers_b)
    )
    assert status_list_b == 200
    ids_b = [r["run_id"] for r in list_b]
    assert run_b_id in ids_b
    assert run_g_id in ids_b
    assert run_a_id not in ids_b, "Bob must not see Alice's private run!"

    # Guest lists runs: must see run_g_id, but NEVER run_a_id or run_b_id
    status_list_guest, list_guest, _ = asyncio.run(
        dispatch_asgi_request("GET", "/api/v1/runs")
    )
    assert status_list_guest == 200
    ids_guest = [r["run_id"] for r in list_guest]
    assert run_g_id in ids_guest
    assert run_a_id not in ids_guest, "Guest must not see Alice's private run!"
    assert run_b_id not in ids_guest, "Guest must not see Bob's private run!"


def test_preview_endpoints_data_isolation():
    """Verify preview status, frame, and SSE stream endpoints enforce run ownership.

    Covers:
    - Private run accessed by its owner (200 OK for preview, frame, and SSE stream).
    - Private run accessed by another authenticated user (403 Forbidden).
    - Private run accessed without authentication (401 Unauthorized).
    - Guest run accessed without authentication (200 OK for preview, frame, and SSE stream).
    """
    user_a, token_a = create_test_user_and_session("alice_preview@example.com", "Alice Preview")
    _, token_b = create_test_user_and_session("bob_preview@example.com", "Bob Preview")
    headers_a = [(b"authorization", f"Bearer {token_a}".encode("utf-8"))]
    headers_b = [(b"authorization", f"Bearer {token_b}".encode("utf-8"))]

    # 1. User A creates private run
    s_a, d_a, _ = asyncio.run(
        dispatch_asgi_request("POST", "/api/v1/runs", {"url": "https://alice-preview.org"}, headers=headers_a)
    )
    assert s_a == 201
    run_a = d_a["run_id"]

    # Publish frame and completed state into preview_service
    dummy_frame = b"\xff\xd8\xff\xe0dummy_jpeg_bytes"
    preview_service.init_run(run_a, "https://alice-preview.org")
    preview_service.publish_frame(
        run_id=run_a,
        frame_bytes=dummy_frame,
        scroll_y=200,
        max_scroll_y=800,
        progress=25,
        stage="completed",
        viewport="desktop",
    )

    # Owner (User A) accesses /preview -> 200
    st_owner_prev, dt_owner_prev, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_a}/preview", headers=headers_a)
    )
    assert st_owner_prev == 200
    assert dt_owner_prev["run_id"] == run_a

    # Owner (User A) accesses /preview/frame -> 200
    st_owner_frame, _, hdrs_owner_frame = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_a}/preview/frame", headers=headers_a)
    )
    assert st_owner_frame == 200
    assert "image/jpeg" in hdrs_owner_frame.get("content-type", "")

    # Owner (User A) accesses stream endpoint directly -> 200 StreamingResponse
    resp_owner_stream = asyncio.run(stream_preview_events(run_a, current_user=user_a))
    assert resp_owner_stream.status_code == 200
    assert resp_owner_stream.media_type == "text/event-stream"

    # User B accesses User A's /preview -> 403 Forbidden
    st_b_prev, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_a}/preview", headers=headers_b)
    )
    assert st_b_prev == 403

    # User B accesses User A's /preview/frame -> 403 Forbidden
    st_b_frame, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_a}/preview/frame", headers=headers_b)
    )
    assert st_b_frame == 403

    # User B accesses User A's /preview/stream -> 403 Forbidden
    st_b_stream, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_a}/preview/stream", headers=headers_b)
    )
    assert st_b_stream == 403

    # Unauthenticated caller accesses User A's /preview -> 401 Unauthorized
    st_unauth_prev, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_a}/preview")
    )
    assert st_unauth_prev == 401

    # Unauthenticated caller accesses User A's /preview/frame -> 401 Unauthorized
    st_unauth_frame, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_a}/preview/frame")
    )
    assert st_unauth_frame == 401

    # Unauthenticated caller accesses User A's /preview/stream -> 401 Unauthorized
    st_unauth_stream, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_a}/preview/stream")
    )
    assert st_unauth_stream == 401

    # 2. Guest creates guest run
    s_g, d_g, _ = asyncio.run(
        dispatch_asgi_request("POST", "/api/v1/runs", {"url": "https://guest-preview.org"})
    )
    assert s_g == 201
    run_g = d_g["run_id"]

    preview_service.init_run(run_g, "https://guest-preview.org")
    preview_service.publish_frame(
        run_id=run_g,
        frame_bytes=dummy_frame,
        scroll_y=0,
        max_scroll_y=400,
        progress=10,
        stage="completed",
        viewport="desktop",
    )

    # Unauthenticated caller accesses guest /preview -> 200 OK
    st_g_prev, dt_g_prev, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_g}/preview")
    )
    assert st_g_prev == 200
    assert dt_g_prev["run_id"] == run_g

    # Unauthenticated caller accesses guest /preview/frame -> 200 OK
    st_g_frame, _, _ = asyncio.run(
        dispatch_asgi_request("GET", f"/api/v1/runs/{run_g}/preview/frame")
    )
    assert st_g_frame == 200

    # Unauthenticated caller accesses guest stream endpoint directly -> 200 StreamingResponse
    resp_g_stream = asyncio.run(stream_preview_events(run_g, current_user=None))
    assert resp_g_stream.status_code == 200
    assert resp_g_stream.media_type == "text/event-stream"
