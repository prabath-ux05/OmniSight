"""Database base module importing all models for Alembic migrations."""

from backend.app.db.base_class import Base
from backend.app.models.run import RunModel
from backend.app.models.finding import FindingModel
from backend.app.models.artifact import ArtifactModel
from backend.app.models.repair_proposal import RepairProposalModel
from backend.app.models.user import UserModel
from backend.app.models.session import SessionModel
from backend.app.models.oauth_account import OAuthAccountModel

__all__ = [
    "Base",
    "RunModel",
    "FindingModel",
    "ArtifactModel",
    "RepairProposalModel",
    "UserModel",
    "SessionModel",
    "OAuthAccountModel",
]
