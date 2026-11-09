# OmniSight Backend API Documentation

## 1. Overview & Architecture

The OmniSight Backend is a high-performance REST API built using **FastAPI**, **Pydantic v2**, **SQLAlchemy 2.0**, and **Uvicorn**. It orchestrates automated UI inspection workflows, persists execution telemetry and defect evidence in **PostgreSQL 18**, manages Human-in-the-Loop repair approval lifecycles, and exposes standardized endpoints for the React dashboard.

### Architecture Topology

```
                       +-------------------------------+
                       |    React Dashboard Frontend   |
                       |       (Vite / Port 5173)      |
                       +---------------+---------------+
                                       | HTTP REST / JSON
                                       v
                       +-------------------------------+
                       |    FastAPI Application Core   |
                       |      (Uvicorn / Port 8000)    |
                       +---------------+---------------+
                                       |
          +----------------------------+----------------------------+
          |                            |                            |
          v                            v                            v
+--------------------+       +--------------------+       +--------------------+
|  RunOrchestrator   |       |  DatabaseRunStore  |       | Artifact Directory |
|  Integration Flow  |       |  (SQLAlchemy 2.0)  |       |    (/artifacts)    |
+---------+----------+       +---------+----------+       +--------------------+
          |                            |
     +----+----+                       v
     |         |             +--------------------+
     v         v             |   PostgreSQL 18    |
[Browser]   [Vision]         |   (omnisight_db)   |
[ Agent ]   [Engine]         +--------------------+
```

---

## 2. Directory Structure

```text
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # Central FastAPI application & lifespan management
│   ├── api/
│   │   ├── __init__.py
│   │   ├── artifacts.py            # Artifact retrieval endpoint with traversal security
│   │   ├── health.py               # Application and database health checks
│   │   ├── proposals.py            # Proposal review, approval, and rejection lifecycle
│   │   └── runs.py                 # Run creation, lookup, history, and pipeline dispatch
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py               # Environment configuration settings
│   │   └── logging.py              # Structured logging configuration
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                 # Declarative Base metadata
│   │   ├── models.py               # SQLAlchemy ORM models (runs, findings, artifacts, proposals)
│   │   └── session.py              # Connection pooling and session lifecycle helpers
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── artifacts.py            # Artifact response Pydantic models
│   │   ├── errors.py               # Standardized error payload models
│   │   ├── findings.py             # FindingResponse and evidence models
│   │   ├── proposals.py            # Proposal request and response models
│   │   ├── repairs.py              # Locator repair, patch, and PR models
│   │   └── runs.py                 # Run creation and lifecycle models
│   └── services/
│       ├── __init__.py
│       ├── orchestrator.py         # Multi-stage execution pipeline coordinator
│       └── run_store.py            # Database-backed repository with PostgreSQL persistence
└── tests/
    ├── test_artifacts.py           # Artifact security and retrieval tests
    ├── test_database.py            # PostgreSQL persistence & schema integrity tests
    ├── test_day5_integration_reliability.py # E2E lifecycle and error resilience tests
    ├── test_github_api.py          # Diff generation and PR approval gate tests
    ├── test_health.py              # Health check endpoint tests
    ├── test_integration.py         # Pipeline coordination and failure recovery tests
    ├── test_live_e2e_pipeline.py   # Multi-defect category round-trip tests
    ├── test_live_vlm_self_healing_e2e.py # VLM provider and live locator repair tests
    ├── test_orchestrator_pipeline.py # State transitions and timeout tests
    ├── test_proposals.py           # Reviewer notes and approval conflict tests
    ├── test_repairs_api.py         # Locator repair candidate generation tests
    └── test_runs.py                # Run validation and history tests
```

---

## 3. Server Startup & Verification

### Virtual Environment & Dependencies
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### Starting the Server
```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Interactive Documentation
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **OpenAPI Schema**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 4. Complete Endpoints Reference

### A. Health & Diagnostics

#### 1. System Health Check
- **Endpoint**: `GET /health`
- **Description**: Verifies API availability and pings PostgreSQL (`SELECT 1`).
- **Response (`200 OK`)**:
  ```json
  {
    "status": "healthy",
    "database": "healthy",
    "version": "0.1.0"
  }
  ```

---

### B. Inspection Runs Management

#### 2. Create Inspection Run
- **Endpoint**: `POST /api/v1/runs`
- **Query Parameters**: `auto_execute` (boolean, optional, default: `false`)
- **Request Body**:
  ```json
  {
    "url": "http://127.0.0.1:8080/index.html"
  }
  ```
- **Response (`201 Created`)**:
  ```json
  {
    "run_id": "run_a1b2c3d4",
    "url": "http://127.0.0.1:8080/index.html",
    "status": "queued",
    "created_at": "2026-11-07T12:00:00Z",
    "completed_at": null,
    "message": "Run created successfully and queued for inspection.",
    "error": null
  }
  ```
- **Validation Errors (`422 Unprocessable Content`)**: Rejects missing or malformed URLs (must start with `http://` or `https://`).

#### 3. List Historical Inspection Runs
- **Endpoint**: `GET /api/v1/runs`
- **Description**: Retrieves all runs persisted in PostgreSQL ordered by creation time descending.
- **Response (`200 OK`)**: Array of `RunResponse` objects.

#### 4. Lookup Run Status
- **Endpoint**: `GET /api/v1/runs/{run_id}`
- **Response (`200 OK`)**: `RunResponse` object reflecting current execution status (`queued`, `capturing`, `analyzing`, `completed`, `failed`).
- **Error (`404 Not Found`)**: If `run_id` does not exist in PostgreSQL.

#### 5. Execute Run Pipeline On Demand
- **Endpoint**: `POST /api/v1/runs/{run_id}/execute`
- **Description**: Asynchronously dispatches the Browser Agent and Vision Engine for a queued run.
- **Response (`202 Accepted`)**: Updated `RunResponse` with status `capturing`.
- **Conflict (`409 Conflict`)**: If the pipeline is already executing for this run.

---

### C. Findings & Evidence Artifacts

#### 6. Retrieve Run Findings
- **Endpoint**: `GET /api/v1/runs/{run_id}/findings`
- **Query Parameters**: `include_mock` (boolean, optional, default: `false`)
- **Response (`200 OK`)**:
  ```json
  [
    {
      "finding_id": "defect_run_a1b2c3d4_001",
      "category": "missing_visible_element",
      "severity": "high",
      "confidence": 0.94,
      "description": "Missing trigger action button locator in DOM.",
      "selector": "#btn-trigger-self-heal",
      "evidence": {
        "screenshot_path": "artifacts/run_a1b2c3d4/before.png",
        "dom_snapshot_path": "artifacts/run_a1b2c3d4/dom.html"
      },
      "source": "dom"
    }
  ]
  ```

#### 7. Serve Evidence Artifact File
- **Endpoint**: `GET /api/v1/artifacts/{run_id}/{filename}`
- **Security**: Strictly rejects path traversal (`../`) and non-artifact directory paths.
- **Response (`200 OK`)**: Binary image stream (`image/png`) or HTML document (`text/html`).
- **Error (`404 Not Found`)**: If the artifact file does not exist on disk.

---

### D. Self-Healing & Proposal Lifecycle

#### 8. Suggest Alternative Locators
- **Endpoint**: `POST /api/v1/runs/{run_id}/repair`
- **Request Body** (optional):
  ```json
  {
    "finding_id": "defect_run_a1b2c3d4_001",
    "verify_live": false
  }
  ```
- **Response (`200 OK`)**: Ranked locator candidates verified against the captured DOM snapshot with explainable heuristic scores.

#### 9. Create or Generate Repair Proposals
- **Endpoint**: `POST /api/v1/runs/{run_id}/proposals`
- **Manual Draft Request (`201 Created`)**:
  ```json
  {
    "finding_id": "defect_run_a1b2c3d4_001",
    "proposed_change": "button[data-testid='trigger-self-heal-cta']",
    "github_pr_url": "https://github.com/prabath-ux05/OmniSight/pull/12",
    "github_pr_number": 12
  }
  ```
- **Automated Generation Request (`200 OK`)**:
  ```json
  {
    "finding_id": "defect_run_a1b2c3d4_001",
    "target_file": "tests/e2e/test_checkout.py"
  }
  ```

#### 10. List Proposals for Run
- **Endpoint**: `GET /api/v1/runs/{run_id}/proposals`
- **Query Parameters**: `finding_id` (optional filter)
- **Response (`200 OK`)**: Array of `RepairProposalResponse` objects with tri-stage statuses.

#### 11. Authorize / Approve Proposal
- **Endpoint**: `POST /api/v1/proposals/{proposal_id}/approve`
- **Request Body**:
  ```json
  {
    "notes": "Verified selector uniqueness against production DOM."
  }
  ```
- **Response (`200 OK`)**: Updates `approval_status` to `"approved"` and records `reviewer_notes`.
- **Conflict (`409 Conflict`)**: If the proposal is already approved or rejected.

#### 12. Reject Proposal
- **Endpoint**: `POST /api/v1/proposals/{proposal_id}/reject`
- **Request Body**:
  ```json
  {
    "notes": "Rejected: locator is fragile on mobile viewports."
  }
  ```
- **Response (`200 OK`)**: Updates `approval_status` to `"rejected"`.
- **Conflict (`409 Conflict`)**: If the proposal is already approved or rejected.

#### 13. Proposal Status Summary
- **Endpoint**: `GET /api/v1/proposals/{proposal_id}/status`
- **Response (`200 OK`)**: Detailed breakdown of Review, Execution, and Verification states.

---

### E. Code Patching & GitHub Pull Request

#### 14. Generate Minimal Safe Diff
- **Endpoint**: `POST /api/v1/runs/{run_id}/proposals/{proposal_id}/patch`
- **Request Body**:
  ```json
  {
    "target_file": "tests/e2e/test_checkout.py"
  }
  ```
- **Security**: Rejects path traversal and protected OmniSight internal directories. Generates minimal unified diff strictly in memory.

#### 15. Submit Pull Request with Human Approval Gate
- **Endpoint**: `POST /api/v1/runs/{run_id}/proposals/{proposal_id}/pull-request`
- **Request Body**:
  ```json
  {
    "user_approved": true,
    "simulate": true
  }
  ```
- **Security & Governance Gate**: If `user_approved` is `false`, strictly returns **HTTP 403 Forbidden**. If `simulate` is `true`, dry-runs without remote writes.

---

### F. Provider Configuration Checks

#### 16. Inspect VLM Configuration
- **Endpoint**: `GET /api/v1/runs/vlm/config` (or `/api/v1/vlm/config`)
- **Description**: Reports VLM readiness (Gemini, OpenAI, Mock) with masked API keys.

#### 17. Inspect GitHub Configuration
- **Endpoint**: `GET /api/v1/runs/github/config` (or `/api/v1/github/config`)
- **Description**: Reports repository credentials status (`owner`, `repo`, `masked_token`) without leaking secrets.

---

## 5. Lifecycles & State Transitions

### Inspection Run Lifecycle
```
[queued] ──> [capturing] ──> [analyzing] ──> [completed]
   │              │               │
   └──────────────┴───────────────┴───────────> [failed]
```

1. **`queued`**: Run created and stored in PostgreSQL; awaiting execution.
2. **`capturing`**: Browser Agent launched Chromium, navigating and capturing screenshots and DOM.
3. **`analyzing`**: Vision Engine inspecting visual artifacts for layout, missing element, or broken image defects.
4. **`completed`**: Inspection finished successfully; findings stored in PostgreSQL.
5. **`failed`**: Execution stopped due to network failure, unreachable host, or fatal pipeline error.

### Repair Proposal Tri-Stage Governance
```
Review Status:       PENDING ──────> APPROVED or REJECTED (Human Decision)
Execution Status:    UNAPPLIED ────> APPLYING ───> APPLIED or FAILED
Verification Status: UNVERIFIED ───> VERIFIED_SUCCESS or VERIFIED_FAILURE
```

- **Separation of Concerns**: Authorizing a repair proposal only updates `approval_status`. It never falsely marks patch execution or visual re-inspection as verified.

---

## 6. Error Handling & HTTP Status Codes

| Code | Meaning | Example Trigger |
| :--- | :--- | :--- |
| **`200 OK`** | Request succeeded | Successful GET, proposal retrieval, status check. |
| **`201 Created`** | Resource created | Successful run creation (`POST /runs`), proposal draft. |
| **`202 Accepted`** | Asynchronous task queued | Dispatched execution pipeline (`POST /runs/{id}/execute`). |
| **`400 Bad Request`** | Malformed input | Empty or whitespace identifier, path traversal attempt. |
| **`403 Forbidden`** | Governance gate rejected | Submitting a PR with `user_approved=false`. |
| **`404 Not Found`** | Resource does not exist | Nonexistent `run_id`, `finding_id`, or missing artifact file. |
| **`409 Conflict`** | State machine conflict | Attempting duplicate approval or re-executing an active run. |
| **`422 Unprocessable`** | Schema validation error | Invalid URL format, empty `proposed_change` string. |
| **`502 Bad Gateway`** | Remote service failed | GitHub API token rejected during live PR submission. |
| **`503 Unavailable`** | Infrastructure failure | PostgreSQL database connection unreachable or down. |
