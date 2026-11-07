# OmniSight Frontend Dashboard Documentation

## 1. Overview & Architecture

The OmniSight Frontend Dashboard is a modern, responsive web application built with **React 18** and **Vite**. It provides an intuitive interface for QA engineers, RPA developers, and team leads to:
1. Dispatch and monitor automated browser inspection runs.
2. Inspect detected UI defects, visual screenshots, and captured DOM snapshots.
3. Review audit logs in the PostgreSQL-backed Run History table.
4. Review, approve, or reject autonomous self-healing repair proposals with Human-in-the-Loop governance.

---

## 2. Component Hierarchy & Responsibilities

```
App.jsx (Main Application Coordinator & State Container)
├── Header.jsx (App branding & backend connection health indicator)
├── Navigation Tabs (Tri-view view switcher: Live, History, Proposals)
├── Alert.jsx (Dismissible toast-style alerts for successes and errors)
│
├── [TAB 1: Live Inspection & Evidence]
│   ├── InspectionForm.jsx (Target URL input with demo defect state presets)
│   ├── RunStatusCard.jsx (Active run status pill, progress, lookup & execute controls)
│   └── Dashboard Split Grid:
│       ├── FindingsSection.jsx (Categorized defect findings list & repair buttons)
│       └── EvidenceSection.jsx (Screenshot viewer, DOM link, & self-healing panel)
│           └── RepairProposalWorkflow.jsx (Single-finding diff generation & PR submission)
│
├── [TAB 2: Run History]
│   └── InspectionHistoryTable.jsx (PostgreSQL audit log with URL/status filtering)
│
└── [TAB 3: Repair Proposals]
    └── RepairProposalWorkflow.jsx (Run-level proposal governance, reviewer notes & approval)
```

---

## 3. Component Details

### `Header.jsx`
- Displays the OmniSight logo, platform title, and real-time backend health badge (`Online` / `Offline`).
- Calls `GET /health` periodically and on user click.

### `InspectionForm.jsx`
- Accepts custom target URLs or provides one-click demo presets (`Clean`, `Overflow`, `Missing Element`, `Broken Image`, `All Defects`).
- Validates URL syntax before dispatching `POST /api/v1/runs?auto_execute=true`.

### `RunStatusCard.jsx`
- Renders the active `run_id`, target URL, and current lifecycle badge (`QUEUED`, `CAPTURING`, `ANALYZING`, `COMPLETED`, `FAILED`).
- Provides controls to toggle auto-polling, manually refresh status, or lookup a past Run ID.

### `FindingsSection.jsx`
- Fetches and displays detected defect cards from `GET /api/v1/runs/{run_id}/findings`.
- Badges categorize severity (`critical`, `high`, `medium`, `low`) and defect types (`layout_overflow`, `missing_visible_element`, `broken_image`).
- Includes a developer toggle for clean inspection vs. mock test data.

### `EvidenceSection.jsx`
- Fetches and renders full-resolution screenshots (`GET /api/v1/artifacts/{run_id}/before.png`) with responsive image loading spinners and missing file fallbacks.
- Provides a one-click link to view captured DOM HTML.
- Embeds the **Self-Healing Locator Repair Engine** panel, displaying ranked alternative locators, uniqueness scores, snapshot DOM matches, and live-page verification results.

### `InspectionHistoryTable.jsx`
- Connects to `GET /api/v1/runs` to display all runs persisted in PostgreSQL.
- Offers interactive search by Run ID or Target URL, status dropdown filters, and one-click inspection selection.

### `RepairProposalWorkflow.jsx`
- **Single-Finding PR Mode** (when embedded in `EvidenceSection`): Generates safe minimal unified diffs and prepares approval-gated GitHub PRs (supporting offline dry-run simulation).
- **Run Proposals Dashboard Mode** (when viewing Tab 3): Displays all proposals for the active run, filter pills by review status, reviewer justification text inputs, and Approve (`POST /api/v1/proposals/{id}/approve`) / Reject (`POST /api/v1/proposals/{id}/reject`) action buttons.

---

## 4. API Communication Layer (`src/services/api.js`)

All communication between React and FastAPI is centralized in `src/services/api.js`.

### Key Service Methods:
- `fetchHealth()`: Queries `/health`.
- `createInspectionRun(url, autoExecute)`: Submits new inspection.
- `fetchRun(runId)`: Queries run status.
- `fetchInspectionRuns()`: Queries PostgreSQL run history.
- `fetchRunFindings(runId, includeMock)`: Fetches detected UI defects.
- `executeRunPipeline(runId)`: Triggers pipeline execution.
- `getArtifactUrl(runId, filename)`: Formats URL for artifact streaming.
- `repairRunFinding(runId, findingId, verifyLive)`: Requests locator repairs.
- `fetchRunProposals(runId, filter)`: Retrieves proposals list.
- `createRepairProposal(runId, payload)`: Drafts new proposal.
- `approveProposal(proposalId, notes)`: Approves proposal.
- `rejectProposal(proposalId, notes)`: Rejects proposal.
- `generateProposalPatch(runId, proposalId, targetFile)`: Synthesizes safe diff.
- `submitProposalPR(runId, proposalId, options)`: Submits PR with approval gate.
- `fetchGitHubConfig()` & `fetchVlmConfig()`: Diagnostic readiness checks.

---

## 5. State Management & Auto-Polling Lifecycle

1. When a run is initiated or selected, `isAutoPolling` is set to `true`.
2. A `setInterval` timer triggers every **2.5 seconds**, fetching fresh state via `fetchRun(currentRun.run_id)`.
3. If the run transitions to a terminal state (`completed`, `failed`, `cancelled`), auto-polling stops automatically.
4. Upon completion, findings, proposals, and history are refreshed automatically.

---

## 6. Human-in-the-Loop Governance & Tri-Stage Badges

The dashboard strictly enforces separation across three distinct governance stages:

| Badge | Permitted States | Governance Principle |
| :--- | :--- | :--- |
| **Review** | `PENDING`, `APPROVED`, `REJECTED` | Human authorization recorded in PostgreSQL. |
| **Execution** | `UNAPPLIED`, `APPLYING`, `APPLIED`, `FAILED` | Physical application of code or CSS patches. |
| **Verification** | `UNVERIFIED`, `VERIFIED_SUCCESS`, `VERIFIED_FAILURE`, `INCONCLUSIVE` | Visual re-inspection on a live page. |

> **Important:** Approving a proposal authorizes remediation; it does **not** claim that the patch has been applied or verified.
