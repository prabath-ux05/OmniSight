# PostgreSQL Database Integration Guide & Architecture

This document outlines the PostgreSQL database setup, configuration, and architecture for the OmniSight platform.

---

## 1. Overview

OmniSight uses **PostgreSQL** as its primary production relational database, managed through **SQLAlchemy 2.0** ORM and **Alembic** schema migrations.

### Key Capabilities
- **Persistent Audit Logging**: Every website inspection run is permanently recorded.
- **Relational Integrity**: Foreign key constraints link findings, artifact metadata, and repair proposals to their parent inspection run with cascading deletes.
- **Safe Session Management**: Session context manager (`get_db_session`) guarantees connection pooling, automatic transaction commit on success, and automatic rollback on failure.
- **Human-in-the-Loop Governance**: Multi-stage review statuses (`approval_status`, `execution_status`, `verification_status`) stored with audit timestamps.

---

## 2. Local Development Setup (Windows)

### Prerequisites
- **PostgreSQL 18** (or PostgreSQL 16+) installed and running as a Windows service (port `5432`).
- Python virtual environment with `psycopg2-binary`, `sqlalchemy>=2.0.0`, and `alembic>=1.13.0`.

### Database & User Provisioning
Run the following commands using PostgreSQL's `psql` shell:

```sql
-- 1. Create the dedicated database user
CREATE USER omnisight_user WITH PASSWORD 'omnisight_password';

-- 2. Create the OmniSight application database
CREATE DATABASE omnisight_db OWNER omnisight_user;

-- 3. Grant schema permissions
GRANT ALL PRIVILEGES ON DATABASE omnisight_db TO omnisight_user;
\connect omnisight_db
GRANT ALL ON SCHEMA public TO omnisight_user;
```

---

## 3. Environment Configuration

Configure the database connection in your local `.env` file (copied from `.env.example`):

```bash
# PostgreSQL Database URL format:
# postgresql+psycopg2://<username>:<password>@<host>:<port>/<database_name>
DATABASE_URL=postgresql+psycopg2://omnisight_user:omnisight_password@localhost:5432/omnisight_db

# Separate database for automated unit and integration tests
TEST_DATABASE_URL=sqlite:///./test_omnisight.db
```

> **Security Note:** Never commit `.env` or plain-text database credentials to source control. `.env` is strictly ignored by `.gitignore`.

---

## 4. Database Schema & Tables

OmniSight manages four core relational tables in PostgreSQL:

### A. `runs` Table
Tracks inspection runs and their lifecycle states:
- `run_id` (VARCHAR(128), Primary Key)
- `url` (TEXT, Target website URL)
- `status` (VARCHAR(32): `queued`, `capturing`, `analyzing`, `repairing`, `completed`, `failed`, `cancelled`)
- `created_at` (TIMESTAMP WITH TIME ZONE)
- `completed_at` (TIMESTAMP WITH TIME ZONE, Nullable)
- `message` (TEXT, Latest human-readable diagnostic message)
- `error` (TEXT, Diagnostic error details if status is `failed`)

### B. `findings` Table
Stores visual defects and DOM anomalies identified by detection engines:
- `finding_id` (VARCHAR(128), Primary Key)
- `run_id` (VARCHAR(128), Foreign Key -> `runs.run_id`, On Delete CASCADE)
- `category` (VARCHAR(64): `layout_overflow`, `missing_visible_element`, `broken_image`)
- `severity` (VARCHAR(32): `low`, `medium`, `high`, `critical`)
- `confidence` (FLOAT, Score between 0.0 and 1.0)
- `description` (TEXT)
- `selector` (TEXT, CSS or DOM locator if element-scoped)
- `screenshot_path` (TEXT, Path to visual evidence file)
- `dom_snapshot_path` (TEXT, Path to captured DOM HTML snapshot)
- `source` (VARCHAR(64): `dom`, `vlm`, `mock`)

### C. `artifacts` Table
Stores evidence file records captured during browser execution:
- `artifact_id` (VARCHAR(128), Primary Key)
- `run_id` (VARCHAR(128), Foreign Key -> `runs.run_id`, On Delete CASCADE)
- `artifact_type` (VARCHAR(32): `screenshot`, `dom_snapshot`)
- `storage_path` (TEXT, Relative filesystem path)
- `file_size_bytes` (INTEGER)
- `content_type` (VARCHAR(64): `image/png`, `text/html`)
- `captured_at` (TIMESTAMP WITH TIME ZONE)

### D. `repair_proposals` Table
Manages Human-in-the-Loop review and self-healing remediations:
- `proposal_id` (VARCHAR(128), Primary Key)
- `run_id` (VARCHAR(128), Foreign Key -> `runs.run_id`, On Delete CASCADE)
- `finding_id` (VARCHAR(128), Foreign Key -> `findings.finding_id`, Nullable, On Delete SET NULL)
- `proposed_change` (TEXT, Proposed CSS patch, unified diff, or selector fix)
- `approval_status` (VARCHAR(32): `pending`, `approved`, `rejected`)
- `execution_status` (VARCHAR(32): `unapplied`, `applying`, `applied`, `failed`)
- `verification_status` (VARCHAR(32): `unverified`, `verified_success`, `verified_failure`, `inconclusive`)
- `reviewer_notes` (TEXT, Human reviewer justification)
- `github_pr_url` (TEXT, Linked pull request URL)
- `github_pr_number` (INTEGER, Linked pull request number)
- `created_at` (TIMESTAMP WITH TIME ZONE)
- `updated_at` (TIMESTAMP WITH TIME ZONE, Nullable)

---

## 5. Schema Migrations (Alembic)

Database schema revisions are managed through Alembic migrations located in `alembic/versions/`:

```powershell
# Run all pending migrations up to latest revision
alembic upgrade head

# Inspect current revision stamp
alembic current
```

---

## 6. Verification and Health Checks

### Verification via Python
Verify that the database connection is active and all tables exist:

```powershell
.\.venv\Scripts\python -c "
from backend.app.db.session import engine, check_db_connection
from sqlalchemy import inspect
print('Connection ping:', check_db_connection())
print('Tables:', inspect(engine).get_table_names())
"
```

### Health Check Endpoint
```powershell
curl http://127.0.0.1:8000/health
```
Expected response:
```json
{
  "status": "healthy",
  "database": "healthy",
  "version": "0.1.0"
}
```

### How to Verify Persistence After Restarting the Backend
To confirm that data remains permanently stored across backend restarts and process terminations:

1. **Create an inspection run and record data**:
   ```powershell
   # Create a run via curl
   curl -X POST "http://127.0.0.1:8000/api/v1/runs" -H "Content-Type: application/json" -d "{\"url\": \"http://127.0.0.1:8080/index.html\"}"
   ```
   Note the returned `run_id` (e.g. `run_9fa35601`).

2. **Terminate the backend server**:
   Press `Ctrl + C` in the backend terminal to completely kill the Uvicorn process.

3. **Restart the backend server**:
   ```powershell
   .\.venv\Scripts\uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
   ```

4. **Query the run again**:
   ```powershell
   curl "http://127.0.0.1:8000/api/v1/runs/run_9fa35601"
   ```
   The run record, status, timestamps, findings, and repair proposals will be fully preserved from PostgreSQL.

### Running Test Suite
```powershell
# Execute database integration tests
.\.venv\Scripts\pytest backend/tests/test_database.py -v

# Execute complete test suite
.\.venv\Scripts\pytest -q
```
