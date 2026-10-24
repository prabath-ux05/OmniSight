# OmniSight Backend API Documentation

## Overview

The OmniSight Backend is a high-performance REST API built using **FastAPI**, **Pydantic v2**, and **Uvicorn**. It serves as the central orchestration engine for OmniSight, coordinating inspection runs, managing execution state, and exposing structured defect findings for the dashboard frontend.

---

## 1. Installation & Environment Configuration

### Step 1: Virtual Environment Setup
Ensure your virtual environment is created and activated:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies
Install the required dependencies from the root `requirements.txt`:
```bash
python -m pip install -r requirements.txt
```

### Step 3: Environment Configuration
Copy the template configuration file to `.env`:

**Windows (PowerShell / Command Prompt):**
```powershell
Copy-Item .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

#### Application Environment Variables:
```env
APP_ENV=development
APP_DEBUG=true
API_HOST=127.0.0.1
API_PORT=8000
API_PREFIX=/api/v1
```
> **Security Notice**: Never commit `.env` files, API keys, passwords, or personal credentials to version control. The repository `.gitignore` automatically excludes `.env` files.

---

## 2. Starting the Backend Server

Start the local development server using **Uvicorn** with hot-reloading:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
*(Or alternatively via the Python module launcher)*:
```bash
python -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Interactive API Documentation:
Once running, open your browser to inspect and interact with the endpoints:
* **Swagger UI (Interactive)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* **ReDoc (Specification)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
* **Raw OpenAPI JSON**: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

---

## 3. Storage Architecture & Limitations

### In-Memory Storage (`RunStore`)
During this development milestone, inspection runs and findings are managed in memory via `backend/app/services/run_store.py`.

#### Documented Limitations:
1. **Volatility (RAM-Only)**: Runs and findings are stored in process memory. Stopping or restarting the Uvicorn server resets the store to empty.
2. **Single-Process Scope**: In-memory data is not shared between multiple Uvicorn worker processes or clustered instances. Run the server with a single worker during development.
3. **Database Integration**: A persistent relational database (such as SQLite or PostgreSQL) with ORM models will replace this in-memory store in a future milestone.

---

## 4. Endpoints Reference

### 1. Health Check
* **Endpoint**: `GET /health`
* **Purpose**: Confirms that the backend API web server is operational.
* **Note**: This endpoint confirms backend service availability only. It does **not** claim that the browser agent or vision engine are operational.

#### Example Request:
```bash
curl -X GET "http://127.0.0.1:8000/health" -H "Accept: application/json"
```

#### Example Response (`200 OK`):
```json
{
  "status": "ok",
  "app": "OmniSight Backend",
  "version": "0.1.0"
}
```

---

### 2. Create Inspection Run
* **Endpoint**: `POST /api/v1/runs`
* **Purpose**: Validates the inspection request, generates a unique `run_id`, and places the run in the initial `"queued"` status.
* **Validation Rules**:
  * `url`: Must be a valid HTTP or HTTPS URL (maximum 2048 characters). Leading/trailing whitespace is automatically stripped.
  * Rejects missing fields, malformed URLs, and unsupported schemes (such as `ftp://`).

#### Example Request:
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/runs" \
     -H "Content-Type: application/json" \
     -d '{"url": "http://127.0.0.1:8000/"}'
```

#### Example Response (`201 Created`):
```json
{
  "run_id": "run_a1b2c3d4",
  "url": "http://127.0.0.1:8000/",
  "status": "queued",
  "created_at": "2026-10-24T18:00:00.123456+00:00",
  "message": "Run created successfully and queued for inspection.",
  "error": null
}
```

#### Example Validation Error Response (`422 Unprocessable Entity`):
*Triggered when `url` is missing or invalid:*
```json
{
  "detail": [
    {
      "type": "url_parsing",
      "loc": ["body", "url"],
      "msg": "Input should be a valid URL, relative URL without a base"
    }
  ]
}
```

---

### 3. Retrieve Run Status & Metadata
* **Endpoint**: `GET /api/v1/runs/{run_id}`
* **Purpose**: Returns the current status and metadata of an existing run.
* **Note**: Returns the genuine stored lifecycle state (`"queued"`). It does **not** invent progress stages or claim that inspection, repair, or verification has occurred.

#### Example Request:
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/runs/run_a1b2c3d4" \
     -H "Accept: application/json"
```

#### Example Response (`200 OK`):
```json
{
  "run_id": "run_a1b2c3d4",
  "url": "http://127.0.0.1:8000/",
  "status": "queued",
  "created_at": "2026-10-24T18:00:00.123456+00:00",
  "message": "Run created successfully and queued for inspection.",
  "error": null
}
```

#### Example Unknown Run Response (`404 Not Found`):
```json
{
  "detail": "Run 'run_unknown_999' not found."
}
```

#### Example Invalid Run ID Response (`400 Bad Request`):
*Triggered when `run_id` is empty or whitespace-only:*
```json
{
  "detail": "Invalid run_id: identifier must not be empty or whitespace."
}
```

---

### 4. Retrieve Run Defect Findings
* **Endpoint**: `GET /api/v1/runs/{run_id}/findings`
* **Purpose**: Retrieves the list of UI defect findings associated with the specified run.
* **Agreed Finding Schema**:
  * `finding_id`: Unique finding identifier (e.g. `defect_run_xxx_001`).
  * `category`: One of `"layout_overflow"`, `"missing_visible_element"`, `"broken_image"`.
  * `severity`: `"low" | "medium" | "high" | "critical"`.
  * `confidence`: Float between `0.0` and `1.0`.
  * `description`: Explanation of the issue.
  * `selector`: CSS/DOM selector if identified (or `null`).
  * `evidence`: Contains `screenshot_path` and `dom_snapshot_path`.
  * `source`: Explicitly tagged as `"mock"` (or `"vlm"` when integrated).

#### Example Request:
```bash
curl -X GET "http://127.0.0.1:8000/api/v1/runs/run_a1b2c3d4/findings" \
     -H "Accept: application/json"
```

#### Example Response — Clean Run with No Defects (`200 OK`):
```json
[]
```

#### Example Response — Run with Mock Defect Findings (`200 OK`):
> **Note**: These findings are clearly labelled mock findings (`source: "mock"`) used for early dashboard testing before real vision model analysis is connected.
```json
[
  {
    "finding_id": "defect_run_a1b2c3d4_001",
    "category": "layout_overflow",
    "severity": "medium",
    "confidence": 0.92,
    "description": "[MOCK] Content panel text extends beyond container boundary.",
    "selector": "#main-content-panel",
    "evidence": {
      "screenshot_path": "artifacts/run_a1b2c3d4/before.png",
      "dom_snapshot_path": "artifacts/run_a1b2c3d4/dom.html"
    },
    "source": "mock"
  },
  {
    "finding_id": "defect_run_a1b2c3d4_002",
    "category": "broken_image",
    "severity": "high",
    "confidence": 0.88,
    "description": "[MOCK] Service topology image fails to display.",
    "selector": "#service-topology-image",
    "evidence": {
      "screenshot_path": "artifacts/run_a1b2c3d4/before.png",
      "dom_snapshot_path": null
    },
    "source": "mock"
  }
]
```

#### Example Unknown Run Response (`404 Not Found`):
```json
{
  "detail": "Run 'run_missing_999' not found."
}
```

---

## 5. Automated Tests

The backend test suite is located in `backend/tests/` and configured via `pytest.ini`.

### Running All Backend Tests:
```bash
pytest -v
```
*(Or via Python)*:
```bash
python -m pytest backend/tests/ -v
```

### Covered Test Cases (25 Tests):
* **Health endpoint**: Registration in OpenAPI, unit execution, raw ASGI HTTP dispatch.
* **Run creation**: Valid URL, leading/trailing whitespace stripping, oversized URL rejection (422), unsupported scheme rejection (422), missing body rejection (422), unique run ID generation.
* **Run retrieval**: Existing run metadata matching (200), unknown run ID (404), whitespace run ID (400).
* **Findings retrieval**: Clean run empty list (200), mock findings structure and `source="mock"` verification (200), unknown run ID (404), whitespace run ID (400).
* **Consistency**: Guaranteed run ID structure and adherence to allowed lifecycle states (`queued`, `capturing`, `analyzing`, etc.).
