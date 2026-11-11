"""Automated test suite for OmniSight Authentication APIs.

Verifies user registration, login, current-user resolution, logout,
session lifecycle, cookie attributes, origin protection, and CSRF defense.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response

from backend.app.api.auth import get_current_user_profile, login, logout, register
from backend.app.api.deps import get_current_user_optional, get_current_user_required
from backend.app.core.config import settings
from backend.app.core.security import hash_token
from backend.app.db.session import SessionLocal, engine, init_db
from backend.app.models.oauth_account import OAuthAccountModel
from backend.app.models.session import SessionModel
from backend.app.models.user import UserModel
from backend.app.schemas.auth import LoginRequest, RegisterRequest


def make_request(
    method: str = "POST",
    path: str = "/api/v1/auth/login",
    headers: Optional[Dict[str, str]] = None,
    cookies: Optional[Dict[str, str]] = None,
    client_host: str = "127.0.0.1",
) -> Request:
    """Construct an ASGI compliant Starlette Request object synchronously."""
    header_list = []
    default_origin = "http://localhost:5173"

    all_headers = {"origin": default_origin}
    if headers:
        all_headers.update(headers)

    for k, v in all_headers.items():
        header_list.append((k.lower().encode("latin-1"), v.encode("latin-1")))

    if cookies:
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        header_list.append((b"cookie", cookie_str.encode("latin-1")))

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": b"",
        "headers": header_list,
        "client": (client_host, 12345),
    }
    return Request(scope)


def parse_cookie_from_response(response: Response, cookie_name: str) -> Optional[dict]:
    """Parse cookie attributes from set-cookie headers in response."""
    cookie_headers = response.headers.getlist("set-cookie")
    for ch in cookie_headers:
        parts = [p.strip() for p in ch.split(";")]
        name_val = parts[0]
        if "=" in name_val:
            k, v = name_val.split("=", 1)
            if k == cookie_name:
                attrs = {"value": v}
                for attr in parts[1:]:
                    if "=" in attr:
                        ak, av = attr.split("=", 1)
                        attrs[ak.lower()] = av
                    else:
                        attrs[attr.lower()] = True
                return attrs
    return None


@pytest.fixture(autouse=True)
def clean_database():
    """Ensure database tables are initialized and clean for each test."""
    init_db(engine)
    session: Session = SessionLocal()
    try:
        session.query(OAuthAccountModel).delete()
        session.query(SessionModel).delete()
        session.query(UserModel).delete()
        session.commit()
    finally:
        session.close()

    yield

    cleanup_session: Session = SessionLocal()
    try:
        cleanup_session.query(OAuthAccountModel).delete()
        cleanup_session.query(SessionModel).delete()
        cleanup_session.query(UserModel).delete()
        cleanup_session.commit()
    finally:
        cleanup_session.close()


# =============================================================================
# Registration Tests
# =============================================================================

def test_register_success():
    """Verify successful user registration creates user, session, and cookies."""
    db: Session = SessionLocal()
    try:
        req = make_request(path="/api/v1/auth/register")
        res = Response()
        payload = RegisterRequest(
            email="developer@omnisight.dev",
            password="StrongPassword123!",
            full_name="Alex Developer",
        )

        user_response = register(request=req, response=res, payload=payload, db=db)

        # 1. Profile assertions
        assert user_response.id is not None
        assert user_response.email == "developer@omnisight.dev"
        assert user_response.full_name == "Alex Developer"
        assert user_response.is_active is True
        assert user_response.is_verified is False
        assert user_response.linked_providers == []

        # 2. Database persistence assertions
        db_user = db.query(UserModel).filter(UserModel.email == "developer@omnisight.dev").first()
        assert db_user is not None
        assert db_user.hashed_password.startswith("$argon2id$")
        assert "StrongPassword123!" not in db_user.hashed_password

        # 3. Cookie issuance assertions
        session_cookie = parse_cookie_from_response(res, settings.SESSION_COOKIE_NAME)
        csrf_cookie = parse_cookie_from_response(res, settings.CSRF_COOKIE_NAME)

        assert session_cookie is not None
        assert session_cookie["httponly"] is True
        assert session_cookie["path"] == "/"
        assert session_cookie["samesite"] == "lax"
        assert int(session_cookie["max-age"]) == settings.SESSION_EXPIRE_DAYS * 86400

        assert csrf_cookie is not None
        assert "httponly" not in csrf_cookie  # Readable by JS
        assert csrf_cookie["path"] == "/"
    finally:
        db.close()


def test_register_email_normalization():
    """Verify registration normalizes email with whitespace and mixed casing."""
    db: Session = SessionLocal()
    try:
        req = make_request(path="/api/v1/auth/register")
        res = Response()
        payload = RegisterRequest(
            email="   NoRMaLiZe.Me@EXAMPLE.Com   ",
            password="StrongPassword123!",
        )

        user_response = register(request=req, response=res, payload=payload, db=db)
        assert user_response.email == "normalize.me@example.com"

        db_user = db.query(UserModel).filter(UserModel.email == "normalize.me@example.com").first()
        assert db_user is not None
    finally:
        db.close()


def test_register_duplicate_email_rejected():
    """Verify registration with an existing email returns HTTP 400 Bad Request."""
    db: Session = SessionLocal()
    try:
        req = make_request(path="/api/v1/auth/register")
        res = Response()
        payload = RegisterRequest(
            email="duplicate@omnisight.dev",
            password="StrongPassword123!",
        )

        register(request=req, response=res, payload=payload, db=db)

        # Attempt to register identical email
        with pytest.raises(HTTPException) as exc_info:
            register(request=req, response=Response(), payload=payload, db=db)

        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail.lower()
    finally:
        db.close()


def test_register_invalid_password_too_short():
    """Verify password validation rejects strings under 8 characters."""
    with pytest.raises(ValidationError):
        RegisterRequest(email="valid@example.com", password="short")


def test_register_untrusted_origin_rejected():
    """Verify cross-origin requests from untrusted origins are blocked with HTTP 403."""
    db: Session = SessionLocal()
    try:
        req = make_request(
            path="/api/v1/auth/register",
            headers={"origin": "http://malicious-attacker.com"},
        )
        res = Response()
        payload = RegisterRequest(email="attack@omnisight.dev", password="ValidPassword123!")

        with pytest.raises(HTTPException) as exc_info:
            register(request=req, response=res, payload=payload, db=db)

        assert exc_info.value.status_code == 403
        assert "untrusted origin" in exc_info.value.detail.lower()
    finally:
        db.close()


# =============================================================================
# Login Tests
# =============================================================================

def test_login_success():
    """Verify login with valid credentials creates a fresh session and sets cookies."""
    db: Session = SessionLocal()
    try:
        # 1. Register user
        req_reg = make_request(path="/api/v1/auth/register")
        register(
            request=req_reg,
            response=Response(),
            payload=RegisterRequest(email="login.test@omnisight.dev", password="CorrectPassword123!"),
            db=db,
        )

        # 2. Login
        req_login = make_request(path="/api/v1/auth/login")
        res_login = Response()
        login_payload = LoginRequest(email="LOGIN.TEST@omnisight.dev", password="CorrectPassword123!")

        user_response = login(request=req_login, response=res_login, payload=login_payload, db=db)

        assert user_response.email == "login.test@omnisight.dev"
        session_cookie = parse_cookie_from_response(res_login, settings.SESSION_COOKIE_NAME)
        assert session_cookie is not None
        assert session_cookie["httponly"] is True
    finally:
        db.close()


def test_login_incorrect_password():
    """Verify login with incorrect password returns generic HTTP 401."""
    db: Session = SessionLocal()
    try:
        req_reg = make_request(path="/api/v1/auth/register")
        register(
            request=req_reg,
            response=Response(),
            payload=RegisterRequest(email="wrong.pwd@omnisight.dev", password="RightPassword123!"),
            db=db,
        )

        req_login = make_request(path="/api/v1/auth/login")
        login_payload = LoginRequest(email="wrong.pwd@omnisight.dev", password="BadPassword123!")

        with pytest.raises(HTTPException) as exc_info:
            login(request=req_login, response=Response(), payload=login_payload, db=db)

        assert exc_info.value.status_code == 401
        assert "invalid email or password" in exc_info.value.detail.lower()
    finally:
        db.close()


def test_login_unknown_email():
    """Verify login with unknown email returns the same generic HTTP 401."""
    db: Session = SessionLocal()
    try:
        req_login = make_request(path="/api/v1/auth/login")
        login_payload = LoginRequest(email="unknown.user@omnisight.dev", password="SomePassword123!")

        with pytest.raises(HTTPException) as exc_info:
            login(request=req_login, response=Response(), payload=login_payload, db=db)

        assert exc_info.value.status_code == 401
        assert "invalid email or password" in exc_info.value.detail.lower()
    finally:
        db.close()


def test_login_inactive_account():
    """Verify login against an inactive account returns HTTP 403 Forbidden."""
    db: Session = SessionLocal()
    try:
        req_reg = make_request(path="/api/v1/auth/register")
        user = register(
            request=req_reg,
            response=Response(),
            payload=RegisterRequest(email="inactive@omnisight.dev", password="Password123!"),
            db=db,
        )

        # Mark user inactive
        db_user = db.query(UserModel).filter(UserModel.id == user.id).first()
        db_user.is_active = False
        db.commit()

        req_login = make_request(path="/api/v1/auth/login")
        login_payload = LoginRequest(email="inactive@omnisight.dev", password="Password123!")

        with pytest.raises(HTTPException) as exc_info:
            login(request=req_login, response=Response(), payload=login_payload, db=db)

        assert exc_info.value.status_code == 403
        assert "inactive" in exc_info.value.detail.lower()
    finally:
        db.close()


# =============================================================================
# Current User (/api/v1/auth/me) Tests
# =============================================================================

def test_get_me_valid_session():
    """Verify GET /me returns authenticated user profile with linked providers."""
    db: Session = SessionLocal()
    try:
        req_reg = make_request(path="/api/v1/auth/register")
        res_reg = Response()
        user_reg = register(
            request=req_reg,
            response=res_reg,
            payload=RegisterRequest(email="current.user@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)
        raw_token = session_cookie["value"]

        # Link an OAuth provider for profile verification
        oauth_acc = OAuthAccountModel(
            user_id=user_reg.id,
            provider="google",
            provider_user_id="google-id-777",
        )
        db.add(oauth_acc)
        db.commit()

        # Call dependency directly
        req_me = make_request(
            method="GET",
            path="/api/v1/auth/me",
            cookies={settings.SESSION_COOKIE_NAME: raw_token},
        )
        resolved_user = get_current_user_required(get_current_user_optional(req_me, db))

        profile = get_current_user_profile(current_user=resolved_user)
        assert profile.email == "current.user@omnisight.dev"
        assert profile.linked_providers == ["google"]
    finally:
        db.close()


def test_get_me_missing_session():
    """Verify GET /me without session cookie or token raises HTTP 401."""
    db: Session = SessionLocal()
    try:
        req_me = make_request(method="GET", path="/api/v1/auth/me")
        user = get_current_user_optional(req_me, db)
        assert user is None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_required(user)

        assert exc_info.value.status_code == 401
    finally:
        db.close()


def test_get_me_invalid_session_token():
    """Verify GET /me with an unrecorded/invalid token raises HTTP 401."""
    db: Session = SessionLocal()
    try:
        req_me = make_request(
            method="GET",
            path="/api/v1/auth/me",
            cookies={settings.SESSION_COOKIE_NAME: "bogus-random-nonexistent-token"},
        )
        user = get_current_user_optional(req_me, db)
        assert user is None

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_required(user)

        assert exc_info.value.status_code == 401
    finally:
        db.close()


def test_get_me_expired_session():
    """Verify expired session is rejected with HTTP 401 and cleaned up."""
    db: Session = SessionLocal()
    try:
        req_reg = make_request(path="/api/v1/auth/register")
        res_reg = Response()
        user_reg = register(
            request=req_reg,
            response=res_reg,
            payload=RegisterRequest(email="expired@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)
        raw_token = session_cookie["value"]
        token_hash = hash_token(raw_token)

        # Force session expiration into the past
        db_session = db.query(SessionModel).filter(SessionModel.session_token_hash == token_hash).first()
        db_session.expires_at = datetime.now(timezone.utc) - timedelta(hours=2)
        db.commit()

        req_me = make_request(
            method="GET",
            path="/api/v1/auth/me",
            cookies={settings.SESSION_COOKIE_NAME: raw_token},
        )
        user = get_current_user_optional(req_me, db)
        assert user is None

        # Verify expired session was purged
        remaining = db.query(SessionModel).filter(SessionModel.session_token_hash == token_hash).first()
        assert remaining is None
    finally:
        db.close()


def test_get_me_via_bearer_header():
    """Verify authentication succeeds when session token is supplied via Authorization Bearer header."""
    db: Session = SessionLocal()
    try:
        req_reg = make_request(path="/api/v1/auth/register")
        res_reg = Response()
        register(
            request=req_reg,
            response=res_reg,
            payload=RegisterRequest(email="bearer@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)
        raw_token = session_cookie["value"]

        req_me = make_request(
            method="GET",
            path="/api/v1/auth/me",
            headers={"authorization": f"Bearer {raw_token}"},
        )
        user = get_current_user_optional(req_me, db)
        assert user is not None
        assert user.email == "bearer@omnisight.dev"
    finally:
        db.close()


# =============================================================================
# Logout Tests
# =============================================================================

def test_logout_revokes_session_and_clears_cookies():
    """Verify logout deletes database session and sends clearing cookie headers."""
    db: Session = SessionLocal()
    try:
        req_reg = make_request(path="/api/v1/auth/register")
        res_reg = Response()
        register(
            request=req_reg,
            response=res_reg,
            payload=RegisterRequest(email="logout@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)
        csrf_cookie = parse_cookie_from_response(res_reg, settings.CSRF_COOKIE_NAME)
        raw_session_token = session_cookie["value"]
        csrf_token = csrf_cookie["value"]
        token_hash = hash_token(raw_session_token)

        # Call logout with cookie and X-CSRF-Token header
        req_logout = make_request(
            path="/api/v1/auth/logout",
            headers={"X-CSRF-Token": csrf_token},
            cookies={
                settings.SESSION_COOKIE_NAME: raw_session_token,
                settings.CSRF_COOKIE_NAME: csrf_token,
            },
        )
        res_logout = Response()
        logout_resp = logout(request=req_logout, response=res_logout, db=db)

        assert logout_resp["message"] == "Logged out successfully."

        # Database session must be deleted
        db_session = db.query(SessionModel).filter(SessionModel.session_token_hash == token_hash).first()
        assert db_session is None

        # Cookies must be cleared (max-age=0 or expires in the past)
        cleared_session = parse_cookie_from_response(res_logout, settings.SESSION_COOKIE_NAME)
        cleared_csrf = parse_cookie_from_response(res_logout, settings.CSRF_COOKIE_NAME)

        assert cleared_session is not None
        assert int(cleared_session.get("max-age", 1)) == 0
        assert cleared_csrf is not None
        assert int(cleared_csrf.get("max-age", 1)) == 0
    finally:
        db.close()


def test_logout_repeated_safe():
    """Verify repeated logout calls do not crash and return 200 OK."""
    db: Session = SessionLocal()
    try:
        req_logout = make_request(path="/api/v1/auth/logout")
        res1 = Response()
        res2 = Response()

        out1 = logout(request=req_logout, response=res1, db=db)
        out2 = logout(request=req_logout, response=res2, db=db)

        assert out1["message"] == "Logged out successfully."
        assert out2["message"] == "Logged out successfully."
    finally:
        db.close()


def test_logout_csrf_mismatch_rejected():
    """Verify cookie-authenticated logout without matching X-CSRF-Token header is rejected with HTTP 403."""
    db: Session = SessionLocal()
    try:
        req_reg = make_request(path="/api/v1/auth/register")
        res_reg = Response()
        register(
            request=req_reg,
            response=res_reg,
            payload=RegisterRequest(email="csrf.fail@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)
        csrf_cookie = parse_cookie_from_response(res_reg, settings.CSRF_COOKIE_NAME)

        # Send request with valid session and CSRF cookie, but WRONG header
        req_bad_csrf = make_request(
            path="/api/v1/auth/logout",
            headers={"X-CSRF-Token": "tampered-wrong-csrf-token"},
            cookies={
                settings.SESSION_COOKIE_NAME: session_cookie["value"],
                settings.CSRF_COOKIE_NAME: csrf_cookie["value"],
            },
        )

        with pytest.raises(HTTPException) as exc_info:
            logout(request=req_bad_csrf, response=Response(), db=db)

        assert exc_info.value.status_code == 403
        assert "csrf token validation failed" in exc_info.value.detail.lower()
    finally:
        db.close()


# =============================================================================
# Security Attribute and Plaintext Resistance Tests
# =============================================================================

def test_security_raw_token_never_in_database():
    """Verify raw session token is never stored in plaintext anywhere in the database."""
    db: Session = SessionLocal()
    try:
        req_reg = make_request(path="/api/v1/auth/register")
        res_reg = Response()
        register(
            request=req_reg,
            response=res_reg,
            payload=RegisterRequest(email="token.leak@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)
        raw_token = session_cookie["value"]

        # Search entire sessions table for any field containing the raw token
        all_sessions = db.query(SessionModel).all()
        assert len(all_sessions) == 1

        s = all_sessions[0]
        assert s.session_token_hash != raw_token
        assert raw_token not in str(s.session_token_hash)
        assert s.session_token_hash == hash_token(raw_token)
    finally:
        db.close()


def test_origin_validation_exact_scheme_host_port():
    """Verify that origin validation enforces exact scheme, host, and port matching."""
    db: Session = SessionLocal()
    try:
        res = Response()
        payload = RegisterRequest(email="origin.test@omnisight.dev", password="Password123!")

        # 1. Exact match succeeds
        req_exact = make_request(
            path="/api/v1/auth/register",
            headers={"origin": "http://localhost:5173"},
        )
        u1 = register(request=req_exact, response=res, payload=payload, db=db)
        assert u1.email == "origin.test@omnisight.dev"

        # 2. Case normalization and trailing slash succeed
        payload2 = RegisterRequest(email="origin.test2@omnisight.dev", password="Password123!")
        req_case = make_request(
            path="/api/v1/auth/register",
            headers={"origin": "HTTP://LOCALHOST:5173/"},
        )
        u2 = register(request=req_case, response=Response(), payload=payload2, db=db)
        assert u2.email == "origin.test2@omnisight.dev"

        # 3. Different port must be rejected (403)
        req_diff_port = make_request(
            path="/api/v1/auth/register",
            headers={"origin": "http://localhost:5174"},
        )
        with pytest.raises(HTTPException) as exc1:
            register(request=req_diff_port, response=Response(), payload=RegisterRequest(email="p@o.dev", password="Password123!"), db=db)
        assert exc1.value.status_code == 403

        # 4. Different scheme must be rejected (403)
        req_diff_scheme = make_request(
            path="/api/v1/auth/register",
            headers={"origin": "https://localhost:5173"},
        )
        with pytest.raises(HTTPException) as exc2:
            register(request=req_diff_scheme, response=Response(), payload=RegisterRequest(email="s@o.dev", password="Password123!"), db=db)
        assert exc2.value.status_code == 403

        # 5. Suffix spoofing (subdomain of attacker) must be rejected (403)
        req_spoof = make_request(
            path="/api/v1/auth/register",
            headers={"origin": "http://localhost:5173.attacker.com"},
        )
        with pytest.raises(HTTPException) as exc3:
            register(request=req_spoof, response=Response(), payload=RegisterRequest(email="a@o.dev", password="Password123!"), db=db)
        assert exc3.value.status_code == 403

        # 6. Malformed origin header must be rejected (403)
        req_malformed = make_request(
            path="/api/v1/auth/register",
            headers={"origin": "not-a-valid-origin"},
        )
        with pytest.raises(HTTPException) as exc4:
            register(request=req_malformed, response=Response(), payload=RegisterRequest(email="m@o.dev", password="Password123!"), db=db)
        assert exc4.value.status_code == 403
    finally:
        db.close()


def test_cookie_auth_with_bearer_cannot_bypass_csrf():
    """Verify that a request carrying a session cookie cannot bypass CSRF validation by supplying a Bearer token."""
    db: Session = SessionLocal()
    try:
        req_reg = make_request(path="/api/v1/auth/register")
        res_reg = Response()
        register(
            request=req_reg,
            response=res_reg,
            payload=RegisterRequest(email="csrf.bypass@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)
        csrf_cookie = parse_cookie_from_response(res_reg, settings.CSRF_COOKIE_NAME)
        raw_session_token = session_cookie["value"]

        # An attacker attempts to logout using victim's session cookie and adding an Authorization header to bypass CSRF
        req_bypass_attempt = make_request(
            path="/api/v1/auth/logout",
            headers={"authorization": f"Bearer {raw_session_token}"},
            cookies={
                settings.SESSION_COOKIE_NAME: raw_session_token,
                settings.CSRF_COOKIE_NAME: csrf_cookie["value"],
            },
        )

        # Must fail with 403 because X-CSRF-Token header was omitted
        with pytest.raises(HTTPException) as exc_info:
            logout(request=req_bypass_attempt, response=Response(), db=db)

        assert exc_info.value.status_code == 403
        assert "csrf token validation failed" in exc_info.value.detail.lower()
    finally:
        db.close()


def test_user_profile_response_always_has_timezone_aware_utc():
    """Verify that user_to_response ensures UTC timezone information even if naive in database."""
    from backend.app.services.auth_service import auth_service

    # Create user with timezone-naive datetime (simulating raw SQLite driver returns)
    naive_dt = datetime(2026, 11, 11, 12, 0, 0)
    user = UserModel(
        id="test-uuid-tz",
        email="tz.test@omnisight.dev",
        is_active=True,
        is_verified=False,
        created_at=naive_dt,
        updated_at=naive_dt,
    )

    resp = auth_service.user_to_response(user)
    assert resp.created_at.tzinfo is not None
    assert resp.created_at.tzinfo == timezone.utc
    assert resp.updated_at.tzinfo is not None
    assert resp.updated_at.tzinfo == timezone.utc


# =============================================================================
# CSRF Cryptographic Binding, Tampering, and Injection Tests
# =============================================================================

def test_csrf_token_tampering_rejected():
    """Verify that a tampered CSRF token signature is rejected with HTTP 403."""
    db: Session = SessionLocal()
    try:
        req_reg = make_request(path="/api/v1/auth/register")
        res_reg = Response()
        register(
            request=req_reg,
            response=res_reg,
            payload=RegisterRequest(email="tamper.csrf@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)
        csrf_cookie = parse_cookie_from_response(res_reg, settings.CSRF_COOKIE_NAME)
        valid_csrf = csrf_cookie["value"]

        # Tamper with the HMAC signature (flip last characters)
        tampered_csrf = valid_csrf[:-4] + "dead"

        req_tampered = make_request(
            path="/api/v1/auth/logout",
            headers={"X-CSRF-Token": tampered_csrf},
            cookies={
                settings.SESSION_COOKIE_NAME: session_cookie["value"],
                settings.CSRF_COOKIE_NAME: tampered_csrf,
            },
        )

        with pytest.raises(HTTPException) as exc_info:
            logout(request=req_tampered, response=Response(), db=db)

        assert exc_info.value.status_code == 403
        assert "not bound to active session" in exc_info.value.detail.lower()
    finally:
        db.close()


def test_csrf_cookie_injection_cross_session_rejected():
    """Verify that a valid CSRF token from Session B injected into Session A is rejected."""
    db: Session = SessionLocal()
    try:
        # User A registers (Victim)
        res_a = Response()
        register(
            request=make_request(path="/api/v1/auth/register"),
            response=res_a,
            payload=RegisterRequest(email="victim.user@omnisight.dev", password="Password123!"),
            db=db,
        )
        session_a = parse_cookie_from_response(res_a, settings.SESSION_COOKIE_NAME)["value"]

        # User B registers (Attacker)
        res_b = Response()
        register(
            request=make_request(path="/api/v1/auth/register"),
            response=res_b,
            payload=RegisterRequest(email="attacker.user@omnisight.dev", password="Password123!"),
            db=db,
        )
        csrf_b = parse_cookie_from_response(res_b, settings.CSRF_COOKIE_NAME)["value"]

        # Attacker injects their own CSRF token B into victim's session A
        # Both cookie and header match csrf_b (simulating standard double-submit match)
        req_injected = make_request(
            path="/api/v1/auth/logout",
            headers={"X-CSRF-Token": csrf_b},
            cookies={
                settings.SESSION_COOKIE_NAME: session_a,
                settings.CSRF_COOKIE_NAME: csrf_b,
            },
        )

        with pytest.raises(HTTPException) as exc_info:
            logout(request=req_injected, response=Response(), db=db)

        # Must fail because csrf_b is bound to session B, NOT victim session A
        assert exc_info.value.status_code == 403
        assert "not bound to active session" in exc_info.value.detail.lower()
    finally:
        db.close()


def test_csrf_missing_origin_and_referer_on_cookie_auth_rejected():
    """Verify that a cookie-authenticated state-changing request missing Origin and Referer is rejected."""
    db: Session = SessionLocal()
    try:
        res_reg = Response()
        register(
            request=make_request(path="/api/v1/auth/register"),
            response=res_reg,
            payload=RegisterRequest(email="no.origin@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)["value"]
        csrf_cookie = parse_cookie_from_response(res_reg, settings.CSRF_COOKIE_NAME)["value"]

        # Construct request with session cookie but explicitly WITHOUT origin or referer header
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/logout",
            "raw_path": b"/api/v1/auth/logout",
            "query_string": b"",
            "headers": [
                (b"cookie", f"{settings.SESSION_COOKIE_NAME}={session_cookie}; {settings.CSRF_COOKIE_NAME}={csrf_cookie}".encode("latin-1")),
                (b"x-csrf-token", csrf_cookie.encode("latin-1")),
            ],
            "client": ("127.0.0.1", 1234),
        }
        req_stripped = Request(scope)

        with pytest.raises(HTTPException) as exc_info:
            logout(request=req_stripped, response=Response(), db=db)

        assert exc_info.value.status_code == 403
        assert "missing required origin or referer" in exc_info.value.detail.lower()
    finally:
        db.close()


def test_csrf_invalid_token_format_rejected():
    """Verify that malformed or non-delimited CSRF tokens are rejected with HTTP 403."""
    db: Session = SessionLocal()
    try:
        res_reg = Response()
        register(
            request=make_request(path="/api/v1/auth/register"),
            response=res_reg,
            payload=RegisterRequest(email="malformed.csrf@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)["value"]
        garbage_token = "plain_string_without_dot_signature_at_all"

        req_garbage = make_request(
            path="/api/v1/auth/logout",
            headers={"X-CSRF-Token": garbage_token},
            cookies={
                settings.SESSION_COOKIE_NAME: session_cookie,
                settings.CSRF_COOKIE_NAME: garbage_token,
            },
        )

        with pytest.raises(HTTPException) as exc_info:
            logout(request=req_garbage, response=Response(), db=db)

        assert exc_info.value.status_code == 403
    finally:
        db.close()


def test_login_untrusted_origin_rejected():
    """Verify that login endpoint rejects requests with untrusted or spoofed origins."""
    db: Session = SessionLocal()
    try:
        # First register a user
        reg_req = make_request(path="/api/v1/auth/register")
        register(
            request=reg_req,
            response=Response(),
            payload=RegisterRequest(email="login.origin@omnisight.dev", password="Password123!"),
            db=db,
        )

        # Attempt login with untrusted origin
        untrusted_req = make_request(
            path="/api/v1/auth/login",
            headers={"origin": "http://evil-attacker.com"},
        )
        with pytest.raises(HTTPException) as exc_info:
            login(
                request=untrusted_req,
                response=Response(),
                payload=LoginRequest(email="login.origin@omnisight.dev", password="Password123!"),
                db=db,
            )

        assert exc_info.value.status_code == 403
        assert "untrusted origin" in exc_info.value.detail.lower()
    finally:
        db.close()


def test_csrf_secret_rotation_invalidates_old_tokens():
    """Verify that rotating settings.CSRF_SECRET_KEY safely invalidates previously issued CSRF tokens."""
    db: Session = SessionLocal()
    original_secret = settings.CSRF_SECRET_KEY
    try:
        res_reg = Response()
        register(
            request=make_request(path="/api/v1/auth/register"),
            response=res_reg,
            payload=RegisterRequest(email="csrf.rotation@omnisight.dev", password="Password123!"),
            db=db,
        )

        session_cookie = parse_cookie_from_response(res_reg, settings.SESSION_COOKIE_NAME)["value"]
        csrf_cookie = parse_cookie_from_response(res_reg, settings.CSRF_COOKIE_NAME)["value"]

        # Simulate rotating the CSRF secret key on the running server
        settings.CSRF_SECRET_KEY = "rotated-new-production-csrf-key-32b-length"

        # Attempt logout with the old token signed under the previous secret
        req = make_request(
            path="/api/v1/auth/logout",
            headers={"X-CSRF-Token": csrf_cookie},
            cookies={
                settings.SESSION_COOKIE_NAME: session_cookie,
                settings.CSRF_COOKIE_NAME: csrf_cookie,
            },
        )

        with pytest.raises(HTTPException) as exc_info:
            logout(request=req, response=Response(), db=db)

        assert exc_info.value.status_code == 403
        assert "not bound to active session" in exc_info.value.detail.lower()
    finally:
        settings.CSRF_SECRET_KEY = original_secret
        db.close()


def test_origin_sec_fetch_site_cross_site_rejected_without_origin():
    """Verify that a browser cross-site request missing Origin/Referer is rejected with HTTP 403."""
    db: Session = SessionLocal()
    try:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "raw_path": b"/api/v1/auth/login",
            "query_string": b"",
            "headers": [
                (b"sec-fetch-site", b"cross-site"),
            ],
            "client": ("127.0.0.1", 1234),
        }
        req = Request(scope)

        with pytest.raises(HTTPException) as exc_info:
            login(
                request=req,
                response=Response(),
                payload=LoginRequest(email="test@omnisight.dev", password="Password123!"),
                db=db,
            )

        assert exc_info.value.status_code == 403
        assert "cross-site browser request rejected" in exc_info.value.detail.lower()
    finally:
        db.close()


def test_machine_client_origin_less_login_permitted():
    """Verify that legitimate non-browser machine clients without session cookies or cross-site metadata can access login."""
    db: Session = SessionLocal()
    try:
        # Register user first
        reg_req = make_request(path="/api/v1/auth/register")
        register(
            request=reg_req,
            response=Response(),
            payload=RegisterRequest(email="machine.client@omnisight.dev", password="Password123!"),
            db=db,
        )

        # Machine client request: no origin, no cookies, no sec-fetch-site
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "raw_path": b"/api/v1/auth/login",
            "query_string": b"",
            "headers": [
                (b"user-agent", b"OmniSight-CLI/1.0.0"),
            ],
            "client": ("127.0.0.1", 1234),
        }
        req = Request(scope)
        res = Response()
        user_resp = login(
            request=req,
            response=res,
            payload=LoginRequest(email="machine.client@omnisight.dev", password="Password123!"),
            db=db,
        )

        assert user_resp.email == "machine.client@omnisight.dev"
    finally:
        db.close()


def test_csrf_secret_key_production_validation(monkeypatch):
    """Verify production startup validation for CSRF_SECRET_KEY."""
    from backend.app.core.config import Settings

    # Case 1: APP_ENV=production without CSRF_SECRET_KEY -> ValueError
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("CSRF_SECRET_KEY", raising=False)
    with pytest.raises(ValueError) as exc1:
        Settings()
    assert "CSRF_SECRET_KEY must be set in production" in str(exc1.value)

    # Case 2: APP_ENV=production with short key (< 32 chars) -> ValueError
    monkeypatch.setenv("CSRF_SECRET_KEY", "too-short")
    with pytest.raises(ValueError) as exc2:
        Settings()
    assert "at least 32 characters" in str(exc2.value)

    # Case 3: APP_ENV=production with dev placeholder -> ValueError
    monkeypatch.setenv("CSRF_SECRET_KEY", "omnisight-dev-insecure-csrf-secret-key-32b")
    with pytest.raises(ValueError) as exc3:
        Settings()
    assert "CSRF_SECRET_KEY must be set in production" in str(exc3.value)

    # Case 4: APP_ENV=production with valid 32+ char key -> Succeeds
    valid_key = "a" * 32
    monkeypatch.setenv("CSRF_SECRET_KEY", valid_key)
    prod_settings = Settings()
    assert prod_settings.CSRF_SECRET_KEY == valid_key

    # Case 5: APP_ENV=development without CSRF_SECRET_KEY -> Falls back to dev placeholder
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("CSRF_SECRET_KEY", raising=False)
    dev_settings = Settings()
    assert dev_settings.CSRF_SECRET_KEY == "omnisight-dev-insecure-csrf-secret-key-32b"
