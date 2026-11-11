"""SQLAlchemy model for user accounts."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import relationship, validates
from backend.app.db.base_class import Base


class UserModel(Base):
    """Database entity representing a registered OmniSight user."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    avatar_url = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
    oauth_accounts = relationship("OAuthAccountModel", back_populates="user", cascade="all, delete-orphan")

    @validates("email")
    def validate_and_normalize_email(self, key, address):
        """Normalize email address to trimmed lowercase before persistence."""
        if address and isinstance(address, str):
            return address.strip().lower()
        return address
