"""SQLAlchemy model for inspection runs."""

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship
from backend.app.db.base_class import Base


class RunModel(Base):
    """Database entity representing an OmniSight UI inspection run."""

    __tablename__ = "runs"

    run_id = Column(String(128), primary_key=True, index=True)
    url = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="queued", index=True)
    created_at = Column(String(64), nullable=False, index=True)
    completed_at = Column(String(64), nullable=True)
    message = Column(Text, nullable=False, default="Run created successfully and queued for inspection.")
    error = Column(Text, nullable=True)

    # Relationships
    findings = relationship("FindingModel", back_populates="run", cascade="all, delete-orphan")
    artifacts = relationship("ArtifactModel", back_populates="run", cascade="all, delete-orphan")
    repair_proposals = relationship("RepairProposalModel", back_populates="run", cascade="all, delete-orphan")
