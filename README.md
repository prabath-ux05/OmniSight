OmniSight — Multimodal UI Self-Healing & RPA Agent
OmniSight is an intelligent, multimodal Robotic Process Automation (RPA) and automated UI test self-healing project. It aims to combine vision-language models, browser automation, and Git workflows to detect UI changes, diagnose broken selectors and workflows, generate candidate test repairs, and submit changes for human review.

The project includes a Playwright-based Browser Agent for browser navigation, screenshot capture, DOM snapshot generation, metadata collection, browser error monitoring, and automated testing. The Vision Engine provides validated input and finding models, evidence validation, deterministic mock detection, static HTML DOM heuristics, Gemini-powered vision-language analysis, screenshot cropping, evaluation metrics, and post-repair verification. It can analyze screenshot and DOM evidence, produce structured findings, and compare full-image and cropped-image detection workflows. Other components are under active development.

🚀 Project Objective
UI automation scripts can break when frontend layouts, DOM structures, CSS classes, or dynamic element IDs change. OmniSight aims to address these issues through:
1. Multimodal Visual Inspection: Analyze screenshots and DOM evidence together to identify potential UI defects.
2. Autonomous Diagnosis: Identify broken locators, layout drift, and UI regressions.
3. Automated Code Self-Healing: Generate candidate selector repairs and test-script updates for review and verification.
4. GitHub Integration: Support branches, commits, and pull requests for validated changes.
5. Human-in-the-Loop Dashboard: Provide a dashboard for reviewing findings and monitoring automation.
📁 Repository Structure
OmniSight/
├── vision_engine/
│   ├── detection/
│   │   ├── dom_detector.py
│   │   ├── mock_detector.py
│   │   ├── gemini_provider.py
│   │   ├── vlm_interface.py
│   │   └── vlm_response_parser.py
│   │
│   ├── prompting/
│   │   └── vlm_prompt.py
│   │
│   ├── demo_tests/
│   │   ├── evidence/
│   │   │   ├── broken_image.html
│   │   │   ├── broken_image.png
│   │   │   ├── clean.html
│   │   │   ├── clean.png
│   │   │   ├── overflow.html
│   │   │   ├── overflow.png
│   │   │   ├── crop_comparison_results.json
│   │   │   ├── dom_timeout_check_results.json
│   │   │   └── live_validation_results.json
│   │   │
│   │   ├── benchmark_crop_modes.py
│   │   ├── capture_evidence.py
│   │   ├── demo_site.html
│   │   ├── run_dom_timeout_check.py
│   │   ├── run_gemini_tests.py
│   │   └── README.md
│   │
│   ├── tests/
│   │   ├── test_dom_detector.py
│   │   ├── test_evidence_validator.py
│   │   ├── test_evaluation.py
│   │   ├── test_gemini_provider.py
│   │   ├── test_image_processing.py
│   │   ├── test_mock_detector.py
│   │   ├── test_models.py
│   │   ├── test_verification.py
│   │   ├── test_vlm_interface.py
│   │   ├── test_vlm_prompt.py
│   │   └── test_vlm_response_parser.py
│   │
│   ├── evaluation.py
│   ├── evidence_validator.py
│   ├── image_processing.py
│   ├── models.py
│   ├── verification.py
│   └── README.md
│
├── browser_agent/
│   ├── navigation/                # Browser navigation and interactions
│   ├── screenshots/               # Screenshot capture and artifacts
│   ├── evidence/                  # DOM snapshots and execution evidence
│   └── tests/                     # Browser Agent automated tests
│
├── backend/                       # FastAPI backend and orchestration API
│   ├── app/
│   │   ├── api/                   # Route handlers (health, runs, findings)
│   │   ├── core/                  # Safe logging and configurations
│   │   ├── schemas/               # Pydantic models (health, runs, findings, errors)
│   │   ├── services/              # Business logic and in-memory RunStore
│   │   └── main.py                # FastAPI application entry point
│   └── tests/                     # Automated backend test suites
│
├── self_healing/                  # Failure analysis and repair pipeline
├── github_integration/            # GitHub and Git workflow automation
├── frontend/                      # Monitoring dashboard
├── docs/                          # Project and module documentation
│   ├── backend_api.md             # Backend API guide and endpoint reference
│   └── browser_agent_setup.md     # Browser Agent setup guide
├── tests/                         # Project-level and integration tests
├── artifacts/                     # Generated browser execution artifacts
├── pytest.ini                     # Pytest configuration
├── .gitignore
├── .env.example
├── requirements.txt
└── README.md

The tree lists the documented Vision Engine files and Browser Agent module structure. Other project modules may contain additional files maintained by their respective team members.
👥 Team Module Distribution
Member / Focus Area	Primary Modules	Responsibilities
Member 1: Vision & Intelligence	vision_engine/	Visual defect detection, input/output models, evidence validation, model integration, prompt engineering, and element localization
Member 2: RPA & Browser Agent	browser_agent/	Playwright navigation, browser interactions, screenshots, DOM snapshots, metadata collection, browser error handling, evidence generation, and automated testing
Member 3: Self-Healing & Verification	self_healing/	Failure analysis, candidate selector repairs, repair generation, and patch verification
Member 4: Backend & GitHub Integration	backend/, github_integration/	API orchestration, backend services, Git workflows, branch management, pull requests, and application state


🛠️ Setup
Prerequisites
- Python installed and available in the terminal.
- Git installed and configured.
- Access to the OmniSight repository.
- Playwright and its required browser installed for Browser Agent work.
1. Clone the Repository
If you have not cloned the repository yet:
git clone https://github.com/prabath-ux05/OmniSight.git
cd OmniSight
If you already have the repository locally, open its root directory instead of cloning it again.
2. Create and Activate a Virtual Environment
Windows PowerShell:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
macOS/Linux:
python -m venv .venv
source .venv/bin/activate
3. Install Python Dependencies
Run from the repository root:
python -m pip install -r requirements.txt
4. Install the Playwright Chromium Browser
For Browser Agent development, install Chromium:
python -m playwright install chromium
5. Configure Environment Variables
Windows PowerShell:
Copy-Item .env.example .env
macOS/Linux:
cp .env.example .env
Configure only the environment variables required for your assigned work. Never commit .env files, API keys, passwords, or access tokens. External model integrations must use team-approved providers and authorized credentials.
6. Run Tests
Run the full test suite from the repository root:
python -m pytest -v
To run only the Vision Engine tests:
python -m pytest ./vision_engine/tests -q
To run the Backend tests:
pytest backend/tests -v
Review the test output to confirm which tests passed. Some test suites may require additional dependencies or configuration.
7. Run the Backend API Server
Start the local FastAPI development server using Uvicorn:
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
Once running, access the interactive API documentation in your browser:
- Swagger UI (Interactive): http://127.0.0.1:8000/docs
- ReDoc (Specification): http://127.0.0.1:8000/redoc
📌 Development Status
The following checklist reflects the documented development status. Features should only be marked complete when their implementation and tests have been verified.
Vision Engine — Member 1: Vision & Intelligence
- [x] Implemented input and finding models using Pydantic.
- [x] Added evidence-reference and bounding-box models.
- [x] Added input validation for required fields and evidence requirements.
- [x] Implemented evidence file validation for existence, file type, readability, and empty files.
- [x] Implemented a deterministic mock detector.
- [x] Added mock defect scenarios for layout_overflow and broken_image.
- [x] Added a clean-page scenario that returns no findings.
- [x] Added automated tests for input validation, evidence validation, and mock detection.
- [x] Added static HTML DOM heuristics for missing or empty image sources.
- [x] Added detection of missing or empty image alt text.
- [x] Added heuristics for form controls that may lack accessible labels.
- [x] Added automated DOM detector regression tests.
- [x] Refined defect categories and finding-output validation.
- [x] Integrated a Gemini vision-language model provider.
- [x] Added VLM response parsing, validation, and failure handling.
- [x] Added screenshot preprocessing, cropping, and bounding-box coordinate translation.
- [x] Added fallback handling when screenshot crop preparation fails.
- [x] Added evaluation metrics for precision, recall, and F1 score.
- [x] Added post-repair verification support.
- [x] Added demo evidence capture and live Gemini testing scripts.
- [x] Added screenshot crop benchmarking for full-image, single-crop, and multi-crop modes.
- [x] Updated Vision Engine documentation and benchmark reports.
Vision Engine Implementation Details
Implemented Files
File	Description
vision_engine/models.py	Defines input, finding, evidence-reference, and bounding-box models.
vision_engine/evidence_validator.py	Validates evidence paths, file existence, file type, readability, and empty files.
vision_engine/detection/mock_detector.py	Provides deterministic mock defect and clean-page scenarios.
vision_engine/detection/dom_detector.py	Uses static HTML heuristics to identify image and form-label issues.
vision_engine/detection/gemini_provider.py	Integrates Gemini for screenshot-based defect detection.
vision_engine/detection/vlm_interface.py	Defines the vision-language model interface.
vision_engine/detection/vlm_response_parser.py	Parses and validates structured VLM responses.
vision_engine/prompting/vlm_prompt.py	Contains prompts and instructions for VLM-based detection.
vision_engine/image_processing.py	Handles screenshot preprocessing, cropping, and coordinate translation.
vision_engine/evaluation.py	Provides evaluation metrics, including precision, recall, and F1 score.
vision_engine/verification.py	Supports post-repair verification.
vision_engine/demo_tests/	Contains evidence capture, live Gemini testing, and benchmark scripts.
vision_engine/tests/	Contains automated regression and integration tests for Vision Engine components.
vision_engine/README.md	Documents Vision Engine architecture, setup, capabilities, and limitations.


Current Capabilities
- Accepts run identifiers, URLs, and screenshot or DOM evidence paths.
- Validates required input fields and evidence files.
- Generates deterministic mock findings for layout_overflow and broken_image.
- Detects selected image and form-label accessibility issues through static HTML analysis.
- Uses Gemini as a vision-language model provider to analyze screenshot evidence.
- Validates and parses model responses into structured findings.
- Handles selected temporary provider failures through retry logic.
- Preprocesses screenshots and supports full-image, single-crop, and multi-crop detection.
- Translates bounding-box coordinates from cropped images back to the original screenshot.
- Falls back to full-screenshot processing if crop preparation fails.
- Calculates precision, recall, and F1 score for detection evaluation.
- Supports post-repair verification.
- Includes demo scripts for capturing evidence and testing the live Gemini integration.
- Includes benchmark scripts comparing screenshot processing modes.
Current Limitations
The mock detector generates deterministic example findings and is intended for testing rather than real visual analysis.

The DOM detector performs static HTML analysis. It does not execute JavaScript, inspect the rendered page layout, fetch image URLs, or verify whether images load successfully. Its heuristic checks may produce false positives or miss issues in complex HTML structures.

Gemini-based detection depends on provider availability, valid API credentials, and model responses. Detection accuracy can vary depending on screenshot quality, prompt interpretation, and the visual complexity of the page.

The screenshot crop benchmark covered two defect scenarios across six runs. All expected defects were detected. Single-crop processing reduced image payload size by approximately 58–60% compared with full-image processing in the tested scenarios. These results are preliminary and should not be treated as a comprehensive accuracy or performance evaluation.

The latest recorded full-project regression test result was 119 passed. Rerun the test suite after further changes to verify the current state.
Browser Agent — Member 2: RPA & Browser Agent
- [x] Implemented Playwright-based browser automation using Chromium.
- [x] Added browser navigation with configurable timeout, viewport dimensions, and render wait.
- [x] Added URL and run ID validation before browser execution.
- [x] Implemented full-page screenshot capture with run-based artifact storage.
- [x] Implemented DOM snapshot capture for before-and-after stages.
- [x] Preserved the backward-compatible dom.html filename alongside the staged before_dom.html snapshot.
- [x] Added DOM metadata collection, including page URL, title, capture timestamp, element counts, tag counts, image details, form details, and interactive element details.
- [x] Added browser console error collection and JavaScript page exception tracking.
- [x] Added failed network request tracking, HTTP response status, and navigation duration.
- [x] Added structured success and failure responses, including navigation timeout handling.
- [x] Added safe browser and page resource cleanup.
- [x] Added Windows Proactor event-loop policy handling for Playwright execution on Windows.
- [x] Added automated tests for navigation, screenshots, DOM capture, metadata, evidence paths, invalid URLs, invalid run IDs, timeouts, and browser error handling.
- [x] Validated browser execution and evidence artifact creation through the backend live-pipeline tests.
- [x] Resolved integration merge conflicts and merged the Browser Agent contribution into main through GitHub PR #9.
- [ ] Complete shared evidence-contract validation with the Vision Engine.
- [ ] Complete any remaining cross-module integration review and final handover.
Browser Agent Implementation Details
The Browser Agent uses Playwright and Chromium to navigate target websites and collect structured browser evidence for the OmniSight workflow.

Implemented Capabilities
- Browser Navigation: Opens target URLs using Chromium, with configurable navigation timeout, viewport size, and render wait.
- Input Validation: Validates target URLs and run identifiers before starting browser execution.
- Screenshot Capture: Captures full-page screenshots and stores them in run-specific artifact directories.
- DOM Snapshot Generation: Captures the page HTML for before-and-after evidence stages. The before-stage capture also maintains the backward-compatible dom.html filename.
- DOM Metadata: Records the page URL, title, capture timestamp, total element count, tag counts, image information, form information, and interactive element information in JSON.
- Browser Diagnostics: Collects console errors, JavaScript page exceptions, failed network requests, HTTP response status, and navigation duration.
- Failure Handling: Handles invalid inputs, navigation timeouts, browser errors, and evidence-file creation failures through structured results.
- Resource Cleanup: Closes browser resources after successful execution or failure.
- Windows Compatibility: Applies the Windows Proactor event-loop policy before starting Playwright on Windows.
- Automated Testing: Includes unit and integration coverage for browser navigation, evidence capture, metadata, validation, diagnostics, and failure scenarios.
Standardized Evidence Contract
The Browser Agent returns structured navigation and evidence information, including:
Field	Description
run_id	Unique identifier for the browser execution
url	Final URL of the visited page
page_title	Title of the page
captured_at / timestamp	Capture timestamp in ISO-8601 format
viewport	Browser viewport width and height
screenshot_path	Path to the captured screenshot
dom_snapshot_path	Path to the generated DOM snapshot
console_errors	Collected browser console errors
page_errors	Captured JavaScript page exceptions
failed_requests	Details of failed network requests
response_status	HTTP response status, when available
navigation_duration_ms	Time taken by the navigation operation
status	Outcome of browser execution
error	Failure details, when applicable


The DOM metadata JSON also records element counts, tag counts, image details, form details, and interactive element details. These outputs provide evidence that other OmniSight components can consume and validate.
Browser Agent Testing
Automated tests cover:
- Browser launch and navigation.
- Screenshot capture and run-based artifact creation.
- Before-and-after DOM snapshot generation.
- Backward-compatible DOM artifact naming.
- DOM metadata collection and JSON output.
- Evidence paths and file existence.
- Console errors and JavaScript page exceptions.
- Failed network request tracking and HTTP response information.
- Invalid URL and invalid run ID handling.
- Navigation timeout and browser failure handling.
- Successful evidence capture when a page contains a broken image.
- Browser resource cleanup and Windows event-loop policy handling.
The Browser Agent test suite and the complete project test suite passed in the latest reported run. No exact test count is stated here because the final test count was not recorded.

The Browser Agent contribution was merged into the repository's main branch through GitHub PR #9. Further shared-contract checks with the Vision Engine and any remaining cross-module review should be completed with the relevant module owners.
Backend & API Orchestration — Member 4: Backend Developer
- [x] Initialized the FastAPI application entry point in backend/app/main.py.
- [x] Implemented GET /health endpoint verifying backend server availability.
- [x] Created POST /api/v1/runs endpoint with URL validation, whitespace stripping, and unique run_id generation.
- [x] Implemented GET /api/v1/runs/{run_id} endpoint returning run status and metadata.
- [x] Implemented GET /api/v1/runs/{run_id}/findings endpoint returning structured findings or empty lists.
- [x] Implemented an in-memory RunStore repository for managing inspection runs and defect findings.
- [x] Coordinated finding schemas (FindingResponse, EvidenceReferences) with the Vision Engine data contract.
- [x] Added deterministic mock defect findings (source="mock") for early milestone testing.
- [x] Added centralized safe application logging without exposing secrets.
- [x] Added standardized error response schemas and HTTP 400/404/422 validation handling.
- [x] Configured pytest.ini with backend testpaths and pythonpath.
- [x] Created 25 automated backend tests covering health, runs, findings, error handling, and lifecycle status consistency.
- [ ] Connect the backend run lifecycle to the live Browser Agent Playwright runner.
- [ ] Connect the backend findings retrieval to live Vision Engine inference.
- [ ] Replace temporary in-memory RunStore with persistent database models and migrations.
Backend Implementation Details
File	Description
backend/app/main.py	FastAPI application instance, router mounting, and OpenAPI metadata.
backend/app/api/health.py	Health check endpoint controller (GET /health).
backend/app/api/runs.py	Runs and findings route controllers (POST /runs, GET /runs/{id}, GET /runs/{id}/findings).
backend/app/schemas/health.py	Pydantic response schema for the /health endpoint.
backend/app/schemas/runs.py	Pydantic schemas for run creation and run response metadata.
backend/app/schemas/findings.py	Pydantic schemas for findings and evidence references matching the Vision Engine.
backend/app/schemas/errors.py	Standardized error response model for 400/404 responses.
backend/app/services/run_store.py	In-memory run and findings repository with mock findings generator.
backend/app/core/logging.py	Centralized safe application logger.
backend/tests/test_health.py	Automated unit and ASGI integration tests for /health.
backend/tests/test_runs.py	Automated tests for run creation, retrieval, findings, error cases, and consistency.
docs/backend_api.md	Comprehensive backend setup, endpoint documentation, and request/response examples.


Current Capabilities
- Validates inspection URLs with automatic whitespace stripping and 2048-character length limit.
- Generates unique run identifiers (run_<hex>) and initializes state to "queued".
- Communicates run status accurately without fabricating progress stages.
- Returns structured findings matching the team's approved categories (layout_overflow, missing_visible_element, broken_image).
- Rejects blank/whitespace run IDs with HTTP 400 and unknown run IDs with HTTP 404.
- Provides interactive Swagger documentation at /docs and ReDoc at /redoc.
Current Limitations
- In-Memory Storage: Runs and findings are stored in RAM (RunStore) and will reset if the Uvicorn server restarts.
- Single-Process: State is isolated to a single Uvicorn process and is not shared across multi-worker clusters.
- Mock Findings: Findings currently use clearly labelled mock results (source: "mock") until real VLM inference is connected.
Other Project Modules
The Self-Healing, GitHub Integration, and Frontend modules are part of the overall project. Their implementation status will be updated by their respective team members based on their actual code and test results.
📋 Development Guidelines
- Work on your assigned feature branch.
- Keep commits focused and descriptive.
- Add or update tests when changing behavior.
- Run relevant tests before pushing changes.
- Review git diff before committing.
- Do not commit secrets, local virtual environments, or generated artifacts.
- Use approved credentials and providers for external model integrations.
- Submit changes through pull requests and follow the team's review process.
🗺️ Future Roadmap
- Improve visual defect classification and finding validation.
- Expand evaluation using more defect categories and real-world test scenarios.
- Improve screenshot preprocessing and crop-selection strategies.
- Connect screenshot and DOM evidence from the Browser Agent to visual inspection.
- Develop the self-healing pipeline for candidate selector repairs.
- Integrate backend APIs and GitHub workflows.
- Develop the human-in-the-loop dashboard for reviewing findings and proposed repairs.
- Complete integration testing across the Browser Agent, Vision Engine, and Backend.
🤝 Contribution
Contributions should follow the team's assigned module responsibilities and development workflow. Keep changes scoped to your assigned work, test them where possible, and document limitations clearly.
⚖️ Current Project Limitations
OmniSight is under active development. The Vision Engine provides validated data models, evidence-file checks, deterministic mock detection, static HTML DOM heuristics, and Gemini-powered vision-language analysis.

Gemini-based detection depends on provider availability, valid API credentials, and model response quality. Its detection accuracy and performance require further evaluation across a wider range of real-world UI defects.

The Browser Agent captures browser evidence and handles common execution failures. However, full integration across the Browser Agent, Vision Engine, Backend, and dashboard still requires verification.

Automated repair generation, complete end-to-end self-healing workflows, and production-level integration remain under development.