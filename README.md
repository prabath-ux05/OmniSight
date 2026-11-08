# OmniSight — Multimodal UI Self-Healing & RPA Agent

OmniSight is an intelligent, multimodal Robotic Process Automation (RPA) and automated UI test self-healing project. It aims to combine vision-language models, browser automation, and Git workflows to detect UI changes, diagnose broken selectors and workflows, generate candidate test repairs, and submit changes for human review.

The project includes a Playwright-based Browser Agent for browser navigation, screenshot capture, DOM snapshot generation, metadata collection, browser error monitoring, and automated testing. The Vision Engine provides validated input and finding models, evidence validation, deterministic mock detection, static HTML DOM heuristics, Gemini-powered vision-language analysis, screenshot cropping, evaluation metrics, and post-repair verification. It can analyze screenshot and DOM evidence, produce structured findings, and compare full-image and cropped-image detection workflows. Other components are under active development.

## 🚀 Project Objective

UI automation scripts can break when frontend layouts, DOM structures, CSS classes, or dynamic element IDs change. OmniSight aims to address these issues through:

1. **Multimodal Visual Inspection:** Analyze screenshots and DOM evidence together to identify potential UI defects.
2. **Autonomous Diagnosis:** Identify broken locators, layout drift, and UI regressions.
3. **Automated Code Self-Healing:** Generate candidate selector repairs and test-script updates for review and verification.
4. **GitHub Integration:** Support branches, commits, and pull requests for validated changes.
5. **Human-in-the-Loop Dashboard:** Provide a dashboard for reviewing findings and monitoring automation.

## 📁 Repository Structure

```text
OmniSight/
vision_engine/
├── detection/
│   ├── dom_detector.py
│   ├── gemini_provider.py
│   ├── mock_detector.py
│   ├── providers.py
│   ├── vlm_detector.py
│   ├── vlm_interface.py
│   └── vlm_response_parser.py
├── prompting/
│   ├── defect_prompts.py
│   └── vlm_prompt.py
├── tests/
│   ├── test_dom_detector.py
│   ├── test_evaluation.py
│   ├── test_evidence_validator.py
│   ├── test_gemini_provider.py
│   ├── test_image_processing.py
│   ├── test_mock_detector.py
│   ├── test_models.py
│   ├── test_verification.py
│   ├── test_vlm_detector.py
│   ├── test_vlm_interface.py
│   ├── test_vlm_prompt.py
│   └── test_vlm_response_parser.py
├── demo_tests/
├── evaluation.py
├── evidence_validator.py
├── image_processing.py
├── models.py
├── verification.py
└── README.md
│
├── browser_agent/
│   ├── navigation/                # Browser navigation and interactions
│   ├── screenshots/               # Screenshot capture and artifacts
│   ├── evidence/                  # DOM snapshots and execution evidence
│   └── tests/                     # Browser Agent automated tests
│
├── backend/                       # FastAPI backend and orchestration API
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   └── tests/
│
├── self_healing/                  # Failure analysis and repair pipeline
├── github_integration/            # GitHub and Git workflow automation
├── frontend/                      # Monitoring dashboard
├── docs/                          # Project and module documentation
│   ├── backend_api.md
│   └── browser_agent_setup.md
├── tests/                         # Project-level and integration tests
├── artifacts/                     # Generated browser execution artifacts
├── pytest.ini
├── .gitignore
├── .env.example
├── requirements.txt
└── README.md
```

The tree lists the documented Vision Engine files and Browser Agent module structure. Other project modules may contain additional files maintained by their respective team members.

## 👥 Team Module Distribution

| Member / Focus Area | Primary Modules | Responsibilities |
|---|---|---|
| Member 1: Vision & Intelligence | `vision_engine/` | Visual defect detection, input/output models, evidence validation, model integration, prompt engineering, and element localization |
| Member 2: RPA & Browser Agent | `browser_agent/` | Playwright navigation, browser interactions, screenshots, DOM snapshots, metadata collection, browser error handling, evidence generation, and automated testing |
| Member 3: Self-Healing & Verification | `self_healing/` | Failure analysis, candidate selector repairs, repair generation, and patch verification |
| Member 4: Backend & GitHub Integration | `backend/`, `github_integration/` | API orchestration, backend services, Git workflows, branch management, pull requests, and application state |

## 🛠️ Setup

### Prerequisites

- Python installed and available in the terminal.
- Git installed and configured.
- Access to the OmniSight repository.
- Playwright and its required browser installed for Browser Agent work.

### 1. Clone the Repository

```bash
git clone https://github.com/prabath-ux05/OmniSight.git
cd OmniSight
```

If you already have the repository locally, open its root directory instead of cloning it again.

### 2. Create and Activate a Virtual Environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS/Linux:**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install Python Dependencies

Run from the repository root:

```bash
python -m pip install -r requirements.txt
```

### 4. Install the Playwright Chromium Browser

For Browser Agent development, install Chromium:

```bash
python -m playwright install chromium
```

### 5. Configure Environment Variables

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**macOS/Linux:**

```bash
cp .env.example .env
```

Configure only the environment variables required for your assigned work. Never commit `.env` files, API keys, passwords, or access tokens. External model integrations must use team-approved providers and authorized credentials.

### 6. Run Tests

Run the full test suite from the repository root:

```bash
python -m pytest -v
```

To run only the Vision Engine tests:

```bash
python -m pytest ./vision_engine/tests -q
```

To run the Backend tests:

```bash
pytest backend/tests -v
```

Review the test output to confirm which tests passed. Some test suites may require additional dependencies or configuration.

### 7. Run the Backend API Server

Start the local FastAPI development server using Uvicorn:

```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running, access the interactive API documentation in your browser:

- **Swagger UI (Interactive):** http://127.0.0.1:8000/docs
- **ReDoc (Specification):** http://127.0.0.1:8000/redoc

## 📌 Development Status

The following checklist reflects the documented development status. Features should only be marked complete when their implementation and tests have been verified.

### Vision Engine — Member 1: Vision & Intelligence

- [x] Implemented Pydantic input, finding, evidence-reference, and bounding-box models.
- [x] Added input validation and evidence-file validation.
- [x] Implemented deterministic mock defect detection.
- [x] Implemented static HTML DOM heuristics for image and form-label issues.
- [x] Integrated Gemini as a vision-language model provider.
- [x] Added VLM prompt engineering and structured response parsing.
- [x] Implemented screenshot cropping with support for single and multiple crop regions.
- [x] Added coordinate translation from cropped images to original screenshot coordinates.
- [x] Implemented spatial defect evaluation using Intersection over Union (IoU).
- [x] Added one-to-one finding matching and configurable IoU thresholds.
- [x] Added precision, recall, and F1-score evaluation metrics.
- [x] Implemented post-repair finding verification.
- [x] Added Gemini demo tests, evidence-capture scripts, and crop-mode benchmarking.
- [x] Expanded automated tests across Vision Engine components.

### Vision Engine Implementation Details

#### Implemented Files

| File | Description |
|---|---|
| `vision_engine/models.py` | Defines validated input, finding, evidence-reference, and bounding-box models. |
| `vision_engine/evidence_validator.py` | Validates evidence-file existence, type, readability, and non-empty content. |
| `vision_engine/detection/mock_detector.py` | Provides deterministic mock defect and clean-page scenarios. |
| `vision_engine/detection/dom_detector.py` | Uses static HTML heuristics to identify selected image and form-label issues. |
| `vision_engine/detection/gemini_provider.py` | Implements Gemini-backed vision-language model detection. |
| `vision_engine/detection/vlm_detector.py` | Provides VLM detection functionality. |
| `vision_engine/detection/vlm_interface.py` | Defines the interface for vision-language model providers. |
| `vision_engine/detection/vlm_response_parser.py` | Parses and validates structured VLM responses. |
| `vision_engine/detection/providers.py` | Contains provider-related detection functionality. |
| `vision_engine/prompting/vlm_prompt.py` | Builds prompts and instructions for VLM-based defect detection. |
| `vision_engine/prompting/defect_prompts.py` | Contains defect-related prompt definitions. |
| `vision_engine/image_processing.py` | Handles screenshot cropping and coordinate translation. |
| `vision_engine/evaluation.py` | Evaluates detection results using selector and spatial IoU matching, with precision, recall, and F1 metrics. |
| `vision_engine/verification.py` | Verifies whether detected issues have been resolved after a repair. |
| `vision_engine/demo_tests/` | Contains demo pages, evidence-capture scripts, Gemini validation, DOM checks, and crop benchmarking. |
| `vision_engine/tests/` | Contains automated tests for Vision Engine models, detection, evaluation, prompting, image processing, and verification. |
| `vision_engine/README.md` | Documents Vision Engine architecture, usage, capabilities, and limitations. |

#### Current Capabilities

- Accepts screenshot and DOM evidence through validated input models.
- Validates evidence-file accessibility and basic file requirements.
- Supports deterministic mock detection for controlled testing.
- Uses static DOM heuristics to identify selected image and form-label issues.
- Integrates Gemini for screenshot and DOM-based vision-language analysis.
- Uses structured prompts and response parsing to produce standardized findings.
- Supports full-image analysis and single or multiple screenshot crop regions.
- Translates bounding boxes from cropped-image coordinates back to original screenshot coordinates.
- Evaluates expected and detected findings using category matching, selector matching, and spatial Intersection over Union (IoU).
- Supports configurable IoU thresholds and one-to-one finding assignment.
- Calculates true positives, false positives, false negatives, precision, recall, and F1 score.
- Supports post-repair verification with `resolved`, `partially_resolved`, `unresolved`, and `unverifiable` outcomes.
- Includes demo scripts for evidence capture, Gemini validation, DOM timeout checks, and crop-mode benchmarking.

#### Current Limitations

The DOM detector performs static HTML analysis and does not execute JavaScript, inspect the fully rendered page layout, or independently verify whether remote images load successfully.

Gemini-based detection depends on external provider availability, API access, and model response quality. VLM predictions may produce false positives or miss defects, so findings require validation.

Screenshot crop benchmarking uses controlled demo fixtures and does not establish general accuracy improvements, production performance, or guaranteed cost savings.

Evidence validation checks basic file accessibility and content requirements but does not establish the semantic correctness of all supplied evidence.

The Vision Engine focuses on defect detection, evaluation, and verification. Complete browser automation, automatic repair execution, and end-to-end RPA workflows are handled by other project components.

#### Testing

- Latest recorded full Vision Engine test suite: **145 passed**.
- Run the tests using:

```powershell
python -m pytest vision_engine/tests -v

### Browser Agent — Member 2: RPA & Browser Agent

- [x] Implemented Playwright-based browser automation using Chromium.
- [x] Added browser launch, page navigation, page title retrieval, and URL collection.
- [x] Implemented full-page screenshot capture and run-based artifact storage.
- [x] Added DOM snapshot generation and evidence storage.
- [x] Implemented metadata collection, including URL, page title, ISO-8601 timestamp, and viewport dimensions.
- [x] Added browser console error collection and JavaScript page exception tracking.
- [x] Implemented invalid URL validation and navigation timeout handling.
- [x] Added HTTP response status and navigation duration tracking.
- [x] Added failed network request tracking.
- [x] Added structured success and failure responses.
- [x] Implemented safe browser cleanup on success and failure.
- [x] Added before-and-after screenshot and DOM evidence capture.
- [x] Added DOM metadata collection, including image details, element counts, form details, and interactive elements.
- [x] Added backward compatibility for existing DOM artifact filenames.
- [x] Added Windows Proactor event-loop compatibility.
- [x] Added automated tests for navigation, screenshots, DOM capture, metadata, and evidence validation.
- [x] Added tests for invalid URLs, missing run IDs, timeout handling, and artifact creation.
- [x] Added a local HTML test page and temporary HTTP server for repeatable browser testing.
- [x] Updated Git ignore rules to exclude generated browser artifacts from version control.
- [x] Documented Playwright installation, usage, testing, evidence structure, and integration requirements.
- [x] Merged Browser Agent changes into the main branch through GitHub PR #9.
- [ ] Complete further cross-module integration validation with the Vision Engine and Backend.
- [ ] Complete final end-to-end integration review and project handover.

#### Browser Agent Implementation Details

The Browser Agent provides a Playwright-based browser automation module that captures browser execution evidence for use by other OmniSight components.

**Implemented Capabilities**

- **Browser Navigation:** Launches Chromium and navigates to target URLs.
- **Screenshot Capture:** Captures full-page screenshots and stores artifacts organized by run.
- **DOM Snapshot Generation:** Captures before-and-after DOM evidence for further inspection.
- **Metadata Collection:** Records the current URL, page title, viewport information, and ISO-8601 timestamps.
- **Error Monitoring:** Collects browser console errors, JavaScript page exceptions, and failed network requests.
- **HTTP Diagnostics:** Records HTTP response status and navigation duration.
- **Failure Handling:** Validates URLs, handles navigation timeouts, returns structured failure information, and safely closes browser resources.
- **DOM Analysis Metadata:** Collects image information, element counts, form details, and interactive element information.
- **Evidence Management:** Organizes screenshots, DOM snapshots, and metadata using unique run IDs.
- **Automated Testing:** Covers navigation, screenshots, DOM capture, metadata, artifact creation, evidence validation, invalid URLs, timeout handling, and browser cleanup.
- **Windows Compatibility:** Includes Windows Proactor event-loop policy handling for Playwright execution.
- **Documentation:** Includes Playwright installation, test execution, evidence structure, and integration guidelines.

#### Standardized Evidence Contract

The Browser Agent provides structured evidence containing:

| Field | Description |
|---|---|
| `run_id` | Unique identifier for the browser execution |
| `url` | URL of the visited page |
| `page_title` | Title of the page |
| `captured_at` | Capture timestamp in ISO-8601 format |
| `viewport` | Browser viewport width and height |
| `screenshot_path` | Reference to the captured screenshot |
| `dom_snapshot_path` | Reference to the generated DOM snapshot |
| `console_errors` | Collected browser console errors |
| `page_errors` | Captured JavaScript page exceptions |
| `response_status` | HTTP response status code |
| `navigation_duration_ms` | Time taken for navigation |
| `failed_requests` | Details of failed network requests |
| `status` | Outcome of browser execution |
| `error` | Failure details, when applicable |

This contract allows the Vision Engine and other components to consume browser execution evidence through a consistent structure.

#### Browser Agent Testing

Automated tests cover:

- Browser launch and navigation.
- Screenshot capture and artifact creation.
- Before-and-after DOM snapshot generation.
- Metadata collection.
- Evidence contract validation.
- Console error and JavaScript exception collection.
- Failed network request tracking.
- HTTP response status handling.
- Invalid URL and missing run ID handling.
- Navigation timeout handling.
- Successful capture when the page contains a broken image.
- Artifact existence and structured failure responses.
- Safe browser cleanup.
- Windows event-loop compatibility.

The complete test suite passed after resolving integration and compatibility issues.

The Browser Agent changes have been merged into the main branch through GitHub PR #9. Further cross-module integration validation and end-to-end testing remain part of the project's ongoing development.

### Backend & API Orchestration — Member 4: Backend Developer

- [x] Initialized the FastAPI application entry point in `backend/app/main.py`.
- [x] Implemented `GET /health` endpoint verifying backend server availability.
- [x] Created `POST /api/v1/runs` endpoint with URL validation, whitespace stripping, and unique `run_id` generation.
- [x] Implemented `GET /api/v1/runs/{run_id}` endpoint returning run status and metadata.
- [x] Implemented `GET /api/v1/runs/{run_id}/findings` endpoint returning structured findings or empty lists.
- [x] Implemented an in-memory `RunStore` repository for managing inspection runs and defect findings.
- [x] Coordinated finding schemas (`FindingResponse`, `EvidenceReferences`) with the Vision Engine data contract.
- [x] Added deterministic mock defect findings (`source="mock"`) for early milestone testing.
- [x] Added centralized safe application logging without exposing secrets.
- [x] Added standardized error response schemas and HTTP 400/404/422 validation handling.
- [x] Configured `pytest.ini` with backend testpaths and pythonpath.
- [x] Created 25 automated backend tests covering health, runs, findings, error handling, and lifecycle status consistency.
- [x] Connected the backend run lifecycle to the live Browser Agent Playwright runner.
- [x] Connected the backend findings retrieval to live Vision Engine inference.
- [x] Replaced temporary in-memory `RunStore` with PostgreSQL 18 database persistence (`runs`, `findings`, `artifacts`, `repair_proposals`) and Alembic migrations.
- [x] Developed React 18 / Vite dashboard with live inspection, run history audit table, and Human-in-the-Loop repair approval workflow.
- [x] Verified full integration across all 152 backend tests and 17 frontend tests.

#### Backend & Dashboard Documentation

| Document | Description |
|---|---|
| [`docs/backend_api.md`](docs/backend_api.md) | Complete backend architecture, all 17 REST endpoints, request/response examples, and error codes. |
| [`docs/postgresql_setup.md`](docs/postgresql_setup.md) | PostgreSQL 18 setup guide, SQLAlchemy 2.0 ORM models, Alembic migrations, and persistence verification. |
| [`docs/artifact_storage.md`](docs/artifact_storage.md) | Screenshot and DOM snapshot storage structure, security path traversal guards, and HTTP retrieval APIs. |
| [`docs/frontend_dashboard.md`](docs/frontend_dashboard.md) | React dashboard component architecture, auto-polling lifecycle, and Human-in-the-Loop review/approval workflow. |
| [`docs/browser_agent_setup.md`](docs/browser_agent_setup.md) | Browser Agent Playwright automation, headless Chromium execution, and evidence capture. |

#### Backend & Dashboard Capabilities

- **PostgreSQL 18 Persistence:** Permanent storage for all inspection runs, defect findings, artifact references, and repair proposals. Survives process and server restarts.
- **Automated Pipeline Coordination:** Orchestrates headless browser navigation via Playwright and defect detection via Vision Engine.
- **Artifact Serving:** Securely streams screenshots and DOM HTML snapshots over HTTP at `/api/v1/artifacts/{run_id}/{filename}` with path traversal protection.
- **Human-in-the-Loop Governance:** Tri-stage lifecycle badges separating Review authorization (`PENDING`/`APPROVED`/`REJECTED`), patch execution (`UNAPPLIED`/`APPLIED`/`FAILED`), and visual verification (`UNVERIFIED`/`VERIFIED_SUCCESS`/`VERIFIED_FAILURE`).
- **Interactive API Documentation:** Full Swagger UI available at `http://127.0.0.1:8000/docs` and ReDoc at `http://127.0.0.1:8000/redoc`.
- **React Frontend Dashboard:** Running on Vite (`http://localhost:5173`) with live inspection progress, defect findings, DOM/screenshot viewer, PostgreSQL history audit log, and proposal approval controls.

### Other Project Modules

The Self-Healing, GitHub Integration, and Frontend modules are part of the overall project. Their implementation status will be updated by their respective team members based on their actual code and test results.

## 📋 Development Guidelines

- Work on your assigned feature branch.
- Keep commits focused and descriptive.
- Add or update tests when changing behavior.
- Run relevant tests before pushing changes.
- Review `git diff` before committing.
- Do not commit secrets, local virtual environments, or generated artifacts.
- Use approved credentials and providers for external model integrations.
- Submit changes through pull requests and follow the team's review process.

## 🗺️ Future Roadmap

- Improve visual defect classification and finding validation.
- Expand evaluation using more defect categories and real-world test scenarios.
- Improve screenshot preprocessing and crop-selection strategies.
- Connect screenshot and DOM evidence from the Browser Agent to visual inspection.
- Develop the self-healing pipeline for candidate selector repairs.
- Integrate backend APIs and GitHub workflows.
- Develop the human-in-the-loop dashboard for reviewing findings and proposed repairs.
- Complete integration testing across the Browser Agent, Vision Engine, and Backend.

## 🤝 Contribution

Contributions should follow the team's assigned module responsibilities and development workflow. Keep changes scoped to your assigned work, test them where possible, and document limitations clearly.

## ⚖️ Current Project Limitations

OmniSight is under active development. The Vision Engine provides validated data models, evidence-file checks, deterministic mock detection, static HTML DOM heuristics, and Gemini-powered vision-language analysis.

Gemini-based detection depends on provider availability, valid API credentials, and model response quality. Its detection accuracy and performance require further evaluation across a wider range of real-world UI defects.

The Browser Agent captures browser evidence and handles common execution failures. However, full integration across the Browser Agent, Vision Engine, Backend, and dashboard still requires verification.

Automated repair generation, complete end-to-end self-healing workflows, and production-level integration remain under development.
