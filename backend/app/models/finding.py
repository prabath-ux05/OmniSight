"""SQLAlchemy model for detected UI defect findings."""

from sqlalchemy import Column, Float, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from backend.app.db.base_class import Base


class FindingModel(Base):
    """Database entity representing a UI defect finding detected during an inspection."""

    __tablename__ = "findings"

    finding_id = Column(String(128), primary_key=True, index=True)
    run_id = Column(String(128), ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)
    description = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    selector = Column(Text, nullable=True)
    screenshot_path = Column(Text, nullable=True)
    dom_snapshot_path = Column(Text, nullable=True)
    source = Column(String(32), nullable=False, default="mock")
    created_at = Column(String(64), nullable=False)

    # Relationships
    run = relationship("RunModel", back_populates="findings")
    repair_proposals = relationship("RepairProposalModel", back_populates="finding")
