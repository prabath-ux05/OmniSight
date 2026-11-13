/**
 * OmniSight Dashboard API Service
 *
 * Centralizes all communication between the React frontend and the FastAPI backend.
 * Uses environment configuration (VITE_API_BASE_URL) rather than hardcoded URLs.
 */

const RAW_BASE_URL = (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_BASE_URL) || '';
// Strip trailing slashes for predictable endpoint concatenation
const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, '');

export const DEFAULT_DEMO_BASE_URL = 'http://127.0.0.1:8080/index.html';

export const DEMO_STATE_PARAMS = {
  clean: { state: 'clean' },
  overflow: { defect: 'overflow' },
  missing: { defect: 'missing' },
  image: { defect: 'image' },
  all: { defects: 'all' },
};

export const DEMO_STATES = [
  { id: 'clean', label: 'Clean', defect: 'clean', description: 'Baseline error-free target state (?state=clean)' },
  { id: 'overflow', label: 'Overflow', defect: 'overflow', description: 'Horizontal layout text overflow (?defect=overflow)' },
  { id: 'missing', label: 'Missing Element', defect: 'missing', description: 'Missing CTA button locator (?defect=missing)' },
  { id: 'image', label: 'Broken Image', defect: 'image', description: 'Broken 404 topology diagram (?defect=image)' },
  { id: 'all', label: 'All Defects', defect: 'all', description: 'Simultaneous combination of all defects (?defects=all)' },
];

/**
 * Builds a demo site URL following the repository construct_demo_url convention.
 *
 * @param {string} baseUrl - Base URL or existing full URL
 * @param {string} state - One of 'clean', 'overflow', 'missing', 'image', 'all'
 * @returns {string} Fully qualified URL with corresponding demo query parameters
 */
export function constructDemoUrl(baseUrl, state = 'clean') {
  let raw = (baseUrl || '').trim() || DEFAULT_DEMO_BASE_URL;

  // Add scheme if omitted
  if (!raw.startsWith('http://') && !raw.startsWith('https://')) {
    raw = 'http://' + raw;
  }

  let parsed;
  try {
    parsed = new URL(raw);
  } catch {
    parsed = new URL(DEFAULT_DEMO_BASE_URL);
  }

  // Clear existing state/defect parameters
  const defectKeys = [
    'defect',
    'defects',
    'state',
    'baseline',
    'defect_overflow',
    'defect_missing',
    'defect_broken_image',
  ];
  defectKeys.forEach((key) => parsed.searchParams.delete(key));

  const stateKey = (state || 'clean').toLowerCase();
  const params = DEMO_STATE_PARAMS[stateKey] || { state: 'clean' };
  Object.entries(params).forEach(([k, v]) => {
    parsed.searchParams.set(k, v);
  });

  return parsed.toString();
}

/**
 * Returns the effective backend URL description for user-facing diagnostic messages.
 */
export function getBackendDisplayUrl() {
  if (API_BASE_URL) {
    return API_BASE_URL;
  }
  return 'http://127.0.0.1:8000 (via Vite proxy)';
}

/**
 * Generates an actionable error message when the backend API is unreachable.
 */
function createNetworkErrorMessage(originalError) {
  const targetUrl = getBackendDisplayUrl();
  return (
    `Backend server is unreachable at ${targetUrl}. ` +
    `Please ensure the backend is running with:\n` +
    `  uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000\n` +
    `and test the connection with:\n` +
    `  curl http://127.0.0.1:8000/health\n` +
    `Details: ${originalError?.message || 'Connection refused'}`
  );
}

/**
 * Formats API error payloads (e.g. FastAPI 422 validation errors or 400/404 messages).
 */
function parseApiErrorDetail(errorData, fallbackMessage) {
  if (!errorData) return fallbackMessage;

  // FastAPI validation error detail is often an array of { loc, msg, type }
  if (Array.isArray(errorData.detail)) {
    return errorData.detail
      .map((item) => {
        const field = item.loc ? item.loc.join('.') : 'payload';
        return `${field}: ${item.msg}`;
      })
      .join('; ');
  }

  // String detail (e.g. { "detail": "Run 'xyz' not found." })
  if (typeof errorData.detail === 'string') {
    return errorData.detail;
  }

  return fallbackMessage;
}

/**
 * Extracts the Double-Submit CSRF cookie value ('omnisight_csrf') from document.cookie.
 *
 * @returns {string} Raw CSRF token string or empty string if not found or in non-browser environment.
 */
export function getCsrfToken() {
  if (typeof document === 'undefined' || !document.cookie) return '';
  const match = document.cookie.match(/(?:^|;\s*)omnisight_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : '';
}

/**
 * Merges standard auth and CSRF headers onto caller-supplied request headers.
 *
 * @param {Record<string, string>} [customHeaders={}]
 * @returns {Record<string, string>}
 */
export function buildAuthHeaders(customHeaders = {}) {
  const headers = { ...customHeaders };
  const csrf = getCsrfToken();
  if (csrf && !headers['X-CSRF-Token']) {
    headers['X-CSRF-Token'] = csrf;
  }
  return headers;
}

/**
 * Check backend health status (GET /health)
 */
export async function fetchHealth() {
  const url = `${API_BASE_URL}/health`;
  try {
    const res = await fetch(url, {
      headers: { Accept: 'application/json' },
    });

    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }

    const errData = await res.json().catch(() => null);
    const msg = parseApiErrorDetail(errData, `Backend responded with HTTP ${res.status}`);
    return { ok: false, error: msg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Create a new inspection run (POST /api/v1/runs)
 *
 * @param {string} targetUrl - Target web page URL to inspect
 * @param {boolean} autoExecute - Whether to automatically schedule browser and vision execution
 * @param {string[]} viewports - List of viewports ('desktop', 'tablet', 'mobile')
 * @returns {Promise<{ ok: boolean, data?: object, error?: string, status?: number, isNetworkError?: boolean }>}
 */
export async function createInspectionRun(targetUrl, autoExecute = true, viewports = ['desktop']) {
  const cleanUrl = (targetUrl || '').trim();
  if (!cleanUrl) {
    return { ok: false, error: 'Target website URL is required.' };
  }

  const query = autoExecute ? '?auto_execute=true' : '';
  const endpoint = `${API_BASE_URL}/api/v1/runs${query}`;

  const payload = { url: cleanUrl };
  if (Array.isArray(viewports) && viewports.length > 0) {
    payload.viewports = viewports;
  }

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({
        'Content-Type': 'application/json',
        Accept: 'application/json',
      }),
      body: JSON.stringify(payload),
    });

    if (res.status === 201) {
      const runData = await res.json();
      return { ok: true, data: runData };
    }

    // Handle 422 validation, 400 bad request, or other errors
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(
      errData,
      `Failed to initiate run (HTTP ${res.status})`
    );

    return {
      ok: false,
      error: errorMsg,
      status: res.status,
    };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Trigger the inspection pipeline for an existing run (POST /api/v1/runs/{run_id}/execute)
 */
export async function executeRunPipeline(runId) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }

  const endpoint = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/execute`;

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({ Accept: 'application/json' }),
    });

    if (res.ok) {
      const runData = await res.json();
      return { ok: true, data: runData };
    }

    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Execution failed for run '${runId}'.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Returns the accessible HTTP URL for an inspection artifact (screenshot or DOM).
 *
 * @param {string} runId
 * @param {string} filename
 * @returns {string} Accessible URL
 */
export function getArtifactUrl(runId, filename) {
  if (!runId || !filename) return '';
  const cleanRun = encodeURIComponent(runId.trim());
  const cleanFile = encodeURIComponent(filename.trim());
  return `${API_BASE_URL}/api/v1/artifacts/${cleanRun}/${cleanFile}`;
}

/**
 * Returns the accessible HTTP URL for a specific viewport and stage screenshot.
 *
 * @param {string} runId
 * @param {string} viewport - 'desktop' | 'tablet' | 'mobile'
 * @param {string} stage - 'before' | 'after'
 * @returns {string} Accessible screenshot URL
 */
export function getViewportScreenshotUrl(runId, viewport = 'desktop', stage = 'before') {
  if (!runId) return '';
  const cleanRun = encodeURIComponent(runId.trim());
  const vp = (viewport || 'desktop').toLowerCase();
  const stg = stage && stage.toLowerCase() === 'after' ? 'after' : 'before';
  const params = new URLSearchParams();
  if (vp !== 'desktop') params.set('viewport', vp);
  if (stg !== 'before') params.set('stage', stg);
  const qs = params.toString() ? `?${params.toString()}` : '';
  return `${API_BASE_URL}/api/v1/artifacts/${cleanRun}/screenshot${qs}`;
}

/**
 * Retrieve status and metadata for a run (GET /api/v1/runs/{run_id})
 */
export async function fetchRun(runId) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }

  const endpoint = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}`;

  try {
    const res = await fetch(endpoint, {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });

    if (res.ok) {
      const runData = await res.json();
      return { ok: true, data: runData };
    }

    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Run '${runId}' could not be retrieved.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
      status: 0,
    };
  }
}

/**
 * Retrieve defect findings for a run (GET /api/v1/runs/{run_id}/findings)
 *
 * @param {string} runId - Unique identifier of the run
 * @param {boolean} includeMock - Whether to request mock findings for testing
 * @param {string|null} viewport - Optional viewport filter ('desktop', 'tablet', 'mobile')
 */
export async function fetchRunFindings(runId, includeMock = false, viewport = null) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }

  const params = new URLSearchParams();
  if (includeMock) params.set('include_mock', 'true');
  if (viewport && viewport !== 'ALL') params.set('viewport', viewport);
  const qs = params.toString() ? `?${params.toString()}` : '';
  const endpoint = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/findings${qs}`;

  try {
    const res = await fetch(endpoint, {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });

    if (res.ok) {
      const findings = await res.json();
      if (!Array.isArray(findings)) {
        return {
          ok: false,
          error: 'Malformed findings response from backend: expected a list of findings.',
        };
      }
      return { ok: true, data: findings };
    }

    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Findings for run '${runId}' could not be retrieved.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Retrieve all historical inspection runs (GET /api/v1/runs)
 */
export async function fetchInspectionRuns() {
  const endpoint = `${API_BASE_URL}/api/v1/runs`;
  try {
    const res = await fetch(endpoint, {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      const runs = await res.json();
      return { ok: true, data: runs };
    }
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Failed to fetch runs history (HTTP ${res.status}).`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Retrieve recorded artifact metadata for a run (GET /api/v1/runs/{run_id}/artifacts)
 */
export async function fetchRunArtifacts(runId) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }
  const endpoint = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/artifacts`;
  try {
    const res = await fetch(endpoint, {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      const artifacts = await res.json();
      return { ok: true, data: artifacts };
    }
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Artifacts for run '${runId}' could not be retrieved.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Retrieve repair proposals for a run (GET /api/v1/runs/{run_id}/proposals)
 */
export async function fetchRunProposals(runId, findingId = null) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }
  const cleanFindingId = typeof findingId === 'string'
    ? findingId.trim()
    : (findingId && typeof findingId === 'object' && findingId.finding_id ? String(findingId.finding_id).trim() : null);
  const query = cleanFindingId ? `?finding_id=${encodeURIComponent(cleanFindingId)}` : '';
  const endpoint = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/proposals${query}`;
  try {
    const res = await fetch(endpoint, {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      const proposals = await res.json();
      return { ok: true, data: proposals };
    }
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Proposals for run '${runId}' could not be retrieved.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Create a new repair proposal for a run (POST /api/v1/runs/{run_id}/proposals)
 */
export async function createRepairProposal(runId, payload) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }
  const endpoint = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/proposals`;
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({
        'Content-Type': 'application/json',
        Accept: 'application/json',
      }),
      body: JSON.stringify(payload),
    });
    if (res.status === 201) {
      const proposal = await res.json();
      return { ok: true, data: proposal };
    }
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Failed to create proposal (HTTP ${res.status}).`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Approve a repair proposal (POST /api/v1/proposals/{proposal_id}/approve)
 * Supports revisiting an already approved proposal when options.revisit is true.
 */
export async function approveProposal(proposalId, reviewerNotes = '', options = {}) {
  if (!proposalId || !proposalId.trim()) {
    return { ok: false, error: 'Proposal ID is required.' };
  }
  const isRevisit = Boolean(options && options.revisit);
  const endpoint = `${API_BASE_URL}/api/v1/proposals/${encodeURIComponent(proposalId.trim())}/approve`;
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({
        'Content-Type': 'application/json',
        Accept: 'application/json',
      }),
      body: JSON.stringify({
        notes: reviewerNotes || null,
        revisit: isRevisit,
      }),
    });
    if (res.ok) {
      const updated = await res.json();
      return { ok: true, data: updated };
    }
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Failed to approve proposal '${proposalId}'.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Reject a repair proposal (POST /api/v1/proposals/{proposal_id}/reject)
 * Supports revisiting an approved proposal and revoking/rejecting it when options.revisit is true.
 */
export async function rejectProposal(proposalId, reviewerNotes = '', options = {}) {
  if (!proposalId || !proposalId.trim()) {
    return { ok: false, error: 'Proposal ID is required.' };
  }
  const isRevisit = Boolean(options && options.revisit);
  const endpoint = `${API_BASE_URL}/api/v1/proposals/${encodeURIComponent(proposalId.trim())}/reject`;
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({
        'Content-Type': 'application/json',
        Accept: 'application/json',
      }),
      body: JSON.stringify({
        notes: reviewerNotes || null,
        revisit: isRevisit,
      }),
    });
    if (res.ok) {
      const updated = await res.json();
      return { ok: true, data: updated };
    }
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Failed to reject proposal '${proposalId}'.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Retrieve Before/After visual comparison details for a proposal (GET /api/v1/runs/{run_id}/proposals/{proposal_id}/comparison)
 */
export async function fetchVisualComparison(runId, proposalId, viewport = 'desktop') {
  if (!proposalId || !proposalId.trim()) {
    return { ok: false, error: 'Proposal ID is required.' };
  }
  const cleanProp = encodeURIComponent(proposalId.trim());
  const cleanVp = encodeURIComponent((viewport || 'desktop').toLowerCase());
  const endpoint = runId
    ? `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/proposals/${cleanProp}/comparison?viewport=${cleanVp}`
    : `${API_BASE_URL}/api/v1/proposals/${cleanProp}/comparison?viewport=${cleanVp}`;

  try {
    const res = await fetch(endpoint, {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Failed to fetch visual comparison for proposal '${proposalId}'.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Simulate applying a repair patch within a controlled sandbox (POST /api/v1/runs/{run_id}/proposals/{proposal_id}/simulate-repair)
 */
export async function simulateControlledRepair(runId, proposalId, viewport = 'desktop') {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }
  if (!proposalId || !proposalId.trim()) {
    return { ok: false, error: 'Proposal ID is required.' };
  }
  const endpoint = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/proposals/${encodeURIComponent(proposalId.trim())}/simulate-repair`;

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({
        'Content-Type': 'application/json',
        Accept: 'application/json',
      }),
      body: JSON.stringify({ viewport: (viewport || 'desktop').toLowerCase() }),
    });
    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Controlled repair simulation failed for proposal '${proposalId}'.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Retrieve status summary of a repair proposal (GET /api/v1/proposals/{proposal_id}/status)
 */
export async function fetchProposalStatus(proposalId) {
  if (!proposalId || !proposalId.trim()) {
    return { ok: false, error: 'Proposal ID is required.' };
  }
  const endpoint = `${API_BASE_URL}/api/v1/proposals/${encodeURIComponent(proposalId.trim())}/status`;
  try {
    const res = await fetch(endpoint, {
      credentials: 'include',
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      const statusData = await res.json();
      return { ok: true, data: statusData };
    }
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Failed to fetch proposal status.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Request locator repair suggestions for a run finding (POST /api/v1/runs/{run_id}/repair)
 */
export async function repairRunFinding(runId, findingId = null, verifyLive = false) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }

  const cleanRun = encodeURIComponent(runId.trim());
  const params = new URLSearchParams();
  if (findingId) params.set('finding_id', findingId.trim());
  if (verifyLive) params.set('verify_live', 'true');
  const query = params.toString() ? `?${params.toString()}` : '';
  const endpoint = `${API_BASE_URL}/api/v1/runs/${cleanRun}/repair${query}`;

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({ Accept: 'application/json' }),
    });

    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }

    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(
      errData,
      `Repair request failed for run '${runId}'.`
    );
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Inspect VLM provider configuration status (GET /api/v1/runs/vlm/config)
 */
export const fetchVLMConfig = fetchVlmConfig;

export async function fetchVlmConfig(provider = null) {
  const query = provider ? `?provider=${encodeURIComponent(provider.trim())}` : '';
  const url = `${API_BASE_URL}/api/v1/runs/vlm/config${query}`;
  try {
    const res = await fetch(url, {
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
    const errData = await res.json().catch(() => null);
    const msg = parseApiErrorDetail(errData, `VLM config check failed with HTTP ${res.status}`);
    return { ok: false, error: msg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Inspect GitHub integration configuration status (GET /api/v1/github/config)
 */
export async function fetchGitHubConfig() {
  const url = `${API_BASE_URL}/api/v1/github/config`;
  try {
    const res = await fetch(url, {
      headers: { Accept: 'application/json' },
    });
    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
    const errData = await res.json().catch(() => null);
    const msg = parseApiErrorDetail(errData, `GitHub config check failed with HTTP ${res.status}`);
    return { ok: false, error: msg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Generate a safe minimal diff patch for a proposal (POST /api/v1/runs/{run_id}/proposals/{proposal_id}/patch)
 */
export async function generateProposalPatch(runId, proposalId, targetFile, workspaceRoot = null) {
  if (!runId || !proposalId || !targetFile) {
    return { ok: false, error: 'runId, proposalId, and targetFile are required for patch generation.' };
  }
  const cleanRunId = encodeURIComponent(runId.trim());
  const cleanPropId = encodeURIComponent(proposalId.trim());
  const url = `${API_BASE_URL}/api/v1/runs/${cleanRunId}/proposals/${cleanPropId}/patch`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        target_file: targetFile.trim(),
        workspace_root: workspaceRoot ? workspaceRoot.trim() : null,
      }),
    });
    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
    const errData = await res.json().catch(() => null);
    const msg = parseApiErrorDetail(errData, `Patch generation failed (HTTP ${res.status})`);
    return { ok: false, error: msg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Submit an approved proposal to GitHub with user approval check (POST /api/v1/runs/{run_id}/proposals/{proposal_id}/pull-request)
 */
export async function submitProposalPR(runId, proposalId, options = {}) {
  const { userApproved = false, targetFile = null, baseBranch = null, simulate = false } = options;
  if (!userApproved) {
    return {
      ok: false,
      error: 'Submission blocked by approval gate: explicit user confirmation is required.',
      isApprovalBlocked: true,
    };
  }
  const cleanRunId = encodeURIComponent(runId.trim());
  const cleanPropId = encodeURIComponent(proposalId.trim());
  const url = `${API_BASE_URL}/api/v1/runs/${cleanRunId}/proposals/${cleanPropId}/pull-request`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_approved: true,
        target_file: targetFile,
        base_branch: baseBranch,
        simulate: Boolean(simulate),
      }),
    });
    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
    const errData = await res.json().catch(() => null);
    const msg = parseApiErrorDetail(errData, `Pull request creation failed (HTTP ${res.status})`);
    return { ok: false, error: msg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Send a conversational query to the OmniSight LLM Assistant (POST /api/v1/chat)
 *
 * @param {Object} payload - { message, history, context }
 */
export async function sendChatMessage(payload) {
  if (!payload || !payload.message || !payload.message.trim()) {
    return { ok: false, error: 'Message cannot be empty.' };
  }

  const endpoint = `${API_BASE_URL}/api/v1/chat`;

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({
        'Content-Type': 'application/json',
        Accept: 'application/json',
      }),
      credentials: 'include',
      body: JSON.stringify({
        message: payload.message.trim(),
        history: Array.isArray(payload.history) ? payload.history : [],
        context: payload.context || null,
      }),
    });

    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }

    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(
      errData,
      res.status === 503
        ? 'LLM Chat service is currently unavailable. Please verify backend API key configuration.'
        : `Chat request failed with status ${res.status}.`
    );
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
      status: 0,
    };
  }
}

/**
 * Fetch LLM assistant configuration status (GET /api/v1/chat/status)
 */
export async function fetchChatStatus() {
  const endpoint = `${API_BASE_URL}/api/v1/chat/status`;

  try {
    const res = await fetch(endpoint, {
      headers: { Accept: 'application/json' },
      credentials: 'include',
    });

    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }

    return {
      ok: false,
      configured: false,
      error: `Status query returned ${res.status}`,
    };
  } catch (err) {
    return {
      ok: false,
      configured: false,
      error: createNetworkErrorMessage(err),
    };
  }
}

/**
 * Fetch live scanning preview status and telemetry for a run (GET /api/v1/runs/{run_id}/preview)
 */
export async function fetchPreviewStatus(runId) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }
  const endpoint = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/preview`;
  try {
    const res = await fetch(endpoint, {
      headers: { Accept: 'application/json' },
      credentials: 'include',
    });
    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(errData, `Failed to fetch preview for run '${runId}'.`);
    return { ok: false, error: errorMsg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
      status: 0,
    };
  }
}

/**
 * Construct Server-Sent Events (SSE) streaming URL for real-time live preview
 */
export function getPreviewStreamUrl(runId) {
  if (!runId || !runId.trim()) return '';
  return `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/preview/stream`;
}

/**
 * Construct raw preview JPEG frame endpoint URL
 */
export function getPreviewFrameUrl(runId) {
  if (!runId || !runId.trim()) return '';
  return `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/preview/frame`;
}

// =============================================================================
// Inspection History & Run Report Export APIs (CSV & PDF)
// =============================================================================

/**
 * Construct URL for downloading history CSV export
 */
export function getHistoryExportCsvUrl(statusFilter = '') {
  const query = statusFilter && statusFilter.toUpperCase() !== 'ALL'
    ? `?status_filter=${encodeURIComponent(statusFilter)}`
    : '';
  return `${API_BASE_URL}/api/v1/runs/export/csv${query}`;
}

/**
 * Construct URL for downloading history PDF export
 */
export function getHistoryExportPdfUrl(statusFilter = '') {
  const query = statusFilter && statusFilter.toUpperCase() !== 'ALL'
    ? `?status_filter=${encodeURIComponent(statusFilter)}`
    : '';
  return `${API_BASE_URL}/api/v1/runs/export/pdf${query}`;
}

/**
 * Construct URL for downloading single run CSV export
 */
export function getRunExportCsvUrl(runId) {
  if (!runId || !runId.trim()) return '';
  return `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/export/csv`;
}

/**
 * Construct URL for downloading single run PDF report
 */
export function getRunExportPdfUrl(runId) {
  if (!runId || !runId.trim()) return '';
  return `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/export/pdf`;
}

/**
 * Download a file from an endpoint via blob URL with fallback filename
 */
export async function downloadExportFile(url, fallbackFilename = 'omnisight_export') {
  if (!url) {
    return { ok: false, error: 'Export URL is required.' };
  }
  try {
    const res = await fetch(url, {
      method: 'GET',
      credentials: 'include',
    });
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      return { ok: false, error: `Export failed (${res.status}): ${errText || res.statusText}` };
    }
    const blob = await res.blob();
    let filename = fallbackFilename;
    const disposition = res.headers.get('content-disposition');
    if (disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename=["']?([^"';]+)["']?/);
      if (match && match[1]) {
        filename = match[1].trim();
      }
    }
    if (typeof window !== 'undefined' && typeof document !== 'undefined') {
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    }
    return { ok: true, filename };
  } catch (err) {
    return { ok: false, error: err?.message || 'Download failed.' };
  }
}

/**
 * Triggers export of all historical runs as CSV
 */
export async function exportInspectionHistoryCsv(statusFilter = '') {
  const url = getHistoryExportCsvUrl(statusFilter);
  return downloadExportFile(url, 'omnisight_inspection_history.csv');
}

/**
 * Triggers export of historical audit log summary as PDF
 */
export async function exportInspectionHistoryPdf(statusFilter = '') {
  const url = getHistoryExportPdfUrl(statusFilter);
  return downloadExportFile(url, 'omnisight_inspection_history.pdf');
}

/**
 * Triggers export of single inspection run findings as CSV
 */
export async function exportRunReportCsv(runId) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }
  const url = getRunExportCsvUrl(runId);
  return downloadExportFile(url, `omnisight_run_${runId.trim()}.csv`);
}

/**
 * Triggers export of single inspection run executive report as PDF
 */
export async function exportRunReportPdf(runId) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }
  const url = getRunExportPdfUrl(runId);
  return downloadExportFile(url, `omnisight_report_${runId.trim()}.pdf`);
}

// =============================================================================
// User Authentication & Session Management
// =============================================================================

/**
 * Registers a new user account with email and password.
 * On success, backend sets HTTP-only session cookie and returns user profile.
 *
 * @param {Object} params
 * @param {string} params.email
 * @param {string} params.password
 * @param {string} [params.fullName]
 * @returns {Promise<{ ok: boolean, data?: Object, error?: string, status?: number }>}
 */
export async function registerUser({ email, password, fullName }) {
  const endpoint = `${API_BASE_URL}/api/v1/auth/register`;
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({
        'Content-Type': 'application/json',
        Accept: 'application/json',
      }),
      body: JSON.stringify({
        email: (email || '').trim(),
        password,
        full_name: (fullName || '').trim() || undefined,
      }),
    });

    if (res.status === 201) {
      const data = await res.json();
      return { ok: true, data };
    }

    const errData = await res.json().catch(() => null);
    const msg = parseApiErrorDetail(errData, `Registration failed (HTTP ${res.status})`);
    return { ok: false, error: msg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Authenticates user credentials and establishes an active session.
 *
 * @param {Object} params
 * @param {string} params.email
 * @param {string} params.password
 * @returns {Promise<{ ok: boolean, data?: Object, error?: string, status?: number }>}
 */
export async function loginUser({ email, password }) {
  const endpoint = `${API_BASE_URL}/api/v1/auth/login`;
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({
        'Content-Type': 'application/json',
        Accept: 'application/json',
      }),
      body: JSON.stringify({
        email: (email || '').trim(),
        password,
      }),
    });

    if (res.status === 200) {
      const data = await res.json();
      return { ok: true, data };
    }

    const errData = await res.json().catch(() => null);
    const msg = parseApiErrorDetail(errData, `Login failed (HTTP ${res.status})`);
    return { ok: false, error: msg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Resolves current user profile from active session cookie.
 * Returns { ok: false, isUnauthenticated: true } when caller has no active session.
 *
 * @returns {Promise<{ ok: boolean, data?: Object, error?: string, isUnauthenticated?: boolean, status?: number }>}
 */
export async function fetchCurrentUser() {
  const endpoint = `${API_BASE_URL}/api/v1/auth/me`;
  try {
    const res = await fetch(endpoint, {
      method: 'GET',
      credentials: 'include',
      headers: {
        Accept: 'application/json',
      },
    });

    if (res.status === 200) {
      const data = await res.json();
      return { ok: true, data };
    }

    if (res.status === 401) {
      return { ok: false, isUnauthenticated: true, status: 401 };
    }

    const errData = await res.json().catch(() => null);
    const msg = parseApiErrorDetail(errData, `Session lookup failed (HTTP ${res.status})`);
    return { ok: false, error: msg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}

/**
 * Revokes active database session and clears authentication cookies.
 *
 * @returns {Promise<{ ok: boolean, data?: Object, error?: string, status?: number }>}
 */
export async function logoutUser() {
  const endpoint = `${API_BASE_URL}/api/v1/auth/logout`;
  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      credentials: 'include',
      headers: buildAuthHeaders({
        Accept: 'application/json',
      }),
    });

    if (res.status === 200) {
      const data = await res.json();
      return { ok: true, data };
    }

    const errData = await res.json().catch(() => null);
    const msg = parseApiErrorDetail(errData, `Logout failed (HTTP ${res.status})`);
    return { ok: false, error: msg, status: res.status };
  } catch (err) {
    return {
      ok: false,
      error: createNetworkErrorMessage(err),
      isNetworkError: true,
    };
  }
}
