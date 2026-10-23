# OmniSight — Multimodal UI Self-Healing & RPA Agent

OmniSight is an intelligent, multimodal Robotic Process Automation (RPA) and automated UI test self-healing project. It aims to combine vision-language models, browser automation, and Git workflows to detect UI changes, diagnose broken selectors and workflows, generate candidate test repairs, and submit changes for human review.

The project includes a Playwright-based Browser Agent for browser navigation, screenshot capture, DOM snapshot generation, metadata collection, browser error monitoring, and automated testing. The Vision Engine provides input and finding models, evidence validation, and deterministic mock defect detection. Other components are under active development.

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
│   │   └── mock_detector.py
│   ├── tests/
│   │   ├── test_evidence_validator.py
│   │   └── test_mock_detector.py
│   ├── models.py
│   ├── evidence_validator.py
│   └── README.md
├── backend/                     # Backend and API
├── browser_agent/               # Browser automation and evidence capture
│   ├── navigation/              # Browser navigation and interactions
│   ├── screenshots/             # Screenshot capture and artifacts
│   ├── evidence/                 # DOM snapshots and execution evidence
│   └── tests/                   # Browser Agent automated tests
├── self_healing/                # Failure analysis and repair pipeline
├── github_integration/          # GitHub and Git workflow automation
├── frontend/                    # Planned monitoring dashboard
├── docs/                        # Project documentation
├── tests/                       # Project-level and integration tests
├── artifacts/                   # Generated browser execution artifacts
├── .gitignore
├── .env.example
├── requirements.txt
└── README.md
```

The tree lists the implemented Vision Engine files and the Browser Agent module structure. Other project modules are shown at a high level and may contain additional files maintained by their respective team members.

## 👥 Team Module Distribution

| Member / Focus Area | Primary Modules | Responsibilities |
|---|---|---|
| Member 1: Vision & Intelligence | `vision_engine/` | Visual defect detection, input/output models, evidence validation, model integration, prompt engineering, and element localization |
| Member 2: RPA & Browser Agent | `browser_agent/` | Playwright navigation, browser interactions, screenshots, DOM snapshots, metadata collection, browser error handling, and testing |
| Member 3: Self-Healing & Verification | `self_healing/` | Failure analysis, candidate selector repairs, repair generation, and patch verification |
| Member 4: Backend & GitHub Integration | `backend/`, `github_integration/` | API orchestration, backend services, Git workflows, branch management, pull requests, and application state |

## 🛠️ Setup

### Prerequisites

- Python installed and available in the terminal.
- Git installed and configured.
- Access to the OmniSight repository.
- Playwright and its required browser installed for Browser Agent work.

### 1. Clone the Repository

If you have not cloned the repository yet:

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

Run this command from the repository root:

```bash
python -m pip install -r requirements.txt
```

### 4. Install the Playwright Chromium Browser

For Browser Agent development, install Chromium using:

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

Run the relevant module tests when working on an individual component. Review the test output to confirm which tests passed. Some test suites may require additional dependencies or configuration.

## 📌 Development Status

The following checklist reflects the documented Vision Engine and Browser Agent development status. Features should only be marked complete when their implementation and tests have been verified.

### Vision Engine — Member 1: Vision & Intelligence

- [x] Implemented input and finding models using Pydantic.
- [x] Added evidence-reference and bounding-box models.
- [x] Added input validation for required fields and evidence requirements.
- [x] Implemented evidence file validation for existence, file type, readability, and empty files.
- [x] Implemented a deterministic mock detector.
- [x] Added a mock defect scenario for `layout_overflow` and `broken_image`.
- [x] Added a clean-page scenario that returns no findings.
- [x] Added automated tests for input validation, evidence validation, and mock detection.
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

#### Current Capabilities

- Accepts a run identifier, URL, and optional screenshot and DOM snapshot paths, requiring at least one evidence path.
- Validates required input fields and rejects blank `run_id` and `url` values.
- Checks whether supplied evidence files exist, are regular files, can be opened, and are non-empty.
- Produces example findings for `layout_overflow` and `broken_image` in the mock defect scenario.
- Returns an empty findings list in the mock clean scenario.
- Represents findings with category, severity, confidence, description, and evidence references.
- Preserves the provided evidence references in mock findings.

#### Current Limitations

The mock detector does not analyze screenshot pixels or DOM content to identify real defects. Its findings are deterministic examples for testing. Evidence validation checks basic file accessibility and non-empty content, but does not verify the semantic validity of image or DOM data. Real vision-language model integration is not yet implemented.

The latest confirmed development test result documented for the Vision Engine was **36 passed**. Run the Vision Engine test command again to verify the current state.

### Browser Agent — Member 2: RPA & Browser Automation

#### Implementation Status

- [x] Implemented Playwright-based browser automation using Chromium.
- [x] Implemented navigation to target URLs.
- [x] Added page title and metadata collection.
- [x] Implemented full-page screenshot capture and run-based artifact storage.
- [x] Implemented DOM snapshot capture.
- [x] Added metadata collection for URL, page title, viewport information, and ISO-8601 timestamps.
- [x] Implemented browser console error collection.
- [x] Added JavaScript page exception tracking.
- [x] Implemented invalid URL validation.
- [x] Added navigation timeout handling.
- [x] Implemented structured failure responses and safe browser resource cleanup.
- [x] Defined a standardized evidence contract.
- [x] Developed automated tests for Browser Agent functionality.
- [x] Prepared setup, usage, evidence structure, and integration documentation.

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
- **Automated Testing:** Covers navigation, screenshots, DOM capture, metadata, artifact creation, evidence validation, timeout scenarios, invalid URLs, and browser cleanup.
- **Documentation:** Includes Playwright installation, test execution, evidence structure, and integration guidelines.

#### Standardized Evidence Contract

The Browser Agent defines a structured evidence contract containing the following information:

| Field | Description |
|---|---|
| `run_id` | Identifier associated with the browser execution |
| `url` | URL associated with the page execution |
| `page_title` | Title of the captured page |
| `captured_at` | Timestamp associated with evidence capture |
| `viewport` | Browser viewport information |
| `screenshot_path` | Reference to the captured screenshot |
| `dom_snapshot_path` | Reference to the generated DOM snapshot |
| `console_errors` | Collected browser console errors |
| `page_errors` | Captured JavaScript page exceptions |
| `status` | Indicates the outcome of browser execution |
| `error` | Details about failures, including navigation and timeout errors |

This contract allows the Vision Engine and other components to consume browser execution evidence through a consistent structure.

#### Browser Agent Testing

Automated tests were developed to verify:

- Browser launch and navigation.
- Screenshot capture and artifact creation.
- DOM snapshot generation.
- Metadata collection.
- Evidence contract compliance.
- Console error and JavaScript exception collection.
- Invalid URL handling and navigation timeouts.
- Structured failure responses and safe browser cleanup.

The Browser Agent implementation and its automated tests are documented as completed. Run the relevant test suite to verify the current state before integration or release.

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