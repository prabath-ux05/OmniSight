"""Focused tests for Alembic database migrations and dependency integrity.

Validates:
1. ReportLab dependency availability and requirements.txt declaration.
2. Alembic migration DAG continuity across revisions 001 -> 002 -> 003 -> 004.
3. Safe handling and escaping of percent-encoded characters (e.g. %40) in database URLs for Alembic ConfigParser.
4. Isolated SQLite lifecycle validation for migration 004 (upgrade, downgrade, re-upgrade)
   starting from a pre-003 schema state, without constraint no-op monkeypatches.
5. Complete migration chain (001 -> 002 -> 003 -> 004) validation against an explicitly
   configured, isolated PostgreSQL test database (with strict production isolation and clean skip).
"""

import os
from pathlib import Path
import tempfile
import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text


def test_reportlab_dependency_available():
    """Verify that reportlab is installed and can be imported at module level."""
    import reportlab
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate

    assert reportlab.__version__ is not None
    assert letter is not None
    assert SimpleDocTemplate is not None


def test_requirements_file_declares_reportlab():
    """Verify that requirements.txt declares reportlab with compatible version."""
    req_path = Path(__file__).resolve().parent.parent.parent / "requirements.txt"
    assert req_path.is_file(), "requirements.txt must exist"
    content = req_path.read_text(encoding="utf-8")
    assert "reportlab>=" in content, "requirements.txt must include reportlab"


def test_alembic_migration_files_and_dag_integrity():
    """Verify that Alembic migrations 001 -> 002 -> 003 -> 004 form an unbroken contiguous DAG."""
    root_dir = Path(__file__).resolve().parent.parent.parent
    alembic_ini_path = root_dir / "alembic.ini"
    assert alembic_ini_path.is_file(), "alembic.ini must exist"

    cfg = Config(str(alembic_ini_path))
    cfg.set_main_option("script_location", str(root_dir / "alembic"))
    script_dir = ScriptDirectory.from_config(cfg)

    # Walk the revision tree from head back to base
    head_rev = script_dir.get_current_head()
    assert head_rev == "004_add_finding_viewport", f"Expected head revision to be '004_add_finding_viewport', got '{head_rev}'"

    rev_004 = script_dir.get_revision("004_add_finding_viewport")
    assert rev_004 is not None
    assert rev_004.down_revision == "003_add_run_user_id"

    rev_003 = script_dir.get_revision("003_add_run_user_id")
    assert rev_003 is not None
    assert rev_003.down_revision == "002_add_auth_tables"

    rev_002 = script_dir.get_revision("002_add_auth_tables")
    assert rev_002 is not None
    assert rev_002.down_revision == "001_initial_tables"

    rev_001 = script_dir.get_revision("001_initial_tables")
    assert rev_001 is not None
    assert rev_001.down_revision is None


def test_alembic_config_escapes_percent_encoded_url():
    """Verify that percent signs in database URLs (e.g. %40 in passwords) are safely escaped for ConfigParser.

    ConfigParser treats '%' as interpolation syntax, raising ValueError: invalid interpolation syntax.
    Escaping '%' -> '%%' allows Config.set_main_option to succeed, while Config.get_main_option
    un-interpolates '%%' back to '%', delivering the exact original encoded URL to SQLAlchemy.
    """
    root_dir = Path(__file__).resolve().parent.parent.parent
    alembic_ini_path = root_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))

    raw_url = "postgresql+psycopg2://test_user:p%40ss%25word%21@localhost:5433/omnisight_test"
    escaped_url = raw_url.replace("%", "%%")

    # set_main_option must not raise ValueError: invalid interpolation syntax
    alembic_cfg.set_main_option("sqlalchemy.url", escaped_url)

    # get_main_option un-interpolates '%%' back to single '%'
    resolved_url = alembic_cfg.get_main_option("sqlalchemy.url")
    assert resolved_url == raw_url
    assert "%40" in resolved_url
    assert "%25" in resolved_url

    # SQLAlchemy parses the resolved URL into the expected unquoted credentials
    engine = create_engine(resolved_url)
    assert engine.url.username == "test_user"
    assert engine.url.password == "p@ss%word!"
    assert engine.url.host == "localhost"
    assert engine.url.port == 5433
    assert engine.url.database == "omnisight_test"


def test_alembic_sqlite_migration_004_lifecycle(monkeypatch):
    """Test migration 004 upgrade, downgrade, and re-upgrade on an isolated SQLite database.

    Builds an isolated temporary SQLite schema representing the database state after
    migration 003 (with runs.user_id present, but findings.viewport not yet added).
    Tests migration 004 lifecycle without any SQLite constraint monkeypatches.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp_db_path = tmp_file.name

    test_db_url = f"sqlite:///{Path(tmp_db_path).resolve().as_posix()}"

    # Set test environment to point to this temporary database
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("TEST_DATABASE_URL", test_db_url)

    root_dir = Path(__file__).resolve().parent.parent.parent
    alembic_ini_path = root_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(root_dir / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url.replace("%", "%%"))

    eng = create_engine(test_db_url)

    try:
        # 1. Initialize schema representing post-003 state
        with eng.connect() as conn:
            raw_conn = conn.connection
            raw_conn.executescript("""
                CREATE TABLE alembic_version (
                    version_num VARCHAR(32) NOT NULL PRIMARY KEY
                );
                INSERT INTO alembic_version (version_num) VALUES ('003_add_run_user_id');

                CREATE TABLE users (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    hashed_password VARCHAR(255),
                    full_name VARCHAR(255),
                    avatar_url TEXT,
                    is_active BOOLEAN DEFAULT 1 NOT NULL,
                    is_verified BOOLEAN DEFAULT 0 NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                );
                CREATE INDEX ix_users_id ON users (id);
                CREATE UNIQUE INDEX ix_users_email ON users (email);

                CREATE TABLE sessions (
                    id VARCHAR(36) NOT NULL PRIMARY KEY,
                    user_id VARCHAR(36) NOT NULL,
                    session_token_hash VARCHAR(64) NOT NULL,
                    user_agent TEXT,
                    ip_address VARCHAR(45),
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_active_at TIMESTAMP NOT NULL
                );
                CREATE INDEX ix_sessions_id ON sessions (id);
                CREATE INDEX ix_sessions_user_id ON sessions (user_id);
                CREATE UNIQUE INDEX ix_sessions_session_token_hash ON sessions (session_token_hash);
                CREATE INDEX ix_sessions_expires_at ON sessions (expires_at);

                CREATE TABLE runs (
                    run_id VARCHAR(128) NOT NULL PRIMARY KEY,
                    user_id VARCHAR(36),
                    url TEXT NOT NULL,
                    status VARCHAR(32) DEFAULT 'queued' NOT NULL,
                    created_at VARCHAR(64) NOT NULL,
                    completed_at VARCHAR(64),
                    message TEXT DEFAULT 'Run created' NOT NULL,
                    error TEXT
                );
                CREATE INDEX ix_runs_run_id ON runs (run_id);
                CREATE INDEX ix_runs_status ON runs (status);
                CREATE INDEX ix_runs_created_at ON runs (created_at);
                CREATE INDEX ix_runs_user_id ON runs (user_id);

                CREATE TABLE findings (
                    finding_id VARCHAR(128) NOT NULL PRIMARY KEY,
                    run_id VARCHAR(128) NOT NULL,
                    category VARCHAR(64) NOT NULL,
                    severity VARCHAR(32) NOT NULL,
                    description TEXT NOT NULL,
                    confidence FLOAT,
                    selector TEXT,
                    screenshot_path TEXT,
                    dom_snapshot_path TEXT,
                    source VARCHAR(32) DEFAULT 'mock' NOT NULL,
                    created_at VARCHAR(64) NOT NULL
                );
                CREATE INDEX ix_findings_finding_id ON findings (finding_id);
                CREATE INDEX ix_findings_run_id ON findings (run_id);
                CREATE INDEX ix_findings_category ON findings (category);
                CREATE INDEX ix_findings_severity ON findings (severity);

                CREATE TABLE artifacts (
                    artifact_id VARCHAR(128) NOT NULL PRIMARY KEY,
                    run_id VARCHAR(128) NOT NULL,
                    artifact_type VARCHAR(64) NOT NULL,
                    storage_path TEXT NOT NULL,
                    file_size_bytes INTEGER,
                    content_type VARCHAR(64),
                    captured_at VARCHAR(64) NOT NULL
                );
                CREATE INDEX ix_artifacts_artifact_id ON artifacts (artifact_id);
                CREATE INDEX ix_artifacts_run_id ON artifacts (run_id);
                CREATE INDEX ix_artifacts_artifact_type ON artifacts (artifact_type);

                CREATE TABLE repair_proposals (
                    proposal_id VARCHAR(128) NOT NULL PRIMARY KEY,
                    run_id VARCHAR(128) NOT NULL,
                    finding_id VARCHAR(128),
                    proposed_change TEXT NOT NULL,
                    approval_status VARCHAR(32) DEFAULT 'pending' NOT NULL,
                    execution_status VARCHAR(32) DEFAULT 'unapplied' NOT NULL,
                    verification_status VARCHAR(32) DEFAULT 'unverified' NOT NULL,
                    github_pr_url TEXT,
                    github_pr_number INTEGER,
                    created_at VARCHAR(64) NOT NULL,
                    updated_at VARCHAR(64)
                );
                CREATE INDEX ix_repair_proposals_proposal_id ON repair_proposals (proposal_id);
                CREATE INDEX ix_repair_proposals_run_id ON repair_proposals (run_id);
                CREATE INDEX ix_repair_proposals_finding_id ON repair_proposals (finding_id);
                CREATE INDEX ix_repair_proposals_approval_status ON repair_proposals (approval_status);
            """)

        # Verify initial pre-004 state: viewport column does not exist yet
        inspector = inspect(eng)
        initial_cols = {col["name"]: col for col in inspector.get_columns("findings")}
        assert "viewport" not in initial_cols, "findings table must NOT have viewport column prior to migration 004"

        # 2. Upgrade to head (applies 004_add_finding_viewport)
        command.upgrade(alembic_cfg, "head")

        inspector = inspect(eng)
        upgraded_cols = {col["name"]: col for col in inspector.get_columns("findings")}
        assert "viewport" in upgraded_cols, "findings table must have viewport column after migration 004 upgrade"
        assert upgraded_cols["viewport"]["nullable"] is True

        indexes = [idx["name"] for idx in inspector.get_indexes("findings")]
        assert "ix_findings_viewport" in indexes, "findings table must have ix_findings_viewport index"

        # 3. Downgrade back to 003_add_run_user_id
        command.downgrade(alembic_cfg, "003_add_run_user_id")

        inspector = inspect(eng)
        downgraded_cols = {col["name"]: col for col in inspector.get_columns("findings")}
        assert "viewport" not in downgraded_cols, "viewport column must be dropped after downgrade to 003"
        downgraded_indexes = [idx["name"] for idx in inspector.get_indexes("findings")]
        assert "ix_findings_viewport" not in downgraded_indexes, "ix_findings_viewport index must be dropped"

        # 4. Re-upgrade to head (idempotent re-application of 004)
        command.upgrade(alembic_cfg, "head")

        inspector = inspect(eng)
        reupgraded_cols = {col["name"]: col for col in inspector.get_columns("findings")}
        assert "viewport" in reupgraded_cols, "viewport column must be restored after re-upgrade to head"
        reupgraded_indexes = [idx["name"] for idx in inspector.get_indexes("findings")]
        assert "ix_findings_viewport" in reupgraded_indexes, "ix_findings_viewport index must be restored"

    finally:
        eng.dispose()
        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except OSError:
                pass


def test_alembic_postgres_migration_chain(monkeypatch):
    """Test the complete migration chain 001 -> 002 -> 003 -> 004 against an isolated PostgreSQL database.

    Strict Safety Guard:
    - Never uses production DATABASE_URL or production-like connection strings.
    - Explicitly skips when no dedicated, isolated PostgreSQL test database is configured.
    """
    # Look ONLY for an explicitly designated test PostgreSQL URL
    raw_test_pg_url = os.getenv("TEST_POSTGRES_DATABASE_URL")

    # If TEST_DATABASE_URL is explicitly set to PostgreSQL (and not SQLite), inspect it
    if not raw_test_pg_url:
        env_test_db = os.getenv("TEST_DATABASE_URL", "")
        if env_test_db.startswith(("postgresql://", "postgresql+psycopg2://", "postgres://")):
            raw_test_pg_url = env_test_db

    if not raw_test_pg_url:
        pytest.skip(
            "Skipped PostgreSQL migration chain test: No dedicated isolated PostgreSQL test database configured. "
            "Set TEST_POSTGRES_DATABASE_URL to enable full PostgreSQL migration chain testing."
        )

    # Enforce strict isolation: prevent accidental execution against production or Render hosts
    lowered_url = raw_test_pg_url.lower()
    if (
        "onrender.com" in lowered_url
        or "render.com" in lowered_url
        or os.getenv("APP_ENV", "").lower() == "production"
    ):
        pytest.fail(
            "Security block: Refusing to run destructive migration tests against a production or Render-hosted database."
        )

    # Normalize url dialect if needed
    if raw_test_pg_url.startswith("postgres://"):
        pg_url = raw_test_pg_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif raw_test_pg_url.startswith("postgresql://") and "+psycopg2" not in raw_test_pg_url:
        pg_url = raw_test_pg_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    else:
        pg_url = raw_test_pg_url

    # Check connection health to the isolated test database
    try:
        eng = create_engine(pg_url, connect_args={"connect_timeout": 3})
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        pytest.skip(f"Configured PostgreSQL test database is currently unreachable: {exc}")

    # Set up test environment
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("TEST_DATABASE_URL", pg_url)

    root_dir = Path(__file__).resolve().parent.parent.parent
    alembic_ini_path = root_dir / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(root_dir / "alembic"))
    # Escape % -> %% for ConfigParser interpolation so percent-encoded credentials (e.g. %40) are preserved
    alembic_cfg.set_main_option("sqlalchemy.url", pg_url.replace("%", "%%"))

    try:
        # Run downgrade to base to start from clean state
        command.downgrade(alembic_cfg, "base")

        # 1. Run complete upgrade from 001 to head (001 -> 002 -> 003 -> 004)
        command.upgrade(alembic_cfg, "head")

        inspector = inspect(eng)
        tables = set(inspector.get_table_names())
        assert "runs" in tables
        assert "findings" in tables
        assert "artifacts" in tables
        assert "repair_proposals" in tables
        assert "users" in tables
        assert "sessions" in tables
        assert "oauth_accounts" in tables

        # Verify runs.user_id from 003
        run_cols = {col["name"]: col for col in inspector.get_columns("runs")}
        assert "user_id" in run_cols

        # Verify findings.viewport from 004
        finding_cols = {col["name"]: col for col in inspector.get_columns("findings")}
        assert "viewport" in finding_cols
        finding_indexes = [idx["name"] for idx in inspector.get_indexes("findings")]
        assert "ix_findings_viewport" in finding_indexes

        # 2. Test downgrade of 004 back to 003
        command.downgrade(alembic_cfg, "003_add_run_user_id")
        inspector = inspect(eng)
        cols_after_downgrade = {col["name"]: col for col in inspector.get_columns("findings")}
        assert "viewport" not in cols_after_downgrade

        # 3. Test re-upgrade to head
        command.upgrade(alembic_cfg, "head")
        inspector = inspect(eng)
        cols_after_reupgrade = {col["name"]: col for col in inspector.get_columns("findings")}
        assert "viewport" in cols_after_reupgrade

    finally:
        eng.dispose()
