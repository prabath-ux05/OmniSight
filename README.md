# OmniSight — Multimodal UI Self-Healing & RPA Agent

[![Live Demo on Vercel](https://img.shields.io/badge/Live%20Demo-omnisight--rho.vercel.app-00C9A7?style=for-the-badge&logo=vercel&logoColor=white)](https://omnisight-rho.vercel.app)
[![Backend Status](https://img.shields.io/badge/API%20Status-Render%20Online-10B981?style=for-the-badge&logo=render&logoColor=white)](https://omnisight-rgqc.onrender.com/health)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![Playwright](https://img.shields.io/badge/Playwright-Chromium-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-18-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://www.postgresql.org)

**OmniSight** is an enterprise-grade multimodal Robotic Process Automation (RPA) and automated UI test self-healing platform. By unifying vision-language models (VLMs), headless browser automation, and deterministic DOM analysis, OmniSight detects visual layout regressions, broken interactive elements, and dynamic selector shifts. It synthesizes resilient candidate repairs, validates them in an isolated sandbox, and submits governed pull requests for human-in-the-loop review.

---

## 🌐 Live Demo & Deployment

| Service | Environment | Live URL | Status |
|---|---|---|---|
| **Frontend Dashboard** | Vercel (React 18 + Vite) | **[https://omnisight-rho.vercel.app](https://omnisight-rho.vercel.app)** | ![Vercel](https://img.shields.io/badge/Vercel-Active-00C9A7?style=flat-square&logo=vercel) |
| **Backend API** | Render (FastAPI + Docker) | **[https://omnisight-rgqc.onrender.com](https://omnisight-rgqc.onrender.com)** | ![Render](https://img.shields.io/badge/Render-Active-10B981?style=flat-square&logo=render) |
| **API Health Probe** | Public JSON Endpoint | **[https://omnisight-rgqc.onrender.com/health](https://omnisight-rgqc.onrender.com/health)** | `HTTP 200 {"status":"ok"}` |
| **Interactive Docs** | Swagger UI | **[https://omnisight-rgqc.onrender.com/docs](https://omnisight-rgqc.onrender.com/docs)** | OpenAPI Specification |
| **Database** | Render Managed PostgreSQL | Attached persistent storage | PostgreSQL 18 + Alembic |

> **Note on Free-Tier Latency:** The backend on Render spins down after periods of inactivity. If visiting the live demo during a cold state, the initial health handshake may take ~30–50 seconds before responding. Subsequent interactions are fast.

---

## 📸 Product Preview & Working Interface

### 1. Main Dashboard & Autonomous Command Center
*The Meridian-themed command center featuring real-time telemetry, platform health monitoring, multi-viewport status indicators, and an interactive 12-column capability mosaic.*

![OmniSight Dashboard](docs/screenshots/dashboard.png)

---

### 2. Live Inspection Studio
*The dedicated Live Inspection Studio where operators initiate automated inspections across desktop, tablet, and mobile viewport presets with real-time status and telemetry.*

![Live Inspection Studio](docs/screenshots/live-inspection.png)

---

### 3. Visual Defect Detection & Finding Evidence
*Multimodal inspection results showing detected visual defects, severity badges, confidence scoring, target DOM selector references, and pixel-level screenshot evidence.*

![Inspection Findings](docs/screenshots/inspection-findings.png)

---

### 4. Self-Healing Repair Proposals & Human-in-the-Loop Governance
*Automated repair proposal workflow synthesizing resilient locator alternatives, showing review authorization states (`PENDING`, `APPROVED`, `REJECTED`), and pull request submission gates.*

![Repair Proposals](docs/screenshots/repair-proposals.png)

---

### 5. Gemini Contextual AI Repair Assistant Chat
*Interactive AI diagnostic assistant grounded in live inspection findings, DOM geometries, and locator metadata to guide developers through remediation.*

![Gemini AI Repair Chatbot](docs/screenshots/gemini-chatbot.png)

---

### 6. Visual Evidence & Verification Stage
*Detailed inspection evidence inspection showing DOM snapshots, captured assets, and side-by-side inspection evidence.*

![Visual Evidence & Verification](docs/screenshots/repair-comparison.png)

---

### 7. Historical Inspection Audit Trail
*Searchable, filterable audit log of historical inspection runs with multi-viewport indicators, duration metrics, defect counts, and CSV/PDF export capability.*

![Inspection History](docs/screenshots/inspection-history.png)

---

## ⚠️ Problem Statement & Motivation

Modern web applications undergo frequent UI iterations, A/B testing, and framework updates. These changes frequently break automated end-to-end (E2E) testing suites and RPA bots:

1. **Brittle Selectors:** Automated tests fail when CSS classes, dynamic auto-generated IDs, or DOM hierarchies shift—even when visual page functionality is completely intact.
2. **Silent Visual Regressions:** Traditional assertions miss off-screen layout overflows, overlapping text, missing graphical elements, and responsive viewport clipping.
3. **High Maintenance Overhead:** QA engineers spend countless hours manually triaging flakiness, diagnosing broken selectors, and authoring patch commits.
4. **Ungoverned Auto-Fixes:** Naive self-healing tools that mutate live production applications without safety gates create significant operational risks.

**OmniSight solves this** by pairing multimodal vision-language intelligence with deterministic DOM heuristics, strictly separating sandboxed repair synthesis from production code through human-reviewed pull requests.

---

## ✨ Key Features & Capabilities

- **Multimodal Visual Inspection:** Combines Playwright full-page screenshots with structural DOM snapshots to analyze visual appearances and underlying code simultaneously.
- **VLM Defect Detection:** Leverages Google Gemini vision models alongside deterministic DOM heuristics to detect layout overflows, broken images, and missing interactive controls.
- **Multi-Viewport Cross-Check:** Simultaneously captures and evaluates pages across Desktop (1280×800), Tablet (768×1024), and Mobile (375×667) resolutions.
- **Self-Healing Locator Synthesis:** Recommends prioritized, resilient locator alternatives (data-testid, role, ARIA, robust CSS paths) when existing selectors degrade.
- **Human-in-the-Loop Safety Gate:** Strictly isolates proposed changes into sandboxed candidates. No code is merged or committed without explicit operator authorization.
- **Automated GitHub PR Integration:** Transforms approved locator repairs into minimal unified diff patches and submits pull requests via the GitHub REST API.
- **Meridian Visual Identity System:** Modern command-center aesthetic featuring an obsidian-teal palette, layered ambient backgrounds, SVG telemetry graphics, and WCAG AA accessibility.
- **Complete Auditability:** PostgreSQL-backed audit trail with full lifecycle tracking, historical run comparisons, and CSV/PDF report exports.

---

## 🔄 How the Complete System Works

OmniSight operates through an end-to-end 5-stage automated pipeline:

```
[ 1. CAPTURE ] ──▶ [ 2. ANALYZE ] ──▶ [ 3. DIAGNOSE ] ──▶ [ 4. REPAIR ] ──▶ [ 5. VERIFY ]
  Playwright         Gemini VLM +        Deterministic      Candidate         Human Review +
  Headless           DOM Heuristic       Selector & Layout  Locator Diff      GitHub PR Gate
  Multi-Viewport     Inference           Drift Mapping      Synthesis         Verification
```

1. **Capture:** The Browser Agent launches headless Chromium via Playwright, navigates to the target URL, executes required interactions, and captures full-page screenshot buffers, raw DOM trees, and console/network logs.
2. **Analyze:** The Vision Engine evaluates visual screenshot buffers and DOM snapshots. It combines Gemini vision-language model inference with deterministic DOM heuristic checks (e.g., missing alt text, unlabelled inputs, broken assets).
3. **Diagnose:** Findings are normalized into validated Pydantic models with categories (`layout_overflow`, `missing_visible_element`, `broken_image`), confidence scores (0.0–1.0), and bounding-box coordinates.
4. **Repair:** The Self-Healing engine synthesizes candidate locator replacements and formats minimal unified diff patches for the test suite.
5. **Verify:** The operator inspects the proposed fix in the dashboard. Upon explicit approval, OmniSight can verify the patch in an isolated local sandbox and open a GitHub pull request.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Client ["Client Layer"]
        User["QA Engineer / Operator"]
        Vercel["Vercel Edge CDN<br/>(React 18 + Vite SPA)"]
        User -->|HTTPS| Vercel
    end

    subgraph Backend ["Backend Orchestration Layer (Render Docker)"]
        FastAPI["FastAPI Orchestrator<br/>(Uvicorn + Proxy Headers)"]
        Vercel -->|/api/* Rewrites| FastAPI

        subgraph Core_Services ["Core Engine Services"]
            BrowserAgent["Browser Agent<br/>(Playwright Chromium)"]
            VisionEngine["Vision Engine<br/>(Gemini VLM + DOM Heuristics)"]
            SelfHealing["Self-Healing Pipeline<br/>(Locator Synthesizer)"]
            GitIntegrator["GitHub Integration<br/>(Branch & PR Manager)"]
        end

        FastAPI --> BrowserAgent
        FastAPI --> VisionEngine
        FastAPI --> SelfHealing
        FastAPI --> GitIntegrator
    end

    subgraph Data ["Data & Storage Layer"]
        PostgreSQL[("Render Managed PostgreSQL<br/>(Runs, Findings, Proposals, Auth)")]
        Disk[("Persistent Artifact Disk<br/>(Screenshots & DOM Snapshots)")]
        FastAPI -->|SQLAlchemy 2.0 + Alembic| PostgreSQL
        BrowserAgent -->|Save Buffers| Disk
        FastAPI -->|Serve Static Artifacts| Disk
    end

    subgraph External ["External Services"]
        TargetWeb["Target Web Application"]
        GeminiAPI["Google Gemini API<br/>(VLM Inference)"]
        GitHubAPI["GitHub REST API<br/>(Pull Request Gate)"]
        BrowserAgent -->|Headless Navigation| TargetWeb
        VisionEngine -->|Visual Inspection| GeminiAPI
        GitIntegrator -->|Open Pull Request| GitHubAPI
    end
```

---

## 💻 Technology Stack

### Frontend Dashboard
- **React 18 & Vite:** Fast single-page application with modular component architecture.
- **Meridian Design Tokens:** Custom obsidian-teal (`#00C9A7`) theme with dark/light mode toggle.
- **Interactive UI Components:** Split-view comparison slider, live preview scanner, and defect highlight overlays.
- **Zero Heavy UI Libraries:** Built using standard CSS custom properties, vanilla React hooks, and SVG animation for high performance.

### Backend & Orchestration
- **FastAPI (Python 3.11 / 3.12):** Asynchronous REST API framework with automatic OpenAPI documentation.
- **Uvicorn:** ASGI web server configured with proxy header forwarding for cloud deployment.
- **Pydantic v2:** Rigorous schema validation across all request/response models and evidence payloads.
- **Argon2-cffi:** Password hashing and secure session management.

### AI & Vision Engine
- **Google Gemini 2.0 / 1.5 Flash:** Multimodal vision-language model for UI defect detection and element localization.
- **Deterministic DOM Heuristics:** Fast rule-based fallbacks for missing attributes, labels, and structural violations.
- **Pillow (PIL):** Screenshot cropping, coordinate translation, and image validation.
- **Intersection-over-Union (IoU):** Spatial evaluation metrics to benchmark detection accuracy against ground truth.

### Browser Automation & RPA
- **Playwright (Python):** Native Chromium headless automation for multi-viewport evidence capture.
- **BeautifulSoup4:** Deterministic DOM snapshot parsing and selector tree traversal.

### Database & Deployment Infrastructure
- **PostgreSQL 18:** Relational persistence for runs, findings, artifacts, proposals, and user accounts.
- **SQLAlchemy 2.0 & Alembic:** Async-capable ORM with sequential database migrations (`001` through `004`).
- **Render:** Cloud container deployment running the official Microsoft Playwright Docker runtime (`mcr.microsoft.com/playwright/python:v1.64.1-noble`).
- **Vercel:** Global edge deployment for the frontend SPA with `/api/*` reverse proxy rewrites.

---

## 📂 Project Structure

```text
OmniSight/
├── backend/                        # FastAPI application & REST services
│   ├── app/
│   │   ├── api/                    # Endpoints (runs, findings, proposals, auth, chat)
│   │   ├── core/                   # Config, security, database session setup
│   │   ├── models/                 # SQLAlchemy 2.0 ORM models
│   │   ├── schemas/                # Pydantic v2 validation contracts
│   │   └── services/               # Orchestrator, preview, and export services
│   └── tests/                      # 150+ automated backend and integration tests
│
├── vision_engine/                  # Multimodal AI & visual defect detection
│   ├── detection/                  # Gemini VLM, DOM heuristics, and mock providers
│   ├── prompting/                  # Engineered vision prompts and JSON parsers
│   ├── image_processing.py         # Screenshot cropping and coordinate mapping
│   ├── evaluation.py               # Spatial IoU evaluation and precision/recall
│   └── verification.py             # Post-repair patch verification logic
│
├── browser_agent/                  # Playwright headless browser automation
│   ├── navigation/                 # Chromium navigation, timeout handling, retries
│   ├── screenshots/                # Multi-viewport full-page image capture
│   └── evidence/                   # Structural DOM snapshots and metadata
│
├── self_healing/                   # Failure analysis & locator repair synthesizer
├── github_integration/             # Automated Git branch, commit, and PR management
│
├── frontend/                       # React 18 / Vite monitoring & review dashboard
│   ├── src/
│   │   ├── components/             # Reusable UI cards, tables, overlays, split-view
│   │   ├── hooks/                  # Custom hooks (useScrollReveal, useCursorGlow)
│   │   ├── services/api.js         # Centralized HTTP client and API integration
│   │   └── utils/                  # Router, session, and findings state helpers
│   ├── vercel.json                 # Vercel reverse proxy rewrites configuration
│   └── package.json                # Frontend dependencies and test runner
│
├── alembic/                        # Database migration scripts (001 -> 004)
├── docs/                           # Technical guides, architecture docs, screenshots
│   └── screenshots/                # Genuine application interface preview images
├── Dockerfile                      # Production Docker container (Playwright base)
├── render.yaml                     # Render Infrastructure-as-Code Blueprint
├── requirements.txt                # Pinned Python production dependencies
└── README.md                       # Repository presentation and documentation
```

---

## ⚙️ Installation & Local Setup

### Prerequisites
- **Python 3.11+** installed and available on PATH
- **Node.js 18+** and **npm**
- **Git**
- Optional: Local PostgreSQL instance (or uses SQLite for testing)

### 1. Clone the Repository
```bash
git clone https://github.com/prabath-ux05/OmniSight.git
cd OmniSight
```

### 2. Set Up Python Backend Virtual Environment
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright Chromium binaries
playwright install chromium
```

### 3. Configure Environment Variables
Copy the template configuration files:
```bash
# Backend environment configuration
cp .env.example .env

# Frontend environment configuration
cp frontend/.env.example frontend/.env
```

Fill in the required values in `.env` using placeholders as reference:

```ini
# --- Application Environment ---
APP_ENV=development
APP_DEBUG=true

# --- Database Connection ---
# Local SQLite for immediate testing:
DATABASE_URL=sqlite:///./test_omnisight.db
# Or local PostgreSQL:
# DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/omnisight_db

# --- Security & CSRF ---
CSRF_SECRET_KEY=your-minimum-32-character-high-entropy-secret-key-here
SESSION_EXPIRE_DAYS=7
COOKIE_SECURE=false

# --- AI & Vision Engine ---
VISION_MODEL_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key-here

# --- GitHub Integration (Optional) ---
GITHUB_TOKEN=your-github-personal-access-token-here
GITHUB_REPO=prabath-ux05/OmniSight
```

### 4. Run Database Migrations
```bash
alembic upgrade head
```

### 5. Start the Backend API Server
```bash
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```
*Backend Swagger UI will be available at: `http://127.0.0.1:8000/docs`*

### 6. Start the Frontend Dashboard
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
*Frontend application will open at: `http://localhost:5173`*

---

## 🧪 Running Automated Tests

OmniSight includes comprehensive automated test suites covering unit logic, integration flows, and end-to-end schemas:

```bash
# 1. Run all Python backend & vision engine tests (150+ tests)
pytest -v

# 2. Run Vision Engine specific tests
pytest vision_engine/tests -v

# 3. Run Backend API & Database tests
pytest backend/tests -v

# 4. Run Frontend unit and router tests (92 tests)
cd frontend
npm test

# 5. Verify Frontend production build
npm run build
```

---

## ☁️ Deployment Architecture

OmniSight is deployed using a modern cloud topology separating edge presentation, containerized orchestration, and managed persistence:

- **Frontend on Vercel:** Hosted as a static Single-Page Application on Vercel's global CDN. The `frontend/vercel.json` file configures clean rewrite rules that proxy `/api/*` and `/health` requests to the Render backend, preventing Cross-Origin Resource Sharing (CORS) friction and securing cookie transmission.
- **Backend on Render:** Packaged inside an official `mcr.microsoft.com/playwright/python:v1.64.1-noble` Docker container. All Linux shared graphics libraries (`libasound2`, `libgbm1`, `libnss3`) and Chromium binaries are pre-installed in the container image to prevent runtime binary lookup failures.
- **Persistent Disk:** Mounted at `/app/artifacts` on Render to preserve screenshot captures and DOM snapshots across service restarts.
- **Managed PostgreSQL:** Attached Render PostgreSQL database storing relational run histories and repair proposals, managed strictly through versioned Alembic migrations.

---

## 🛡️ Security & Responsible-Use Notes

1. **Human-in-the-Loop Safety:** OmniSight will **never** mutate target production environments directly. All self-healing repairs are formulated as candidate diffs that require explicit operator approval before generating a pull request.
2. **Sandbox Isolation:** Patch simulation and before-and-after verification execute strictly in temporary local headless sessions.
3. **Session & Cookie Security:** In production mode (`APP_ENV=production`), OmniSight enforces `HttpOnly`, `SameSite=Lax`, and `Secure` cookie attributes with cryptographic Argon2 password hashing.
4. **Secret Protection:** API keys (`GEMINI_API_KEY`, `GITHUB_TOKEN`, `CSRF_SECRET_KEY`) are managed via environment variables and never logged or serialized into client responses.
5. **Path Traversal Guards:** The artifact serving endpoint strictly validates filenames and canonical paths to prevent directory traversal outside the declared storage directory.

---

## 🔭 Future Scope

- **Autonomous Regression Test Generation:** Synthesizing complete Playwright test specifications directly from multimodal user interaction traces.
- **Expanded Vision Models:** Adding adapter support for Claude 3.5 Sonnet and GPT-4o vision backends alongside Gemini.
- **Multi-Browser Matrix:** Expanding the Browser Agent from Chromium to include Firefox and WebKit (Safari) cross-engine visual comparison.
- **Automated CI/CD Webhooks:** Direct integration with GitHub Actions to trigger self-healing diagnostic sweeps on failed test workflows.

---

## 👥 Contributors & Team Roles

OmniSight was developed as an end-to-end collaborative platform with clear domain ownership:

| Contributor / Domain | Core Modules | Responsibilities |
|---|---|---|
| **Vision & AI Intelligence** | `vision_engine/` | Gemini VLM integration, prompt engineering, spatial IoU evaluation, bounding-box parsing, and deterministic DOM heuristics. |
| **RPA & Browser Automation** | `browser_agent/` | Playwright Chromium automation, full-page screenshot capture, multi-viewport evidence streaming, and browser diagnostics. |
| **Self-Healing & Verification** | `self_healing/` | Failure pattern analysis, candidate selector synthesis, unified diff patch generation, and post-repair verification. |
| **Backend & Dashboard Architecture** | `backend/`, `github_integration/`, `frontend/` | FastAPI orchestration, PostgreSQL persistence, Alembic migrations, GitHub PR API integration, and React 18 Meridian dashboard redesign. |

---

## 📄 License & Attribution

This project is developed for portfolio, demonstration, and research purposes. All trademarks, logos, and brand icons belong to their respective owners.
