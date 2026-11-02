"""Database-backed storage service for OmniSight inspection runs, findings, artifacts, and repair proposals."""

from datetime import datetime, timezone
from pathlib import Path
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
from backend.app.models.artifact import ArtifactModel
from backend.app.models.finding import FindingModel
from backend.app.models.repair_proposal import RepairProposalModel
from backend.app.models.run import RunModel
from backend.app.schemas.artifacts import ArtifactResponse
from backend.app.schemas.findings import EvidenceReferences, FindingResponse
from backend.app.schemas.proposals import RepairProposalCreateRequest, RepairProposalResponse
from backend.app.schemas.runs import RunCreateRequest, RunResponse

_UNSET = object()


class ProposalConflictError(Exception):
    """Raised when an approval decision conflicts with the current proposal lifecycle state."""
    pass


class DatabaseRunStore:
    """Persistent PostgreSQL/SQLAlchemy repository managing runs, findings, artifacts, and proposals."""

    def __init__(self, session_factory=None) -> None:
        self._session_factory = session_factory or SessionLocal
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

    def _model_to_artifact_response(self, art: ArtifactModel) -> ArtifactResponse:
        """Convert a SQLAlchemy ArtifactModel instance into a Pydantic ArtifactResponse."""
        filename = Path(art.storage_path).name
        download_url = f"/api/v1/artifacts/{art.run_id}/{filename}"
        return ArtifactResponse(
            artifact_id=art.artifact_id,
            run_id=art.run_id,
            artifact_type=art.artifact_type,
            storage_path=art.storage_path,
            file_size_bytes=art.file_size_bytes,
            content_type=art.content_type,
            captured_at=art.captured_at,
            download_url=download_url,
        )

    def _model_to_proposal_response(self, prop: RepairProposalModel) -> RepairProposalResponse:
        """Convert a SQLAlchemy RepairProposalModel instance into a Pydantic RepairProposalResponse."""
        return RepairProposalResponse(
            proposal_id=prop.proposal_id,
            run_id=prop.run_id,
            finding_id=prop.finding_id,
            proposed_change=prop.proposed_change,
            approval_status=prop.approval_status,
            execution_status=prop.execution_status,
            verification_status=prop.verification_status,
            github_pr_url=prop.github_pr_url,
            github_pr_number=prop.github_pr_number,
            created_at=prop.created_at,
            updated_at=prop.updated_at,
        )

    # =========================================================================
    # Run Lifecycle Management
    # =========================================================================

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

    # =========================================================================
    # Findings Management
    # =========================================================================

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

    # =========================================================================
    # Artifact Management (Day 3)
    # =========================================================================

    def record_artifact(
        self,
        run_id: str,
        artifact_type: str,
        storage_path: str,
        file_size_bytes: int | None = None,
        content_type: str | None = None,
        captured_at: str | None = None,
    ) -> ArtifactResponse:
        """Save artifact metadata in the database associated with an inspection run."""
        clean_path = str(Path(storage_path).as_posix())
        path_obj = Path(storage_path)

        if file_size_bytes is None and path_obj.is_file():
            try:
                file_size_bytes = path_obj.stat().st_size
            except Exception:
                file_size_bytes = None

        if content_type is None:
            if clean_path.lower().endswith(".png"):
                content_type = "image/png"
            elif clean_path.lower().endswith((".html", ".htm")):
                content_type = "text/html"
            elif clean_path.lower().endswith(".json"):
                content_type = "application/json"
            else:
                content_type = "application/octet-stream"

        timestamp = captured_at or datetime.now(timezone.utc).isoformat()
        artifact_id = f"art_{run_id}_{artifact_type}_{uuid.uuid4().hex[:6]}"

        artifact_obj = ArtifactModel(
            artifact_id=artifact_id,
            run_id=run_id,
            artifact_type=artifact_type,
            storage_path=clean_path,
            file_size_bytes=file_size_bytes,
            content_type=content_type,
            captured_at=timestamp,
        )

        try:
            with get_db_session(self._session_factory) as db:
                run_obj = db.get(RunModel, run_id)
                if not run_obj:
                    raise ValueError(f"Cannot record artifact: run '{run_id}' not found.")
                db.add(artifact_obj)
                db.flush()
                response = self._model_to_artifact_response(artifact_obj)
            logger.info("Recorded %s artifact %s for run %s in database.", artifact_type, artifact_id, run_id)
            return response
        except ValueError:
            raise
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while recording artifact for run %s: %s", run_id, str(exc))
            raise DatabaseConnectionError(f"Database error during artifact recording: {str(exc)}") from exc

    def get_artifacts(self, run_id: str) -> list[ArtifactResponse] | None:
        """Retrieve all recorded artifacts for an inspection run. Returns None if run does not exist."""
        try:
            with get_db_session(self._session_factory) as db:
                run_obj = db.get(RunModel, run_id)
                if not run_obj:
                    return None
                stmt = select(ArtifactModel).where(ArtifactModel.run_id == run_id)
                artifacts = db.execute(stmt).scalars().all()
                return [self._model_to_artifact_response(a) for a in artifacts]
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while retrieving artifacts for run %s: %s", run_id, str(exc))
            raise DatabaseConnectionError(f"Database error during artifacts retrieval: {str(exc)}") from exc

    def get_artifact_by_type(self, run_id: str, artifact_type: str) -> ArtifactResponse | None:
        """Retrieve the latest artifact of a specific type for an inspection run."""
        try:
            with get_db_session(self._session_factory) as db:
                stmt = (
                    select(ArtifactModel)
                    .where(ArtifactModel.run_id == run_id, ArtifactModel.artifact_type == artifact_type)
                    .order_by(ArtifactModel.captured_at.desc())
                )
                artifact = db.execute(stmt).scalars().first()
                if not artifact:
                    return None
                return self._model_to_artifact_response(artifact)
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while retrieving %s artifact for run %s: %s", artifact_type, run_id, str(exc))
            raise DatabaseConnectionError(f"Database error during artifact lookup: {str(exc)}") from exc

    # =========================================================================
    # Repair Proposals Management (Day 3)
    # =========================================================================

    def create_proposal(self, run_id: str, request: RepairProposalCreateRequest) -> RepairProposalResponse:
        """Create and persist a new repair proposal in initial 'pending' review status."""
        proposal_id = f"prop_{run_id}_{uuid.uuid4().hex[:6]}"
        created_at = datetime.now(timezone.utc).isoformat()

        proposal_obj = RepairProposalModel(
            proposal_id=proposal_id,
            run_id=run_id,
            finding_id=request.finding_id,
            proposed_change=request.proposed_change,
            approval_status="pending",
            execution_status="unapplied",
            verification_status="unverified",
            github_pr_url=request.github_pr_url,
            github_pr_number=request.github_pr_number,
            created_at=created_at,
            updated_at=None,
        )

        try:
            with get_db_session(self._session_factory) as db:
                run_obj = db.get(RunModel, run_id)
                if not run_obj:
                    raise ValueError(f"Cannot create proposal: run '{run_id}' not found.")
                db.add(proposal_obj)
                db.flush()
                response = self._model_to_proposal_response(proposal_obj)
            logger.info("Persisted repair proposal %s for run %s in database.", proposal_id, run_id)
            return response
        except ValueError:
            raise
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while creating proposal for run %s: %s", run_id, str(exc))
            raise DatabaseConnectionError(f"Database error during proposal creation: {str(exc)}") from exc

    def get_proposal(self, proposal_id: str) -> RepairProposalResponse | None:
        """Retrieve a single repair proposal by proposal_id."""
        try:
            with get_db_session(self._session_factory) as db:
                prop = db.get(RepairProposalModel, proposal_id)
                if not prop:
                    return None
                return self._model_to_proposal_response(prop)
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while retrieving proposal %s: %s", proposal_id, str(exc))
            raise DatabaseConnectionError(f"Database error during proposal retrieval: {str(exc)}") from exc

    def list_proposals(self, run_id: str, finding_id: str | None = None) -> list[RepairProposalResponse] | None:
        """List proposals associated with a run (optionally filtered by finding_id). Returns None if run not found."""
        try:
            with get_db_session(self._session_factory) as db:
                run_obj = db.get(RunModel, run_id)
                if not run_obj:
                    return None
                stmt = select(RepairProposalModel).where(RepairProposalModel.run_id == run_id)
                if finding_id:
                    stmt = stmt.where(RepairProposalModel.finding_id == finding_id)
                stmt = stmt.order_by(RepairProposalModel.created_at.desc())
                proposals = db.execute(stmt).scalars().all()
                return [self._model_to_proposal_response(p) for p in proposals]
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while listing proposals for run %s: %s", run_id, str(exc))
            raise DatabaseConnectionError(f"Database error during proposals listing: {str(exc)}") from exc

    def update_proposal_approval(self, proposal_id: str, decision: str, notes: str | None = None) -> RepairProposalResponse | None:
        """Record an approval or rejection decision on a proposal with strict state validation."""
        if decision not in ("approved", "rejected"):
            raise ValueError(f"Invalid approval decision '{decision}'. Must be 'approved' or 'rejected'.")

        try:
            with get_db_session(self._session_factory) as db:
                prop = db.get(RepairProposalModel, proposal_id)
                if not prop:
                    return None

                # Guard against duplicate or conflicting decisions
                if prop.approval_status == decision:
                    raise ProposalConflictError(f"Proposal '{proposal_id}' is already {decision}.")
                if prop.approval_status == "approved" and decision == "rejected":
                    raise ProposalConflictError(f"Proposal '{proposal_id}' is already approved and cannot be rejected.")
                if prop.approval_status == "rejected" and decision == "approved":
                    raise ProposalConflictError(f"Proposal '{proposal_id}' has already been rejected and cannot be approved.")

                prop.approval_status = decision
                prop.updated_at = datetime.now(timezone.utc).isoformat()
                db.flush()
                response = self._model_to_proposal_response(prop)
            logger.info("Updated proposal %s approval status to '%s'.", proposal_id, decision)
            return response
        except (ValueError, ProposalConflictError):
            raise
        except (OperationalError, DBAPIError) as exc:
            logger.error("Database connection failure while updating approval for %s: %s", proposal_id, str(exc))
            raise DatabaseConnectionError(f"Database error during proposal approval update: {str(exc)}") from exc

    def clear(self) -> None:
        """Clear all stored runs, findings, artifacts, and proposals (used for test isolation)."""
        try:
            with get_db_session(self._session_factory) as db:
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
