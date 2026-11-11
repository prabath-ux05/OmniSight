"""SQLAlchemy model for authenticated user sessions."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from backend.app.db.base_class import Base


class SessionModel(Base):
    """Database entity representing an active user login session.

    Session tokens are stored exclusively as SHA-256 hashes.
    Raw tokens are never persisted in the database.
    """

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token_hash = Column(String(64), unique=True, index=True, nullable=False)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_active_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("UserModel", back_populates="sessions")
