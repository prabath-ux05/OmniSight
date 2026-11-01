"""Database-backed storage service for OmniSight inspection runs and findings."""

from datetime import datetime, timezone
import uuid
from sqlalchemy import delete, select
from sqlalchemy.exc import DBAPIError, OperationalError

from backend.app.core.logging import logger
from backend.app.db.session import (
    DatabaseConnectionError,
    SessionLocal,
    get_db_session,
    init_db,
)
from backend.app.models.finding import FindingModel
from backend.app.models.run import RunModel
from backend.app.schemas.findings import EvidenceReferences, FindingResponse
from backend.app.schemas.runs import RunCreateRequest, RunResponse

_UNSET = object()


class DatabaseRunStore:
    """Persistent PostgreSQL/SQLAlchemy repository managing inspection runs and defect findings."""

    def __init__(self, session_factory=None) -> None:
        self._session_factory = session_factory or SessionLocal
        # Ensure database tables exist upon store instantiation
        try:
            init_db()
        except Exception as exc:
            logger.warning("Could not auto-create database tables on startup: %s", str(exc))

    def _model_to_run_response(self, run: RunModel) -> RunResponse:
        """Convert a SQLAlchemy RunModel instance into a Pydantic RunResponse."""
        return RunResponse(
            run_id=run.run_id,
            url=run.url,
            status=run.status,
            created_at=run.created_at,
            completed_at=run.completed_at,
            message=run.message,
            error=run.error,
        )

    def _model_to_finding_response(self, finding: FindingModel) -> FindingResponse:
        """Convert a SQLAlchemy FindingModel instance into a Pydantic FindingResponse."""
        return FindingResponse(
            finding_id=finding.finding_id,
            category=finding.category,
            severity=finding.severity,
            confidence=finding.confidence if finding.confidence is not None else 1.0,
            description=finding.description,
            selector=finding.selector,
            evidence=EvidenceReferences(
                screenshot_path=finding.screenshot_path,
                dom_snapshot_path=finding.dom_snapshot_path,
            ),
            source=finding.source,
        )

    def create(self, request: RunCreateRequest) -> RunResponse:
        """Create and persist a new run in the initial 'queued' status."""
        run_id = f"run_{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()
        message = "Run created successfully and queued for inspection."

        run_obj = RunModel(
            run_id=run_id,
            url=str(request.url),
            status="queued",
            created_at=created_at,
            completed_at=None,
            message=message,
            error=None,
        )

        try:
            with get_db_session(self._session_factory) as db:
                db.add(run_obj)
                db.flush()
                response = self._model_to_run_response(run_obj)
            logger.info("Persisted new run %s to database.", run_id)
            return response
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while creating run: %s", str(exc))
            raise DatabaseConnectionError(f"Database error during run creation: {str(exc)}") from exc

    def get(self, run_id: str) -> RunResponse | None:
        """Retrieve a run from the database by its unique identifier."""
        try:
            with get_db_session(self._session_factory) as db:
                run_obj = db.get(RunModel, run_id)
                if not run_obj:
                    return None
                return self._model_to_run_response(run_obj)
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while retrieving run %s: %s", run_id, str(exc))
            raise DatabaseConnectionError(f"Database error during run retrieval: {str(exc)}") from exc

    def list_all(self) -> list[RunResponse]:
        """List all stored runs from the database ordered by creation time descending."""
        try:
            with get_db_session(self._session_factory) as db:
                stmt = select(RunModel).order_by(RunModel.created_at.desc())
                runs = db.execute(stmt).scalars().all()
                return [self._model_to_run_response(r) for r in runs]
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while listing runs: %s", str(exc))
            raise DatabaseConnectionError(f"Database error during runs listing: {str(exc)}") from exc

    def get_findings(self, run_id: str) -> list[FindingResponse] | None:
        """Retrieve findings associated with a run. Returns None if run does not exist."""
        try:
            with get_db_session(self._session_factory) as db:
                run_obj = db.get(RunModel, run_id)
                if not run_obj:
                    return None
                stmt = select(FindingModel).where(FindingModel.run_id == run_id)
                findings = db.execute(stmt).scalars().all()
                return [self._model_to_finding_response(f) for f in findings]
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while retrieving findings for run %s: %s", run_id, str(exc))
            raise DatabaseConnectionError(f"Database error during findings retrieval: {str(exc)}") from exc

    def set_findings(self, run_id: str, findings: list[FindingResponse]) -> None:
        """Set findings for a run in the database, replacing any existing findings."""
        try:
            with get_db_session(self._session_factory) as db:
                # Remove prior findings for this run
                db.execute(delete(FindingModel).where(FindingModel.run_id == run_id))

                created_at = datetime.now(timezone.utc).isoformat()
                for item in findings:
                    model = FindingModel(
                        finding_id=item.finding_id,
                        run_id=run_id,
                        category=item.category,
                        severity=item.severity,
                        description=item.description,
                        confidence=item.confidence,
                        selector=item.selector,
                        screenshot_path=item.evidence.screenshot_path if item.evidence else None,
                        dom_snapshot_path=item.evidence.dom_snapshot_path if item.evidence else None,
                        source=item.source,
                        created_at=created_at,
                    )
                    db.add(model)
            logger.info("Persisted %d findings for run %s in database.", len(findings), run_id)
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while saving findings for run %s: %s", run_id, str(exc))
            raise DatabaseConnectionError(f"Database error during findings save: {str(exc)}") from exc

    def update_run(
        self,
        run_id: str,
        *,
        status: str | None = None,
        message: str | None = None,
        error: str | None | object = _UNSET,
        completed_at: str | None | object = _UNSET,
    ) -> RunResponse | None:
        """Update mutable status, message, error, and timestamp fields of an existing run."""
        try:
            with get_db_session(self._session_factory) as db:
                run_obj = db.get(RunModel, run_id)
                if not run_obj:
                    return None

                if status is not None:
                    run_obj.status = status
                    if status in ("completed", "failed", "cancelled") and completed_at is _UNSET and not run_obj.completed_at:
                        run_obj.completed_at = datetime.now(timezone.utc).isoformat()

                if message is not None:
                    run_obj.message = message
                if error is not _UNSET:
                    run_obj.error = error
                if completed_at is not _UNSET:
                    run_obj.completed_at = completed_at

                db.flush()
                return self._model_to_run_response(run_obj)
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while updating run %s: %s", run_id, str(exc))
            raise DatabaseConnectionError(f"Database error during run update: {str(exc)}") from exc

    def clear(self) -> None:
        """Clear all stored runs, findings, and related entities (used for test isolation)."""
        try:
            with get_db_session(self._session_factory) as db:
                from backend.app.models.artifact import ArtifactModel
                from backend.app.models.repair_proposal import RepairProposalModel

                db.execute(delete(RepairProposalModel))
                db.execute(delete(ArtifactModel))
                db.execute(delete(FindingModel))
                db.execute(delete(RunModel))
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure during clear: %s", str(exc))
            raise DatabaseConnectionError(f"Database error during clear: {str(exc)}") from exc


# Alias for backward compatibility
RunStore = DatabaseRunStore

# Global database-backed repository instance
run_store = DatabaseRunStore()


def create_mock_findings(run_id: str) -> list[FindingResponse]:
    """Generate clearly labelled mock defect findings for early milestone development."""
    return [
        FindingResponse(
            finding_id=f"defect_{run_id}_001",
            category="layout_overflow",
            severity="medium",
            confidence=0.92,
            description="[MOCK] Content panel text extends beyond container boundary.",
            selector="#main-content-panel",
            evidence=EvidenceReferences(
                screenshot_path=f"artifacts/{run_id}/before.png",
                dom_snapshot_path=f"artifacts/{run_id}/dom.html",
            ),
            source="mock",
        ),
        FindingResponse(
            finding_id=f"defect_{run_id}_002",
            category="broken_image",
            severity="high",
            confidence=0.88,
            description="[MOCK] Service topology image fails to display.",
            selector="#service-topology-image",
            evidence=EvidenceReferences(
                screenshot_path=f"artifacts/{run_id}/before.png",
            ),
            source="mock",
        ),
    ]
