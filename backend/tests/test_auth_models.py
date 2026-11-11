"""Automated test suite for OmniSight authentication SQLAlchemy models."""

from datetime import datetime, timezone
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal, init_db, engine
from backend.app.models.oauth_account import OAuthAccountModel
from backend.app.models.session import SessionModel
from backend.app.models.user import UserModel
from backend.app.core.security import hash_password, hash_token, generate_secure_token


@pytest.fixture(autouse=True)
def clean_auth_tables():
    """Ensure auth tables are initialized and clean for each test."""
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


def test_user_model_creation_and_defaults():
    """Verify that UserModel persists correctly with expected default values."""
    db: Session = SessionLocal()
    try:
        user = UserModel(
            email="TEST.USER@EXAMPLE.COM",
            hashed_password=hash_password("Secr3tP@ss!"),
            full_name="Test Operator",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.id is not None
        assert len(user.id) == 36
        # Email must be normalized to lowercase
        assert user.email == "test.user@example.com"
        assert user.full_name == "Test Operator"
        assert user.is_active is True
        assert user.is_verified is False
        assert user.created_at is not None
        assert isinstance(user.created_at, datetime)
        assert user.updated_at is not None
        assert isinstance(user.updated_at, datetime)
        assert user.avatar_url is None
    finally:
        db.close()


def test_user_model_email_normalization_trims_whitespace():
    """Verify that email validator strips whitespace and converts to lowercase."""
    db: Session = SessionLocal()
    try:
        user = UserModel(
            email="   Whitespace.User@DOMAIN.Org   ",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        assert user.email == "whitespace.user@domain.org"
    finally:
        db.close()


def test_user_model_email_uniqueness_enforced():
    """Verify that creating two users with the same email raises an IntegrityError."""
    db: Session = SessionLocal()
    try:
        user1 = UserModel(email="duplicate@example.com", full_name="User One")
        db.add(user1)
        db.commit()

        user2 = UserModel(email="DUPLICATE@example.com", full_name="User Two")
        db.add(user2)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_session_model_creation_and_lookup():
    """Verify that SessionModel persists with SHA-256 token hash and user relationship."""
    db: Session = SessionLocal()
    try:
        user = UserModel(email="session.test@example.com", full_name="Session Tester")
        db.add(user)
        db.commit()
        db.refresh(user)

        raw_token = generate_secure_token()
        token_hash = hash_token(raw_token)
        expires_at_dt = datetime.now(timezone.utc)

        session_record = SessionModel(
            user_id=user.id,
            session_token_hash=token_hash,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            ip_address="127.0.0.1",
            expires_at=expires_at_dt,
        )
        db.add(session_record)
        db.commit()
        db.refresh(session_record)

        assert session_record.id is not None
        assert session_record.user_id == user.id
        assert session_record.session_token_hash == token_hash
        assert session_record.user.email == "session.test@example.com"
        assert len(user.sessions) == 1
    finally:
        db.close()


def test_session_model_token_hash_uniqueness():
    """Verify that duplicate session_token_hash values are rejected."""
    db: Session = SessionLocal()
    try:
        user = UserModel(email="session.dup@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)

        token_hash = hash_token("identical-session-token")
        future_dt = datetime(2026, 12, 31, 0, 0, 0, tzinfo=timezone.utc)
        s1 = SessionModel(user_id=user.id, session_token_hash=token_hash, expires_at=future_dt)
        db.add(s1)
        db.commit()

        s2 = SessionModel(user_id=user.id, session_token_hash=token_hash, expires_at=future_dt)
        db.add(s2)
        with pytest.raises(IntegrityError):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_oauth_account_creation_and_uniqueness():
    """Verify OAuthAccountModel creation and (provider, provider_user_id) unique constraint."""
    db: Session = SessionLocal()
    try:
        user = UserModel(email="oauth.user@example.com", full_name="OAuth User")
        db.add(user)
        db.commit()
        db.refresh(user)

        # Link Google account
        oauth_google = OAuthAccountModel(
            user_id=user.id,
            provider="google",
            provider_user_id="google-sub-12345",
            provider_email="oauth.user@example.com",
        )
        db.add(oauth_google)
        db.commit()
        db.refresh(oauth_google)

        assert oauth_google.id is not None
        assert oauth_google.user_id == user.id
        assert oauth_google.provider == "google"
        assert oauth_google.user.email == "oauth.user@example.com"

        # Attempt to link duplicate Google account with same provider_user_id must fail
        duplicate_google = OAuthAccountModel(
            user_id=user.id,
            provider="google",
            provider_user_id="google-sub-12345",
        )
        db.add(duplicate_google)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        # Same provider_user_id with different provider (e.g. microsoft) is permitted
        oauth_ms = OAuthAccountModel(
            user_id=user.id,
            provider="microsoft",
            provider_user_id="google-sub-12345",
            provider_email="oauth.user@microsoft.com",
        )
        db.add(oauth_ms)
        db.commit()
        db.refresh(user)
        assert len(user.oauth_accounts) == 2
    finally:
        db.close()


def test_cascade_delete_removes_sessions_and_oauth_accounts():
    """Verify that deleting a UserModel cascades and removes all linked sessions and oauth accounts."""
    db: Session = SessionLocal()
    try:
        user = UserModel(email="cascade@example.com", full_name="Cascade User")
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

        session_record = SessionModel(
            user_id=user_id,
            session_token_hash=hash_token("cascade-token"),
            expires_at=datetime(2026, 12, 31, 0, 0, 0, tzinfo=timezone.utc),
        )
        oauth_record = OAuthAccountModel(
            user_id=user_id,
            provider="google",
            provider_user_id="cascade-sub-999",
        )
        db.add(session_record)
        db.add(oauth_record)
        db.commit()

        # Delete user
        db.delete(user)
        db.commit()

        # Verify child records were cascade-deleted
        remaining_sessions = db.query(SessionModel).filter(SessionModel.user_id == user_id).all()
        remaining_oauth = db.query(OAuthAccountModel).filter(OAuthAccountModel.user_id == user_id).all()

        assert len(remaining_sessions) == 0
        assert len(remaining_oauth) == 0
    finally:
        db.close()
