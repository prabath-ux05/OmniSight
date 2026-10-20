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
├── backend/                       # Backend and API
│   ├── app/                       # Backend application components
│   │   ├── api/                   # API endpoints
│   │   ├── core/                  # Configuration and security
│   │   ├── schemas/               # Request and response schemas
│   │   └── services/              # Business logic
│   └── tests/                     # Backend tests
├── browser_agent/                 # Browser automation and evidence capture
│   ├── navigation/                # Navigation and browser interactions
│   ├── screenshots/               # Screenshot artifacts
│   ├── evidence/                  # DOM snapshots and browser evidence
│   └── tests/                     # Browser Agent tests
├── vision_engine/                 # Visual inspection and defect detection
│   ├── detection/                 # Detection logic and mock detector
│   ├── tests/                     # Vision Engine tests
│   ├── models.py                  # Input and finding models
│   ├── evidence_validator.py      # Evidence file validation
│   └── README.md                  # Vision Engine documentation
├── self_healing/                  # Failure analysis and repair pipeline
│   ├── analysis/                  # Root cause analysis
│   ├── code_generation/            # Candidate repair generation
│   └── verification/              # Repair verification
├── github_integration/            # GitHub and Git workflow automation
│   ├── branches/                  # Branch management
│   ├── commits/                   # Commit workflows
│   └── pull_requests/             # Pull request workflows
├── frontend/                      # Planned monitoring dashboard
├── docs/                          # Project documentation
├── tests/                         # Project-level and integration tests
├── .gitignore                     # Git ignore rules
├── .env.example                   # Environment variable template
├── requirements.txt               # Python dependencies
└── README.md                      # Main project documentation
```

This structure describes the project's intended and documented modules. Individual modules may contain additional files and directories, and some listed components may still be under development.

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

From the repository root:

```bash
python -m pytest -v
```

Review the test output to confirm which tests passed. Some test suites may require additional dependencies or configuration.

## 📌 Development Status

The following checklist reflects the documented project status. Features should only be marked complete when their implementation and tests have been verified.

### Foundation and Vision Engine

- [x] Initial repository structure and baseline dependencies documented.
- [x] Environment variable template and Git ignore rules configured.
- [x] Vision Engine input and finding models implemented.
- [x] Deterministic mock detector implemented.
- [x] Evidence file validation implemented and integrated.
- [x] Tests for input validation, evidence validation, and mock detection added.
- [x] Clean-page mock scenario implemented.
- [ ] Integrate an approved vision-language model.
- [ ] Refine defect categories and output validation.
- [ ] Implement
