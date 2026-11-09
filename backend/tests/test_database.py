"""Comprehensive tests for OmniSight PostgreSQL/SQLAlchemy database models and persistence."""

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from backend.app.db.session import (
    DatabaseConnectionError,
    check_db_connection,
    engine,
    get_db_session,
)
from backend.app.models.artifact import ArtifactModel
from backend.app.models.finding import FindingModel
from backend.app.models.repair_proposal import RepairProposalModel
from backend.app.models.run import RunModel
from backend.app.schemas.runs import RunCreateRequest
from backend.app.services.run_store import DatabaseRunStore, create_mock_findings, run_store


# =============================================================================
# Schema and Table Existence Tests
# =============================================================================

def test_database_tables_created_and_indexed():
    """Verify that all four required tables are created in the database with expected columns."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()

    assert "runs" in table_names, "Expected 'runs' table to exist."
    assert "findings" in table_names, "Expected 'findings' table to exist."
    assert "artifacts" in table_names, "Expected 'artifacts' table to exist."
    assert "repair_proposals" in table_names, "Expected 'repair_proposals' table to exist."

    # Verify runs table columns
    run_columns = {col["name"]: col for col in inspector.get_columns("runs")}
    assert "run_id" in run_columns
    assert "url" in run_columns
    assert "status" in run_columns
    assert "created_at" in run_columns
    assert "completed_at" in run_columns
    assert "message" in run_columns
    assert "error" in run_columns

    # Verify findings table columns
    finding_columns = {col["name"]: col for col in inspector.get_columns("findings")}
    assert "finding_id" in finding_columns
    assert "run_id" in finding_columns
    assert "category" in finding_columns
    assert "severity" in finding_columns
    assert "description" in finding_columns
    assert "confidence" in finding_columns
    assert "selector" in finding_columns


# =============================================================================
# Run CRUD and Persistence Tests
# =============================================================================

def test_database_run_creation_and_persistence():
    """Verify creating a run saves it to the database with initial status 'queued'."""
    request = RunCreateRequest(url="https://example.com/checkout")
    created = run_store.create(request)

    assert created.run_id.startswith("run_")
    assert created.status == "queued"
    assert created.url == "https://example.com/checkout"
    assert created.completed_at is None

    # Directly verify in database via fresh session
    with get_db_session() as db:
        row = db.get(RunModel, created.run_id)
        assert row is not None
        assert row.run_id == created.run_id
        assert row.url == "https://example.com/checkout"
        assert row.status == "queued"


def test_database_run_retrieval():
    """Verify retrieving a run fetches accurate data from the database."""
    request = RunCreateRequest(url="https://example.com/dashboard")
    created = run_store.create(request)

    retrieved = run_store.get(created.run_id)
    assert retrieved is not None
    assert retrieved.run_id == created.run_id
    assert retrieved.url == created.url
    assert retrieved.status == "queued"


def test_database_run_status_update_and_completed_at():
    """Verify updating run status persists in DB and stamps completed_at on terminal states."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    assert run.completed_at is None

    # Intermediate update
    updated_capturing = run_store.update_run(run.run_id, status="capturing", message="Capturing browser")
    assert updated_capturing.status == "capturing"
    assert updated_capturing.completed_at is None

    # Terminal update: completed
    updated_completed = run_store.update_run(run.run_id, status="completed", message="Complete")
    assert updated_completed.status == "completed"
    assert updated_completed.completed_at is not None
    assert "T" in updated_completed.completed_at

    # Verify persistence in database
    with get_db_session() as db:
        row = db.get(RunModel, run.run_id)
        assert row.status == "completed"
        assert row.completed_at == updated_completed.completed_at


def test_database_run_error_clearing():
    """Verify setting error=None in update_run clears any previously recorded error."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    run_store.update_run(run.run_id, error="Transient network error")

    with get_db_session() as db:
        assert db.get(RunModel, run.run_id).error == "Transient network error"

    cleared = run_store.update_run(run.run_id, error=None)
    assert cleared.error is None

    with get_db_session() as db:
        assert db.get(RunModel, run.run_id).error is None


# =============================================================================
# Findings and Relationships Tests
# =============================================================================

def test_database_finding_persistence_and_association():
    """Verify findings are persisted and properly linked to the run in the database."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    mock_findings = create_mock_findings(run.run_id)

    run_store.set_findings(run.run_id, mock_findings)
    retrieved_findings = run_store.get_findings(run.run_id)

    assert retrieved_findings is not None
    assert len(retrieved_findings) == 2
    assert retrieved_findings[0].finding_id == mock_findings[0].finding_id

    # Verify foreign key association in database
    with get_db_session() as db:
        rows = db.query(FindingModel).filter(FindingModel.run_id == run.run_id).all()
        assert len(rows) == 2
        for r in rows:
            assert r.run_id == run.run_id


def test_database_cascade_deletion():
    """Verify deleting a run cascades and removes associated findings."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    mock_findings = create_mock_findings(run.run_id)
    run_store.set_findings(run.run_id, mock_findings)

    with get_db_session() as db:
        run_row = db.get(RunModel, run.run_id)
        db.delete(run_row)

    with get_db_session() as db:
        remaining_findings = db.query(FindingModel).filter(FindingModel.run_id == run.run_id).all()
        assert len(remaining_findings) == 0


# =============================================================================
# Artifact and Repair Proposal Models Tests
# =============================================================================

def test_database_artifact_model_persistence():
    """Verify ArtifactModel can be saved and queried with proper run relationship."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))

    with get_db_session() as db:
        artifact = ArtifactModel(
            artifact_id=f"art_{run.run_id}_01",
            run_id=run.run_id,
            artifact_type="screenshot",
            storage_path=f"artifacts/{run.run_id}/before.png",
            file_size_bytes=10240,
            content_type="image/png",
            captured_at="2026-11-01T18:00:00Z",
        )
        db.add(artifact)

    with get_db_session() as db:
        saved = db.get(ArtifactModel, f"art_{run.run_id}_01")
        assert saved is not None
        assert saved.artifact_type == "screenshot"
        assert saved.run.run_id == run.run_id


def test_database_repair_proposal_model_persistence():
    """Verify RepairProposalModel can be saved with link to run and finding."""
    run = run_store.create(RunCreateRequest(url="https://example.com/"))
    mock_findings = create_mock_findings(run.run_id)
    run_store.set_findings(run.run_id, mock_findings)

    with get_db_session() as db:
        proposal = RepairProposalModel(
            proposal_id=f"prop_{run.run_id}_01",
            run_id=run.run_id,
            finding_id=mock_findings[0].finding_id,
            proposed_change="Update CSS overflow-x to hidden on container",
            approval_status="pending",
            execution_status="unapplied",
            verification_status="unverified",
            github_pr_url="https://github.com/prabath-ux05/OmniSight/pull/42",
            github_pr_number=42,
            created_at="2026-11-01T18:00:00Z",
        )
        db.add(proposal)

    with get_db_session() as db:
        saved = db.get(RepairProposalModel, f"prop_{run.run_id}_01")
        assert saved is not None
        assert saved.approval_status == "pending"
        assert saved.github_pr_number == 42
        assert saved.run.run_id == run.run_id
        assert saved.finding.finding_id == mock_findings[0].finding_id


# =============================================================================
# Unknown Run IDs and Persistence Across Restart
# =============================================================================

def test_database_unknown_run_handling():
    """Verify that unknown run_id lookups cleanly return None without errors."""
    assert run_store.get("run_nonexistent_xyz") is None
    assert run_store.get_findings("run_nonexistent_xyz") is None
    assert run_store.update_run("run_nonexistent_xyz", status="completed") is None


def test_database_persistence_across_simulated_backend_restart(tmp_path):
    """Verify data remains fully accessible after simulating a backend process restart."""
    db_file = tmp_path / "restart_test.db"
    restart_db_url = f"sqlite:///{db_file}"

    restart_engine = create_engine(restart_db_url, connect_args={"check_same_thread": False})
    from backend.app.db.base import Base
    Base.metadata.create_all(bind=restart_engine)

    Session1 = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=restart_engine)
    store1 = DatabaseRunStore(session_factory=Session1)

    # 1. Store data before "shutdown"
    run = store1.create(RunCreateRequest(url="https://example.com/persistent"))
    store1.set_findings(run.run_id, create_mock_findings(run.run_id))
    store1.update_run(run.run_id, status="completed")

    # 2. Simulate complete process restart (dispose old engine, create brand-new engine and store instance)
    restart_engine.dispose()

    reopened_engine = create_engine(restart_db_url, connect_args={"check_same_thread": False})
    Session2 = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=reopened_engine)
    store2 = DatabaseRunStore(session_factory=Session2)

    # 3. Verify data is still present after restart
    reopened_run = store2.get(run.run_id)
    assert reopened_run is not None
    assert reopened_run.run_id == run.run_id
    assert reopened_run.status == "completed"
    assert reopened_run.completed_at is not None

    reopened_findings = store2.get_findings(run.run_id)
    assert reopened_findings is not None
    assert len(reopened_findings) == 2

    reopened_engine.dispose()


# =============================================================================
# Connection Failure Handling Tests
# =============================================================================

def test_database_connection_failure_raises_clean_error():
    """Verify that connection failure raises DatabaseConnectionError and does not fall back to RAM."""
    # Use invalid host/port that will immediately refuse connection
    failing_engine = create_engine(
        "postgresql+psycopg2://invalid_user:invalid_pass@127.0.0.1:59999/nonexistent_db",
        connect_args={"connect_timeout": 1},
    )

    # check_db_connection should gracefully return False
    assert check_db_connection(failing_engine) is False

    FailingSession = sessionmaker(bind=failing_engine)
    broken_store = DatabaseRunStore(session_factory=FailingSession)

    # Store operations should raise DatabaseConnectionError and not silently succeed
    with pytest.raises(DatabaseConnectionError):
        broken_store.create(RunCreateRequest(url="https://example.com/"))

    with pytest.raises(DatabaseConnectionError):
        broken_store.get("run_any_id")
