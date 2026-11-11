"""FastAPI dependency injection and security helpers for OmniSight API.

Provides optional and required current-user resolution, database session management,
secure cookie assignment/clearing, and CSRF/origin validation.
"""

from typing import Optional
from urllib.parse import urlparse
import secrets

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.security import verify_csrf_token
from backend.app.db.session import get_db
from backend.app.models.user import UserModel
from backend.app.services.auth_service import auth_service


def extract_session_token(request: Request) -> Optional[str]:
    """Extract raw session token from HTTP-only cookie or Authorization Bearer header."""
    # 1. Primary: HTTP-only session cookie
    cookie_token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    # 2. Secondary: Authorization: Bearer <token>
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        if token:
            return token

    return None


def get_current_user_optional(
    request: Request,
    db: Session = Depends(get_db),
) -> Optional[UserModel]:
    """Resolve currently authenticated user from session token if present.

    Returns:
        UserModel if a valid, unexpired session exists and user is active;
        None if token is missing, invalid, expired, or user is inactive.
    """
    token = extract_session_token(request)
    if not token:
        return None

    session_record = auth_service.get_session_by_token(db, token)
    if not session_record:
        return None

    return session_record.user


def get_current_user_required(
    current_user: Optional[UserModel] = Depends(get_current_user_optional),
) -> UserModel:
    """Enforce authentication, rejecting unauthenticated or invalid callers with HTTP 401."""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


def set_auth_cookies(response: Response, session_token: str, csrf_token: str) -> None:
    """Set secure session and CSRF cookies using configured security parameters."""
    max_age_seconds = settings.SESSION_EXPIRE_DAYS * 86400

    # HTTP-only session cookie (protected from client-side scripts)
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        max_age=max_age_seconds,
        expires=max_age_seconds,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )

    # CSRF cookie (readable by frontend client to populate X-CSRF-Token header)
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=max_age_seconds,
        expires=max_age_seconds,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear session and CSRF cookies using matching path, domain, and security attributes."""
    response.delete_cookie(
        key=settings.SESSION_COOKIE_NAME,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key=settings.CSRF_COOKIE_NAME,
        path=settings.COOKIE_PATH,
        domain=settings.COOKIE_DOMAIN,
        secure=settings.COOKIE_SECURE,
        httponly=False,
        samesite=settings.COOKIE_SAMESITE,
    )


def _normalize_origin(raw_origin: str) -> Optional[tuple[str, str, int]]:
    """Parse and normalize an origin or referer string into (scheme, hostname, port).

    Compares exact scheme, hostname, and port according to RFC 6454.
    Returns:
        (scheme, hostname, port) tuple if valid; None if malformed or invalid scheme.
    """
    if not raw_origin or not isinstance(raw_origin, str):
        return None

    cleaned = raw_origin.strip()
    try:
        parsed = urlparse(cleaned)
        if not parsed.scheme or not parsed.netloc or not parsed.hostname:
            return None

        scheme = parsed.scheme.lower()
        if scheme not in ("http", "https"):
            return None

        hostname = parsed.hostname.lower()

        # Explicit port takes precedence; fall back to standard scheme port
        if parsed.port is not None:
            port = parsed.port
        elif scheme == "https":
            port = 443
        elif scheme == "http":
            port = 80
        else:
            return None

        return (scheme, hostname, port)
    except Exception:
        return None


def validate_trusted_origin(request: Request) -> None:
    """Validate that state-changing requests originate from an exact trusted origin.

    Compares parsed origins exactly, including scheme, hostname, and port.
    Rejects malformed, untrusted, or prefix/suffix-spoofed origins with HTTP 403.

    Deliberate Origin Policy:
    1. Cookie-authenticated requests MUST provide a valid, trusted Origin or Referer header.
    2. Browser-identified cross-site requests (Sec-Fetch-Site: cross-site) without a trusted origin
       are unconditionally rejected with HTTP 403.
    3. Machine-client exception: Direct machine/non-browser clients (e.g. mobile apps, CLI,
       server-to-server) without session cookies and without cross-site browser metadata are
       permitted to access unauthenticated state-changing endpoints (login/register) without Origin.
    4. Whenever an Origin or Referer header is present, it MUST strictly match configured CORS_ORIGINS.
    """
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")

    raw_origin = origin or referer
    has_session_cookie = bool(request.cookies.get(settings.SESSION_COOKIE_NAME))

    if not raw_origin:
        if has_session_cookie:
            logger.warning("Rejected cookie-authenticated state-changing request missing Origin and Referer headers.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Untrusted origin: missing required origin or referer header on cookie-authenticated request.",
            )

        # Reject browser-driven cross-site requests that omit or strip Origin/Referer
        sec_fetch_site = request.headers.get("sec-fetch-site")
        if sec_fetch_site and sec_fetch_site.strip().lower() == "cross-site":
            logger.warning("Rejected cross-site browser request missing Origin and Referer headers.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Untrusted origin: cross-site browser request rejected.",
            )

        # Machine-client exception: direct non-browser clients without session cookies
        # and without browser cross-site metadata are permitted to proceed.
        return

    parsed_target = _normalize_origin(raw_origin)
    if parsed_target is None:
        logger.warning("Rejected malformed or invalid origin header: %s", raw_origin)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Untrusted origin: malformed or invalid origin header.",
        )

    # Build set of exact (scheme, hostname, port) tuples from configured origins
    allowed_tuples = set()
    for o in settings.CORS_ORIGINS:
        norm = _normalize_origin(o)
        if norm:
            allowed_tuples.add(norm)

    if parsed_target not in allowed_tuples:
        logger.warning(
            "Rejected request from untrusted origin: %s (parsed: %s)",
            raw_origin,
            parsed_target,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Untrusted origin: cross-origin request rejected.",
        )


def validate_csrf(request: Request, db: Optional[Session] = None) -> None:
    """Validate CSRF token for state-changing requests authenticated via cookies.

    Enforces:
    1. Exact trusted origin validation (rejecting missing Origin/Referer on cookie requests).
    2. Double-submit cookie verification against the X-CSRF-Token header.
    3. Session-bound HMAC cryptographic verification against the caller's session_token_hash.
    """
    validate_trusted_origin(request)

    session_cookie = request.cookies.get(settings.SESSION_COOKIE_NAME)
    # Whenever a session cookie is present, CSRF token validation is mandatory
    # regardless of whether an Authorization header is also supplied.
    if session_cookie:
        csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
        csrf_header = request.headers.get("X-CSRF-Token") or request.headers.get("x-csrf-token")

        if (
            not csrf_cookie
            or not csrf_header
            or not isinstance(csrf_cookie, str)
            or not isinstance(csrf_header, str)
            or len(csrf_cookie.strip()) < 16
            or not secrets.compare_digest(csrf_cookie.strip(), csrf_header.strip())
        ):
            logger.warning("CSRF validation mismatch on request %s %s", request.method, request.url.path)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token validation failed.",
            )

        # If a database session is provided, cryptographically verify the token is bound to this user's active session
        if db is not None:
            session_record = auth_service.get_session_by_token(db, session_cookie)
            if not session_record:
                logger.warning("CSRF validation failed: active session record not found for cookie")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required.",
                )

            if not verify_csrf_token(csrf_cookie.strip(), session_record.session_token_hash):
                logger.warning(
                    "CSRF token binding mismatch: token signature does not match session %s",
                    session_record.id,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token validation failed: token is not bound to active session.",
                )
