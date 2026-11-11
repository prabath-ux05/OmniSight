"""Automated test suite for OmniSight core security and cryptographic utilities."""

import base64
import hashlib
import pytest

from backend.app.core.security import (
    generate_pkce_pair,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_hash_password_produces_valid_argon2id_hash():
    """Verify that hash_password returns an Argon2id formatted hash."""
    hashed = hash_password("SuperSecret123!")
    assert isinstance(hashed, str)
    assert hashed.startswith("$argon2id$")
    assert len(hashed) > 50


def test_hash_password_salts_uniquely():
    """Verify that multiple hashes of the same password produce distinct hashes due to salts."""
    pwd = "IdenticalPassword"
    hash1 = hash_password(pwd)
    hash2 = hash_password(pwd)
    assert hash1 != hash2


def test_hash_password_rejects_empty():
    """Verify that hash_password raises ValueError for empty or invalid input."""
    with pytest.raises(ValueError, match="Password cannot be empty"):
        hash_password("")
    with pytest.raises(ValueError, match="Password cannot be empty"):
        hash_password(None)  # type: ignore


def test_verify_password_matches_correct_password():
    """Verify that verify_password confirms the exact password."""
    pwd = "ValidUserPassword#2026"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True


def test_verify_password_rejects_incorrect_password():
    """Verify that verify_password rejects an incorrect password."""
    hashed = hash_password("CorrectPassword")
    assert verify_password("WrongPassword", hashed) is False


def test_verify_password_handles_invalid_or_corrupt_hash_safely():
    """Verify that verify_password handles invalid hashes without raising unhandled exceptions."""
    assert verify_password("some_password", "invalid_hash_format") is False
    assert verify_password("some_password", "$argon2id$v=19$corrupted_payload") is False
    assert verify_password("some_password", "") is False
    assert verify_password("", "some_hash") is False
    assert verify_password(None, None) is False  # type: ignore


def test_generate_secure_token():
    """Verify that generate_secure_token returns high-entropy, unique tokens."""
    token1 = generate_secure_token()
    token2 = generate_secure_token()

    assert isinstance(token1, str)
    assert len(token1) >= 43  # 32 bytes base64url encoded is 43 chars
    assert token1 != token2


def test_hash_token_sha256_consistency():
    """Verify that hash_token computes a correct deterministic SHA-256 hex digest."""
    token = "fixed-sample-token-12345"
    expected = hashlib.sha256(token.encode("utf-8")).hexdigest()

    result = hash_token(token)
    assert result == expected
    assert len(result) == 64
    assert all(c in "0123456789abcdef" for c in result)


def test_hash_token_rejects_empty():
    """Verify that hash_token rejects empty tokens."""
    with pytest.raises(ValueError, match="Token must be a non-empty string"):
        hash_token("")
    with pytest.raises(ValueError, match="Token must be a non-empty string"):
        hash_token(None)  # type: ignore


def test_generate_pkce_pair_rfc7636_compliance():
    """Verify RFC 7636 PKCE S256 code verifier and challenge generation."""
    verifier, challenge = generate_pkce_pair()

    # Verifier length must be between 43 and 128 characters
    assert 43 <= len(verifier) <= 128

    # Challenge must be base64url(sha256(verifier)) without padding
    expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
    expected_challenge = base64.urlsafe_b64encode(expected_digest).decode("ascii").rstrip("=")

    assert challenge == expected_challenge
    assert len(challenge) == 43
    assert "=" not in challenge


def test_generate_pkce_pair_uniqueness():
    """Verify that consecutive PKCE pairs are cryptographically unique."""
    v1, c1 = generate_pkce_pair()
    v2, c2 = generate_pkce_pair()

    assert v1 != v2
    assert c1 != c2
