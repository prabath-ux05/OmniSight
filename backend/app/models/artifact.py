"""SQLAlchemy model for visual and DOM artifacts."""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.db.base_class import Base


class ArtifactModel(Base):
    """Database entity representing visual, DOM, or telemetry artifacts saved for a run."""

    __tablename__ = "artifacts"

    artifact_id = Column(String(128), primary_key=True, index=True)
    run_id = Column(String(128), ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    artifact_type = Column(String(64), nullable=False, index=True)
    storage_path = Column(Text, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    content_type = Column(String(64), nullable=True)
    captured_at = Column(String(64), nullable=False)

    # Relationships
    run = relationship("RunModel", back_populates="artifacts")
