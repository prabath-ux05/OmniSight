# OmniSight - Multimodal UI Self-Healing & RPA Agent

OmniSight is an intelligent, multimodal Robotic Process Automation (RPA) and automated UI test self-healing agent. It aims to detect UI changes, diagnose broken selectors, repair test scripts, and automate GitHub pull requests.

---

## 🚀 Project Objective

OmniSight aims to solve common UI automation failures through:

1. **Multimodal Visual Inspection**: Analyzing screenshots and DOM snapshots.
2. **Autonomous Diagnosis**: Identifying broken locators and UI changes.
3. **Automated Code Self-Healing**: Generating and verifying test repairs.
4. **GitHub Integration**: Creating branches, commits, and pull requests.
5. **Human-in-the-Loop Dashboard**: Providing a web interface for reviewing fixes and monitoring execution.

---

## 📁 Repository Structure

```text
OmniSight/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── api/              # API endpoints
│   │   ├── core/             # Configuration and security
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # Business logic
│   └── tests/                # Backend tests
├── browser_agent/             # Browser automation engine
│   ├── navigation/           # Page navigation and interactions
│   ├── screenshots/          # Screenshot capture and storage
│   ├── evidence/             # DOM snapshots and browser evidence
│   └── tests/                # Browser Agent tests
├── vision_engine/             # Vision models and element detection
│   ├── detection/            # Visual element localization
│   ├── prompting/             # Vision model prompts
│   └── tests/                # Vision engine tests
├── self_healing/              # Failure analysis and repair
│   ├── analysis/             # Root cause analysis
│   ├── code_generation/      # Selector repair generation
│   └── verification/         # Patch verification
├── github_integration/        # GitHub automation
│   ├── branches/             # Branch management
│   ├── commits/              # Commit generation
│   └── pull_requests/        # Pull request creation
├── frontend/                  # Planned React dashboard
├── docs/                      # Documentation
├── tests/                     # End-to-end tests
├── .gitignore                 # Git ignore rules
├── .env.example               # Environment template
├── requirements.txt           # Python dependencies
└── README.md                  # Project documentation
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
