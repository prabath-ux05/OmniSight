"""Authentication service module for OmniSight.

Manages user registration, credential verification, session creation,
session lookup, revocation, and user profile resolution.
Uses Argon2id hashing and stores only SHA-256 digests of session tokens.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.security import hash_password, hash_token, generate_secure_token, verify_password
from backend.app.models.session import SessionModel
from backend.app.models.user import UserModel
from backend.app.schemas.auth import LoginRequest, RegisterRequest, UserResponse


class AuthServiceError(Exception):
    """Base exception for authentication service errors."""
    pass


class DuplicateEmailError(AuthServiceError):
    """Raised when registration is attempted with an existing email address."""
    pass


class InvalidCredentialsError(AuthServiceError):
    """Raised when authentication credentials fail verification."""
    pass


class InactiveAccountError(AuthServiceError):
    """Raised when login is attempted against an inactive or suspended account."""
    pass


def _ensure_utc_datetime(dt: Optional[datetime]) -> Optional[datetime]:
    """Ensure a datetime instance is timezone-aware in UTC.

    Safely handles string datetimes and naive datetimes returned by SQLite.
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AuthService:
    """Core authentication service encapsulating identity and session workflows."""

    def register_user(self, db: Session, request: RegisterRequest) -> UserModel:
        """Register a new user account with Argon2id password hash.

        Args:
            db: Active database session.
            request: Validated registration payload.

        Returns:
            Newly created UserModel instance.

        Raises:
            DuplicateEmailError: If the normalized email address is already registered.
        """
        normalized_email = request.email.strip().lower()

        existing_user = db.query(UserModel).filter(UserModel.email == normalized_email).first()
        if existing_user:
            logger.warning("Registration rejected: duplicate email %s", normalized_email)
            raise DuplicateEmailError("An account with this email address already exists.")

        hashed_pw = hash_password(request.password)

        now_utc = datetime.now(timezone.utc)
        new_user = UserModel(
            email=normalized_email,
            hashed_password=hashed_pw,
            full_name=request.full_name,
            is_active=True,
            is_verified=False,
            created_at=now_utc,
            updated_at=now_utc,
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        logger.info("Successfully registered new user: %s", new_user.id)
        return new_user

    def authenticate_user(self, db: Session, request: LoginRequest) -> UserModel:
        """Authenticate user credentials using constant-time Argon2id verification.

        Args:
            db: Active database session.
            request: Validated login payload.

        Returns:
            Authenticated UserModel instance.

        Raises:
            InvalidCredentialsError: On incorrect password, missing user, or account without password.
            InactiveAccountError: If the user account is marked inactive.
        """
        normalized_email = request.email.strip().lower()
        user = db.query(UserModel).filter(UserModel.email == normalized_email).first()

        # Generic failure message to prevent email enumeration
        if not user or not user.hashed_password:
            logger.warning("Authentication failed: user not found or has no password hash (%s)", normalized_email)
            raise InvalidCredentialsError("Invalid email or password.")

        if not verify_password(request.password, user.hashed_password):
            logger.warning("Authentication failed: password mismatch for user %s", user.id)
            raise InvalidCredentialsError("Invalid email or password.")

        if not user.is_active:
            logger.warning("Authentication rejected: account %s is inactive", user.id)
            raise InactiveAccountError("Account is inactive or suspended.")

        logger.info("Successfully authenticated user: %s", user.id)
        return user

    def create_session(
        self,
        db: Session,
        user: UserModel,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[SessionModel, str]:
        """Create a new database-backed session for an authenticated user.

        Generates a 32-byte opaque raw token, persists exclusively its SHA-256 hash,
        and returns both the SessionModel entity and the plaintext raw token for cookie issuance.

        Args:
            db: Active database session.
            user: Authenticated UserModel.
            user_agent: Optional HTTP User-Agent header string.
            ip_address: Optional client IP address string.

        Returns:
            Tuple of (SessionModel, raw_session_token_string).
        """
        raw_token = generate_secure_token(32)
        token_hash = hash_token(raw_token)

        now_utc = datetime.now(timezone.utc)
        expires_at = now_utc + timedelta(days=settings.SESSION_EXPIRE_DAYS)

        session_record = SessionModel(
            user_id=user.id,
            session_token_hash=token_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=expires_at,
            created_at=now_utc,
            last_active_at=now_utc,
        )
        db.add(session_record)
        db.commit()
        db.refresh(session_record)

        logger.info("Created session %s for user %s (expires: %s)", session_record.id, user.id, expires_at.isoformat())
        return session_record, raw_token

    def get_session_by_token(self, db: Session, raw_token: str) -> Optional[SessionModel]:
        """Look up, validate, and refresh an active session by its raw token.

        Hashes the incoming raw token and looks up the stored SHA-256 digest.
        Validates expiration against timezone-aware UTC timestamps and checks user active status.

        Args:
            db: Active database session.
            raw_token: Raw session token from cookie or header.

        Returns:
            Valid SessionModel if active and unexpired, None otherwise.
        """
        if not raw_token or not isinstance(raw_token, str):
            return None

        try:
            token_hash = hash_token(raw_token)
        except ValueError:
            return None

        session_record = db.query(SessionModel).filter(SessionModel.session_token_hash == token_hash).first()
        if not session_record:
            return None

        # Safe datetime expiration handling (supporting both native DateTime and SQLite string conversions)
        now_utc = datetime.now(timezone.utc)
        expires_at = session_record.expires_at

        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            except Exception:
                return None

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at <= now_utc:
            logger.info("Session %s has expired (expired at %s)", session_record.id, expires_at.isoformat())
            try:
                db.delete(session_record)
                db.commit()
            except Exception:
                db.rollback()
            return None

        # Check if user account is active
        if not session_record.user or not session_record.user.is_active:
            logger.warning("Session %s rejected: associated user is inactive or missing", session_record.id)
            return None

        # Update last_active_at timestamp
        try:
            session_record.last_active_at = now_utc
            db.commit()
        except Exception:
            db.rollback()

        return session_record

    def revoke_session(self, db: Session, raw_token: str) -> bool:
        """Revoke a session by deleting it from the database.

        Safe to invoke repeatedly or when the session does not exist.

        Args:
            db: Active database session.
            raw_token: Raw session token to revoke.

        Returns:
            True if a matching session was deleted, False otherwise.
        """
        if not raw_token or not isinstance(raw_token, str):
            return False

        try:
            token_hash = hash_token(raw_token)
        except ValueError:
            return False

        deleted = db.query(SessionModel).filter(SessionModel.session_token_hash == token_hash).delete()
        db.commit()
        if deleted > 0:
            logger.info("Revoked active session with hash %s...", token_hash[:8])
            return True
        return False

    def user_to_response(self, user: UserModel) -> UserResponse:
        """Transform a UserModel database entity into a public UserResponse."""
        linked_providers = [acc.provider for acc in (user.oauth_accounts or [])]
        now_fallback = datetime.now(timezone.utc)
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=_ensure_utc_datetime(user.created_at) or now_fallback,
            updated_at=_ensure_utc_datetime(user.updated_at) or now_fallback,
            linked_providers=linked_providers,
        )


auth_service = AuthService()
