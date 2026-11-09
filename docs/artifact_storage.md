# OmniSight Artifact Storage & Evidence Persistence Documentation

## 1. Overview

OmniSight captures and persists two primary visual evidence artifacts for every inspection run:
1. **Viewport Screenshots** (`before.png`): High-resolution visual capture of the target web page in headless Chromium.
2. **DOM Snapshots** (`dom.html`): Full HTML source document captured at the exact moment of inspection.

Evidence persistence combines **local filesystem storage** for raw artifact binaries with **PostgreSQL metadata records** for indexing, querying, and audit tracking.

---

## 2. Directory Hierarchy

All inspection artifacts are written into the root `artifacts/` folder, namespaced by unique `run_id`:

```text
OmniSight/
├── artifacts/
│   ├── run_80e37fa1/
│   │   ├── before.png         # Primary viewport screenshot artifact (PNG)
│   │   └── dom.html           # Full DOM snapshot HTML document
│   ├── run_a1b2c3d4/
│   │   ├── before.png
│   │   └── dom.html
│   └── test_sample_run/
│       ├── before.png
│       └── dom.html
```

### Git Exclusion
Raw artifact files are dynamic test outputs and are strictly ignored in `.gitignore` to keep the repository lightweight:
```gitignore
# Generated browser evidence
artifacts/
```

---

## 3. Database Metadata Records (`artifacts` Table)

Whenever the Browser Agent writes an evidence file to disk, the orchestrator registers its metadata in the PostgreSQL `artifacts` table via `run_store.record_artifact()`:

### Schema Fields:
| Column | Type | Description |
| :--- | :--- | :--- |
| `artifact_id` | VARCHAR(128), PK | Unique identifier (e.g. `art_run_80e37fa1_screenshot`) |
| `run_id` | VARCHAR(128), FK | Foreign Key to `runs.run_id` (On Delete CASCADE) |
| `artifact_type` | VARCHAR(32) | `"screenshot"` or `"dom_snapshot"` |
| `storage_path` | TEXT | Local filesystem path (e.g. `artifacts/run_80e37fa1/before.png`) |
| `file_size_bytes` | INTEGER | Exact byte size of the file on disk |
| `content_type` | VARCHAR(64) | MIME type (`image/png` or `text/html`) |
| `captured_at` | TIMESTAMP (TZ) | ISO 8601 capture timestamp |

---

## 4. Evidence Retrieval via REST API

Evidence files are securely exposed over HTTP through the FastAPI backend:

### Endpoint:
```http
GET /api/v1/artifacts/{run_id}/{filename}
```

### Example Usage:
```bash
# Retrieve full screenshot image
curl "http://127.0.0.1:8000/api/v1/artifacts/run_80e37fa1/before.png" --output screenshot.png

# Retrieve captured DOM HTML document
curl "http://127.0.0.1:8000/api/v1/artifacts/run_80e37fa1/dom.html" --output snapshot.html
```

### Response Headers:
- For Screenshots: `Content-Type: image/png`
- For DOM Snapshots: `Content-Type: text/html; charset=utf-8`

---

## 5. Security & Path Traversal Protections

The artifact serving endpoint enforces strict security validations to prevent arbitrary file reading and directory traversal attacks:

1. **Path Normalization**: Rejects paths containing relative traversal sequences (`../`, `..\\`).
2. **Directory Confinement**: Resolves target paths against the run's canonical directory (`artifacts/{run_id}/`). Any path attempting to escape this root triggers **HTTP 400 Bad Request**.
3. **MIME Type Validation**: Only permitted artifact filenames and file extensions are served.
4. **Missing File Resilience**: If an artifact record exists in PostgreSQL but the physical file is missing from disk, the endpoint cleanly returns **HTTP 404 Not Found** with a descriptive JSON error payload rather than crashing.
