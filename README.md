
# OmniSight — Multimodal UI Self-Healing & RPA Agent
# OmniSight - Multimodal UI Self-Healing & RPA Agent

OmniSight is an intelligent, multimodal Robotic Process Automation (RPA) and automated UI test self-healing agent. It is designed to combine vision-language models, browser automation, and automated Git workflows to detect UI changes, diagnose broken selectors and workflows, repair test scripts, and submit self-healing pull requests.

The project currently includes a Playwright-based Browser Agent that supports page navigation, screenshot capture, DOM snapshot generation, metadata collection, browser error monitoring, and automated testing. Other major components are under development.

OmniSight is a multimodal Robotic Process Automation (RPA) and UI test self-healing project. It aims to combine vision-language models, browser automation, and GitHub workflows to detect UI changes, diagnose broken selectors, support automated test repairs, and submit changes for human review.

## 🚀 Project Objective

UI automation scripts can break when frontend layouts, DOM structures, CSS classes, or dynamic element IDs change. OmniSight aims to address these issues through:
OmniSight aims to solve common UI automation failures through:

1. **Multimodal Visual Inspection**: Analyzing screenshots and DOM snapshots.
2. **Autonomous Diagnosis**: Identifying broken locators and UI changes.
3. **Automated Code Self-Healing**: Generating and verifying test repairs.
4. **GitHub Integration**: Creating branches, commits, and pull requests.
5. **Human-in-the-Loop Dashboard**: Providing a web interface for reviewing fixes and monitoring execution.

1. **Multimodal Visual Inspection:** Analyze screenshots and DOM evidence together.
2. **Autonomous Diagnosis:** Identify potential broken locators, layout drift, and UI regressions.
3. **Automated Code Self-Healing:** Generate candidate selector repairs and test-script updates.
4. **GitHub Integration:** Support branches, commits, and pull requests for validated changes.
5. **Human-in-the-Loop Dashboard:** Provide a dashboard for reviewing findings and monitoring automation.

## 📁 Repository Structure

```text
OmniSight/
├── backend/                 # Core backend and API
├── browser_agent/           # Browser automation and evidence capture
│   └── screenshots/         # Screenshot artifacts
├── vision_engine/           # Visual inspection and defect detection
│   ├── detection/           # Detection logic
│   ├── tests/               # Vision Engine tests
│   ├── models.py            # Input and finding models
│   ├── evidence_validator.py # Evidence file validation
│   └── README.md            # Vision Engine documentation
├── self_healing/            # Failure analysis and repair pipeline
├── github_integration/      # Git and pull request workflows
├── frontend/                # Planned monitoring dashboard
├── docs/                    # Project documentation
├── tests/                   # Project-level tests
├── .gitignore               # Git ignore rules
├── .env.example             # Environment variable template
├── requirements.txt         # Python dependencies
└── README.md                # Main project documentation
```

The structure above highlights the main modules. Individual modules may contain additional files and directories.

## 👥 Team Module Distribution

| Member | Module | Responsibilities |
|---|---|---|
| Member 1: Vision & Intelligence | `vision_engine/` | Visual defect detection, model integration, prompt engineering, and element localization |
| Member 2: RPA & Browser Agent | `browser_agent/` | Browser navigation, action execution, screenshots, and DOM capture |
| Member 3: Self-Healing & Verification | `self_healing/` | Failure analysis, selector repair, and patch verification |
| Member 4: Backend & GitHub Integration | `backend/`, `github_integration/` | API orchestration, Git workflows, pull requests, and application state |

## 🛠️ Setup

### 1. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure environment variables

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Configure only the environment variables required for your assigned work. Never commit `.env` files, API keys, or access tokens. External model integrations must use team-approved providers and authorized credentials.

### 4. Run tests

From the repository root:

```bash
python -m pytest -v
```

Review the test output to confirm which tests passed.

## 📌 Development Status

### Foundation

- [x] Initial repository structure established.
- [x] Baseline Python dependencies defined.
- [x] Environment variable template created.
- [x] Git ignore rules configured.
- [x] Vision Engine input and finding models implemented.
- [x] Deterministic mock detector implemented.
- [x] Evidence file validation implemented and integrated.
- [x] Initial Vision Engine tests added.

### Planned Work

- [ ] Finalize shared input/output contracts across modules.
- [ ] Implement a clean-page mock scenario and additional tests.
- [ ] Integrate an approved vision-language model.
- [ ] Implement browser automation and evidence capture.
- [ ] Implement self-healing analysis and verification.
- [ ] Develop backend orchestration endpoints.
- [ ] Implement GitHub branch and pull request workflows.
- [ ] Develop the monitoring dashboard.
- [ ] Run end-to-end integration tests.

This checklist reflects the current development baseline and planned work. Features should only be marked complete after implementation and verification.

## 🔒 Development Guidelines

- Work on the feature branch assigned to your module.
- Agree on shared schemas before changing interfaces used by other modules.
- Keep mock output separate from actual model-generated findings.
- Add tests for new behavior and failure cases.
- Run tests and inspect `git diff` before committing.
- Never commit credentials or secrets.
- Push changes to your feature branch and submit a pull request for review.
- Merge into `main` only with team approval.

## 🗺️ Roadmap

1. **Foundation:** Data models, evidence validation, and deterministic mock detection.
2. **Detection:** Refine defect categories and output validation.
3. **Model Integration:** Connect an approved vision-language model when access is available.
4. **Self-Healing:** Analyze failures and generate candidate repairs.
5. **Verification:** Validate proposed repairs before they are accepted.
6. **Integration:** Connect the browser agent, backend, and GitHub workflows.
7. **Handover:** Complete testing, document limitations, and prepare a reproducible demonstration.

## ⚠️ Current Limitations

OmniSight is under active development. The current Vision Engine mock detector does not analyze screenshot pixels or DOM content to detect real defects. Evidence validation checks file existence, file type, and readability, but does not establish that evidence contains valid image data or meaningful HTML.

Actual model inference, automated repair, and end-to-end workflows should not be considered complete until implemented and tested.
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── core/             # Configuration and security
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # Business logic
│   └── tests/                # Backend tests
├── browser_agent/            # Browser automation engine
│   ├── navigation/           # Page navigation and interactions
│   ├── screenshots/          # Screenshot capture and storage
│   ├── evidence/             # DOM snapshots and browser evidence
│   └── tests/                # Browser Agent tests
├── vision_engine/            # Vision models and element detection
│   ├── detection/            # Visual element localization
│   ├── prompting/            # Vision model prompts
│   └── tests/                # Vision engine tests
├── self_healing/             # Failure analysis and repair
│   ├── analysis/             # Root cause analysis
│   ├── code_generation/      # Selector repair generation
│   └── verification/         # Patch verification
├── github_integration/       # GitHub automation
│   ├── branches/             # Branch management
│   ├── commits/              # Commit generation
│   └── pull_requests/        # Pull request creation
├── frontend/                 # Planned React dashboard
├── docs/                     # Documentation
├── tests/                    # End-to-end tests
├── .gitignore                # Git ignore rules
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
└── README.md                 # Project documentation
```

---

## 👥 Module Distribution (4-Member Collaborative Setup)

| Member / Focus Area | Primary Modules | Responsibilities |
| :--- | :--- | :--- |
| **Member 1: Vision & Intelligence** | `vision_engine/` | Vision model integration, element detection, and prompt engineering. |
| **Member 2: RPA & Browser Agent** | `browser_agent/` | Playwright automation, navigation, screenshots, DOM snapshots, metadata collection, error handling, and unit testing. |
| **Member 3: Self-Healing & Verification** | `self_healing/` | Failure analysis, selector repair, and patch verification. |
| **Member 4: Backend & GitHub Integration** | `backend/`, `github_integration/` | FastAPI APIs, backend orchestration, and GitHub branch and pull request automation. |

---

## 🛠️ Setup & Development Status

### Current Status

- [x] Initial repository structure and dependencies configured
- [x] `.env.example` and `.gitignore` created
- [x] Playwright browser navigation implemented
- [x] Screenshot capture and artifact storage implemented
- [x] DOM snapshot and browser evidence capture implemented
- [x] Metadata collection (URL, title, timestamp, viewport)
- [x] Browser console errors and JavaScript exceptions captured
- [x] Navigation timeout handling and invalid URL validation
- [x] Safe browser cleanup and Browser Agent unit tests
- [ ] Environment configuration (`.env`)
- [ ] Backend APIs and services implementation
- [ ] Vision model inference pipeline
- [ ] Self-healing and verification pipeline
- [ ] GitHub integration
- [ ] React dashboard

### Baseline Setup

**1. Create and activate a virtual environment**

```bash
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# macOS/Linux
source .venv/bin/activate
```

**2. Install dependencies and the Chromium browser**

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

**3. Configure environment variables**

```bash
# Windows (PowerShell)
Copy-Item .env.example .env

# macOS/Linux
cp .env.example .env
```

Edit `.env` with your required configuration and API keys.

**4. Run tests**

```bash
pytest
```
