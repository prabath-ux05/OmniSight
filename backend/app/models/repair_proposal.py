"""SQLAlchemy model for self-healing repair proposals."""

from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from backend.app.db.base_class import Base


class RepairProposalModel(Base):
    """Database entity representing an automated self-healing repair proposal."""

    __tablename__ = "repair_proposals"

    proposal_id = Column(String(128), primary_key=True, index=True)
    run_id = Column(String(128), ForeignKey("runs.run_id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(String(128), ForeignKey("findings.finding_id", ondelete="SET NULL"), nullable=True, index=True)
    proposed_change = Column(Text, nullable=False)
    approval_status = Column(String(32), nullable=False, default="pending", index=True)
    execution_status = Column(String(32), nullable=False, default="unapplied")
    verification_status = Column(String(32), nullable=False, default="unverified")
    github_pr_url = Column(Text, nullable=True)
    github_pr_number = Column(Integer, nullable=True)
    created_at = Column(String(64), nullable=False)
    updated_at = Column(String(64), nullable=True)

    # Relationships
    run = relationship("RunModel", back_populates="repair_proposals")
    finding = relationship("FindingModel", back_populates="repair_proposals")
