"""Authentication and user account Pydantic schemas for OmniSight API.

Ensures strict validation, email normalization, safe name handling,
and guarantees that password hashes and session token internals are never exposed.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    """Payload for new user registration."""

    email: EmailStr = Field(
        ...,
        description="User email address (normalized to lowercase).",
        examples=["operator@omnisight.dev"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Plaintext password (minimum 8 characters, maximum 128).",
        examples=["SuperSecretPass123!"],
    )
    full_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Optional full name or display handle.",
        examples=["Jane Doe"],
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Trim whitespace and normalize email to lowercase."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("full_name", mode="before")
    @classmethod
    def clean_full_name(cls, v: Optional[str]) -> Optional[str]:
        """Trim whitespace from full_name and convert empty strings to None."""
        if isinstance(v, str):
            cleaned = v.strip()
            return cleaned if cleaned else None
        return v


class LoginRequest(BaseModel):
    """Payload for user email/password login."""

    email: EmailStr = Field(
        ...,
        description="Registered user email address.",
        examples=["operator@omnisight.dev"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Plaintext password.",
        examples=["SuperSecretPass123!"],
    )

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Trim whitespace and normalize email to lowercase."""
        if isinstance(v, str):
            return v.strip().lower()
        return v


class UserResponse(BaseModel):
    """Public representation of an authenticated user profile.

    Strictly excludes sensitive credential attributes such as password hashes
    and internal session identifiers.
    """

    id: str = Field(..., description="Unique UUID identifier for the user.")
    email: str = Field(..., description="Normalized primary email address.")
    full_name: Optional[str] = Field(None, description="User full display name.")
    avatar_url: Optional[str] = Field(None, description="Optional avatar image URL.")
    is_active: bool = Field(True, description="Whether the user account is active.")
    is_verified: bool = Field(False, description="Whether the email address has been verified.")
    created_at: datetime = Field(..., description="UTC creation timestamp.")
    updated_at: datetime = Field(..., description="UTC update timestamp.")
    linked_providers: List[str] = Field(
        default_factory=list,
        description="List of linked third-party OAuth providers (e.g. ['google', 'microsoft']).",
    )

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(UserResponse):
    """Current-user profile response payload."""
    pass


class AuthResponse(BaseModel):
    """Standardized wrapper response for successful authentication events."""

    user: UserResponse = Field(..., description="Authenticated user profile.")
    message: str = Field("Authenticated successfully.", description="Human-readable outcome message.")
