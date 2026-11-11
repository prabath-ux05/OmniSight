"""OmniSight Core Security and Cryptographic Utilities.

Provides password hashing via Argon2id, cryptographically secure token generation,
SHA-256 token hashing, and RFC 7636 PKCE S256 challenge generation.
Never logs sensitive inputs such as passwords, raw session tokens, or secrets.
"""

import base64
import hashlib
import hmac
import secrets
from typing import Tuple

import argon2
from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from backend.app.core.config import settings

# Standard RFC-recommended Argon2id profile (64 MiB memory, 2 iterations, 4 parallelism)
_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    type=Type.ID,
)


def hash_password(password: str) -> str:
    """Hash a plaintext password using Argon2id with unique cryptographic salt.

    Args:
        password: Plaintext password to hash.

    Returns:
        Argon2id encoded password hash string.

    Raises:
        ValueError: If password is empty or not a string.
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password cannot be empty.")
    return _hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against an Argon2id password hash in constant time.

    Handles invalid or corrupted hashes safely without raising exceptions or
    exposing internal timing channels.

    Args:
        password: Plaintext candidate password.
        hashed_password: Stored Argon2id hash.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    if not password or not hashed_password or not isinstance(password, str) or not isinstance(hashed_password, str):
        return False

    try:
        return _hasher.verify(hashed_password, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    except Exception:
        return False


def generate_secure_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure, high-entropy URL-safe random token.

    Args:
        nbytes: Number of random bytes of entropy (default 32 bytes = 256 bits).

    Returns:
        URL-safe base64-encoded token string.
    """
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """Compute deterministic SHA-256 hex digest of a token for secure database lookup.

    Raw session tokens must never be persisted in plaintext. Only their SHA-256
    digests are stored in the database.

    Args:
        token: Raw token string.

    Returns:
        64-character lowercase hexadecimal SHA-256 digest string.
    """
    if not token or not isinstance(token, str):
        raise ValueError("Token must be a non-empty string.")
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_pkce_pair() -> Tuple[str, str]:
    """Generate an RFC 7636 compliant PKCE (Proof Key for Code Exchange) pair using S256.

    Returns:
        A tuple of (code_verifier, code_challenge):
        - code_verifier: High-entropy cryptographic random string (43-128 chars).
        - code_challenge: Base64URL-encoded SHA-256 hash of the verifier without padding.
    """
    # 64 random bytes produce an 86-character URL-safe string, satisfying RFC 7636 (43-128 chars)
    code_verifier = secrets.token_urlsafe(64)

    # Compute SHA-256 digest of the ASCII-encoded verifier
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()

    # Base64URL encode without trailing '=' padding
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    return code_verifier, code_challenge


def generate_csrf_token(session_token_hash: str) -> str:
    """Generate a cryptographically signed CSRF token bound to an active session.

    Format: <nonce>.<hmac_signature>
    HMAC binds the token to both the server-side CSRF secret and the session's SHA-256 token hash.
    Prevents cookie injection and cross-session CSRF forgery.

    Args:
        session_token_hash: 64-character SHA-256 hash of the session token.

    Returns:
        Signed, session-bound CSRF token string.
    """
    if not session_token_hash or not isinstance(session_token_hash, str):
        raise ValueError("session_token_hash must be a non-empty string.")

    nonce = secrets.token_urlsafe(16)
    message = f"{session_token_hash}:{nonce}".encode("utf-8")
    sig = hmac.new(
        settings.CSRF_SECRET_KEY.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()
    return f"{nonce}.{sig}"


def verify_csrf_token(csrf_token: str, session_token_hash: str) -> bool:
    """Verify that a CSRF token has a valid HMAC signature bound to the specific session.

    Uses constant-time comparison to protect against timing side-channels.

    Args:
        csrf_token: Incoming double-submit CSRF token string.
        session_token_hash: SHA-256 hash of the caller's active session.

    Returns:
        True if the signature is valid and cryptographically bound to the session, False otherwise.
    """
    if not csrf_token or not isinstance(csrf_token, str) or not session_token_hash:
        return False

    parts = csrf_token.strip().split(".")
    if len(parts) != 2:
        return False

    nonce, sig = parts
    if not nonce or not sig:
        return False

    message = f"{session_token_hash}:{nonce}".encode("utf-8")
    expected_sig = hmac.new(
        settings.CSRF_SECRET_KEY.encode("utf-8"),
        message,
        hashlib.sha256,
    ).hexdigest()

    return secrets.compare_digest(sig, expected_sig)
