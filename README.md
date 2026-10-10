# OmniSight - Multimodal UI Self-Healing & RPA Agent

OmniSight is an intelligent, multimodal Robotic Process Automation (RPA) and automated UI test self-healing agent. By combining vision-language models, browser automation, and automated Git workflows, OmniSight dynamically detects UI changes, diagnoses broken selectors/flows, repairs test scripts, and automatically submits self-healing pull requests.

---

## 🚀 Project Objective

Modern UI automation scripts frequently break due to minor frontend updates, DOM changes, dynamic element IDs, and CSS restructuring. OmniSight solves this by:

1. **Multimodal Visual Inspection**: Inspecting web applications through visual screenshots and DOM trees simultaneously.
2. **Autonomous Diagnosis**: Identifying broken locators, layout drift, and UI regressions using vision models.
3. **Automated Code Self-Healing**: Generating repaired selector strategies and test script updates.
4. **Seamless GitHub Integration**: Creating dedicated branches, committing validated fixes, and opening automated pull requests with visual diff reports.
5. **Human-in-the-Loop Dashboard**: Offering a streamlined web dashboard for review, manual execution overrides, and telemetry.

---

## 📁 Repository Structure

```text
OmniSight/
├── backend/                  # Core FastAPI backend application
│   ├── app/
│   │   ├── api/              # API endpoints and route handlers
│   │   ├── core/             # Configuration, logging, and security
│   │   ├── schemas/          # Pydantic data schemas
│   │   └── services/         # Application business logic
│   └── tests/                # Backend unit and integration tests
├── browser_agent/            # RPA automation & browser execution engine
│   ├── navigation/           # Action runners, click/type/scroll routines
│   ├── screenshots/          # Screen capture artifacts and storage
│   └── tests/                # Browser automation test suites
├── vision_engine/            # Multimodal vision and locator models
│   ├── detection/            # Bounding box and visual element localization
│   ├── prompting/            # Vision model prompts and structured outputs
│   └── tests/                # Vision engine evaluations
├── self_healing/             # Self-healing analysis and repair pipeline
│   ├── analysis/             # Root cause failure analysis and DOM/visual diff
│   ├── code_generation/      # Automated code and selector repair generator
│   └── verification/         # Pre-commit patch execution & verification
├── github_integration/       # Automated version control workflow
│   ├── branches/             # Branch creation and management
│   ├── commits/              # Code patching and commit generation
│   └── pull_requests/        # Pull request creation and PR descriptions
├── frontend/                 # Future React-based control and monitoring dashboard
├── docs/                     # Architectural specs, API docs, and guides
├── tests/                    # End-to-end integration test suites
├── .gitignore                # Git ignore rules for Python, Node, and secrets
├── .env.example              # Environment variables template
├── requirements.txt          # Baseline Python dependencies
└── README.md                 # Project documentation
```

---

## 👥 Module Distribution (4-Member Collaborative Setup)

The architecture is modularized to support concurrent development across four team members:

| Member / Focus Area | Primary Modules | Responsibilities |
| :--- | :--- | :--- |
| **Member 1: Vision & Intelligence** | `vision_engine/` | Multimodal model integration, element detection, prompt engineering, visual bounding boxes. |
| **Member 2: RPA & Browser Agent** | `browser_agent/` | Browser automation runtime, page navigation, screenshot capture, DOM serialization. |
| **Member 3: Self-Healing & Verification** | `self_healing/` | Failure analysis, selector repair generator, patch verification test runner. |
| **Member 4: Backend & GitHub Integration** | `backend/`, `github_integration/` | FastAPI orchestration APIs, branch/PR automation, state management, frontend preparation. |

---

## 🛠️ Setup & Development Status

### Current Status
- [x] Initial monorepo layout and directory scaffolding established
- [x] Baseline dependencies defined (`requirements.txt`)
- [x] Environment configuration blueprint created (`.env.example`)
- [x] Version control rules configured (`.gitignore`)
- [ ] Environment variable configuration (`.env`)
- [ ] Core backend endpoints and services implementation
- [ ] Browser automation driver setup (Playwright / Selenium)
- [ ] Vision model inference pipeline setup
- [ ] Self-healing verification loop implementation
- [ ] GitHub App / personal access token integration
- [ ] Frontend React dashboard scaffolding

### Baseline Setup

1. **Create and activate a Python virtual environment**:
   ```bash
   python -m venv .venv
   # Windows (PowerShell):
   .venv\Scripts\Activate.ps1
   # macOS/Linux:
   source .venv/bin/activate
   ```

2. **Install baseline dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your local settings and API keys
   ```

4. **Verify Installation**:
   ```bash
   pytest
   ```
