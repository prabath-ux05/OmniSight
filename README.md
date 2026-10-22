# OmniSight — Multimodal UI Self-Healing & RPA Agent

OmniSight is an intelligent, multimodal Robotic Process Automation (RPA) and automated UI test self-healing project. It aims to combine vision-language models, browser automation, and Git workflows to detect UI changes, diagnose broken selectors and workflows, generate candidate test repairs, and submit changes for human review.

The project includes a Playwright-based Browser Agent for browser navigation, screenshot capture, DOM snapshot generation, metadata collection, browser error monitoring, and automated testing. The Vision Engine provides input and finding models, evidence validation, deterministic mock defect detection, and static HTML DOM heuristics for identifying selected image and form-label issues. Other components are under active development.

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
├── vision_engine/
│   ├── detection/
│   │   ├── dom_detector.py
│   │   └── mock_detector.py
│   ├── tests/
│   │   ├── test_dom_detector.py
│   │   ├── test_evidence_validator.py
│   │   └── test_mock_detector.py
│   ├── models.py
│   ├── evidence_validator.py
│   └── README.md
├── backend/                       # Backend and API (team development)
├── browser_agent/                 # Browser automation and evidence capture
│   ├── navigation/                # Browser navigation and interactions
│   ├── screenshots/               # Screenshot capture and artifacts
│   ├── evidence/                  # DOM snapshots and execution evidence
│   └── tests/                     # Browser Agent automated tests
├── self_healing/                  # Failure analysis and repair pipeline
├── github_integration/            # GitHub and Git workflow automation
├── frontend/                      # Planned monitoring dashboard
├── docs/                          # Project documentation
├── tests/                         # Project-level and integration tests
├── artifacts/                     # Generated browser execution artifacts (local)
├── .gitignore
├── .env.example
├── requirements.txt
└── README.md
```

The tree lists the implemented Vision Engine files and the Browser Agent module structure. The other project modules are shown at a high level and may contain additional files maintained by their respective team members.

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

### 1. Clone the repository

If you have not cloned the repository yet:

```bash
git clone https://github.com/prabath-ux05/OmniSight.git
cd OmniSight
```

If you already have the repository locally, open its root directory instead of cloning it again.

### 2. Create and activate a virtual environment

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

### 3. Install Python dependencies

Run from the repository root:

```bash
python -m pip install -r requirements.txt
```

### 4. Install the Playwright Chromium browser

For Browser Agent development, install Chromium using:

```bash
python -m playwright install chromium
```

### 5. Configure environment variables

**Windows PowerShell:**

```powershell
Copy-Item .env.example .env
```

**macOS/Linux:**

```bash
cp .env.example .env
```

Configure only the environment variables required for your assigned work. Never commit `.env` files, API keys, passwords, or access tokens. External model integrations must use team-approved providers and authorized credentials.

### 6. Run tests

Run the full test suite from the repository root:

```bash
python -m pytest -v
```

To run only the Vision Engine tests:

```bash
python -m pytest ./vision_engine/tests -q
```

Review the test output to confirm which tests passed. Some test suites may require additional dependencies or configuration.

## 📌 Development Status

The following checklist reflects the documented Vision Engine development status. Features should only be marked complete when their implementation and tests have been verified.

### Vision Engine — Member 1: Vision & Intelligence

- [x] Implemented input and finding models using Pydantic.
- [x] Added evidence-reference and bounding-box models.
- [x] Added input validation for required fields and evidence requirements.
- [x] Implemented evidence file validation for existence, file type, readability, and empty files.
- [x] Implemented a deterministic mock detector.
- [x] Added a mock defect scenario for `layout_overflow` and `broken_image`.
- [x] Added a clean-page scenario that returns no findings.
- [x] Added automated tests for input validation, evidence validation, and mock detection.
- [x] Added static HTML DOM heuristics for missing or empty image sources.
- [x] Added detection of missing or empty image alt text.
- [x] Added heuristics for form controls that may lack accessible labels.
- [x] Added automated DOM detector regression tests.
- [ ] Refine defect categories and finding-output validation.
- [ ] Integrate an approved vision-language model when provider access is available.
- [ ] Validate real model responses and expand failure-handling tests.

### Vision Engine Implementation Details

#### Implemented Files

| File | Description |
|---|---|
| `vision_engine/models.py` | Defines the input, finding, evidence-reference, and bounding-box models. |
| `vision_engine/evidence_validator.py` | Checks evidence paths, file existence, file type, readability, and empty files. |
| `vision_engine/detection/mock_detector.py` | Provides deterministic mock defect and clean-page scenarios. |
| `vision_engine/tests/test_evidence_validator.py` | Covers evidence-validation behavior and failure cases. |
| `vision_engine/tests/test_mock_detector.py` | Covers mock detection scenarios and evidence-validation failures. |
| `vision_engine/README.md` | Documents the Vision Engine module and its current capabilities. |
| `vision_engine/detection/dom_detector.py` | Uses static HTML heuristics to identify selected image and form-label issues. |
| `vision_engine/tests/test_dom_detector.py` | Tests DOM issue detection, label recognition, input edge cases, and evidence references. |

#### Current Capabilities

- Accepts a run identifier, URL, and optional screenshot and DOM snapshot paths, requiring at least one evidence path.
- Validates required input fields and rejects blank `run_id` and `url` values.
- Checks whether supplied evidence files exist, are regular files, can be opened, and are non-empty.
- Produces example findings for `layout_overflow` and `broken_image` in the mock defect scenario.
- Returns an empty findings list in the mock clean scenario.
- Represents findings with category, severity, confidence, description, and evidence references.
- Preserves the provided evidence references in mock findings.
- Scans saved HTML for image elements with missing or empty `src` attributes.
- Identifies image elements with missing or empty `alt` text.
- Flags form controls that may lack accessible labels.
- Recognizes common label indicators, including explicit `<label for="...">` references, wrapping labels, `aria-label`, and `aria-labelledby`.

#### Current Limitations

The mock detector generates deterministic example findings for testing and does not analyze real screenshot pixels to identify visual defects. The DOM detector performs static HTML analysis to identify potential issues, including missing or empty image sources, missing image alt text, and potentially unlabelled form controls. It recognizes common labeling mechanisms such as explicit labels, wrapping labels, `aria-label`, and `aria-labelledby`.

The DOM detector does not execute JavaScript, inspect the rendered page layout, fetch image URLs, or verify whether images load successfully. Its heuristic checks may produce false positives or miss issues in complex HTML structures. Evidence validation checks basic file accessibility and non-empty content but does not establish the semantic validity of image or DOM data. Real vision-language model integration is not yet implemented.

The latest locally confirmed Vision Engine test result was **47 passed**. Rerun the Vision Engine tests to verify the current state.

### Browser Agent — Member 2: RPA & Browser Agent

- [x] Implemented Playwright-based browser automation using Chromium.
- [x] Added browser launch, page navigation, page title retrieval, and URL collection.
- [x] Implemented full-page screenshot capture and run-based artifact storage.
- [x] Added DOM snapshot generation and evidence storage.
- [x] Implemented metadata collection, including URL, page title, ISO-8601 timestamp, and viewport dimensions.
- [x] Added browser console error collection and JavaScript page exception tracking.
- [x] Implemented invalid URL validation and navigation timeout handling.
- [x] Added structured success and failure responses.
- [x] Implemented safe browser cleanup on success and failure.
- [x] Standardized the evidence contract, including run ID, artifact paths, metadata, errors, status, and failure details.
- [x] Added automated tests for navigation, screenshots, DOM capture, metadata, and evidence validation.
- [x] Added tests for invalid URLs, missing run IDs, timeout handling, and artifact existence.
- [x] Added a local HTML test page and temporary HTTP server for repeatable browser testing.
- [x] Updated Git ignore rules to exclude generated browser artifacts from version control.
- [x] Documented Playwright installation, usage, testing, evidence structure, and integration requirements.
- [ ] Integrate the Browser Agent with the Vision Engine.
- [ ] Integrate browser execution and evidence collection with the Backend.
- [ ] Complete end-to-end testing across the integrated modules.
- [ ] Perform final integration review and project handover.

#### Browser Agent Implementation Details

The Browser Agent provides a Playwright-based browser automation module that captures browser execution evidence for use by other OmniSight components.

**Implemented Capabilities**

- **Browser Navigation:** Launches Chromium and navigates to target URLs.
- **Screenshot Capture:** Captures full-page screenshots and stores artifacts organized by run.
- **DOM Snapshot Generation:** Captures DOM evidence for further inspection by the Vision Engine.
- **Metadata Collection:** Records the current URL, page title, viewport information, and ISO-8601 timestamps.
- **Error Monitoring:** Collects browser console errors and JavaScript page exceptions.
- **Failure Handling:** Validates URLs, handles navigation timeouts, returns structured failure information, and safely closes browser resources.
- **Evidence Contract:** Standardizes browser execution results for integration with other modules.
- **Automated Testing:** Covers navigation, screenshots, DOM capture, metadata, artifact creation, evidence validation, invalid URLs, timeout handling, and browser cleanup.
- **Local Test Environment:** Includes a local HTML test page and temporary HTTP server for repeatable browser tests without relying on external websites.
- **Generated Artifacts:** Excludes generated browser evidence from Git tracking to keep the repository clean.
- **Documentation:** Includes Playwright installation, test execution, evidence structure, and integration guidelines.

#### Standardized Evidence Contract

The Browser Agent defines a structured evidence contract containing:

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
| `status` | Outcome of browser execution |
| `error` | Failure details, when applicable |

This contract allows the Vision Engine and other components to consume browser execution evidence through a consistent structure.

#### Browser Agent Testing

Automated tests cover:

- Browser launch and navigation.
- Screenshot capture and artifact creation.
- DOM snapshot generation.
- Metadata collection.
- Evidence contract validation.
- Console error and JavaScript exception collection.
- Invalid URL and missing run ID handling.
- Navigation timeout handling.
- Successful capture when the page contains a broken image.
- Artifact existence and structured failure responses.
- Safe browser cleanup.

A local test page and temporary HTTP server support repeatable testing. The full test suite should be run before integration or release to verify the current state.

The Browser Agent implementation and its automated tests have been completed according to the current development progress. Run the relevant test suite to verify the current state before integration or release.

### Other Project Modules

The Self-Healing, Backend, GitHub Integration, and Frontend modules are part of the overall project. Their implementation status should be updated by their respective team members based on their actual code and test results.

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

- Integrate an approved vision-language model into the Vision Engine.
- Improve visual defect classification and finding validation.
- Connect screenshot and DOM evidence from the Browser Agent to visual inspection.
- Develop the self-healing pipeline for candidate selector repairs.
- Integrate backend APIs and GitHub workflows.
- Develop the human-in-the-loop dashboard for reviewing findings and proposed repairs.

## 🤝 Contribution

Contributions should follow the team's assigned module responsibilities and development workflow. Keep changes scoped to your assigned work, test them where possible, and document limitations clearly.

## ⚖️ Current Project Limitations

OmniSight is under active development. The Vision Engine currently provides validated data models, evidence-file checks, and deterministic mock detection. End-to-end visual analysis, automated repair generation, and full integration across all modules depend on further development and testing.
