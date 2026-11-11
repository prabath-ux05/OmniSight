"""SQLAlchemy model for linked third-party OAuth provider accounts."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.db.base_class import Base


class OAuthAccountModel(Base):
    """Database entity representing a linked OAuth account (e.g. Google, Microsoft)."""

    __tablename__ = "oauth_accounts"
    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user_id"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(32), nullable=False, index=True)
    provider_user_id = Column(String(255), nullable=False, index=True)
    provider_email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("UserModel", back_populates="oauth_accounts")
