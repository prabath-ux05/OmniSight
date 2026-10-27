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
    raw = `http://${raw}`;
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
 * @returns {Promise<{ ok: boolean, data?: object, error?: string, status?: number, isNetworkError?: boolean }>}
 */
export async function createInspectionRun(targetUrl, autoExecute = true) {
  const cleanUrl = (targetUrl || '').trim();
  if (!cleanUrl) {
    return { ok: false, error: 'Target website URL is required.' };
  }

  const query = autoExecute ? '?auto_execute=true' : '';
  const endpoint = `${API_BASE_URL}/api/v1/runs${query}`;

  try {
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({ url: cleanUrl }),
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
      headers: { Accept: 'application/json' },
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
 * Retrieve status and metadata for a run (GET /api/v1/runs/{run_id})
 */
export async function fetchRun(runId) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }

  const endpoint = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}`;

  try {
    const res = await fetch(endpoint, {
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
    };
  }
}

/**
 * Retrieve defect findings for a run (GET /api/v1/runs/{run_id}/findings)
 *
 * @param {string} runId - Unique identifier of the run
 * @param {boolean} includeMock - Whether to request mock findings for testing
 */
export async function fetchRunFindings(runId, includeMock = false) {
  if (!runId || !runId.trim()) {
    return { ok: false, error: 'Run ID is required.' };
  }

  const query = includeMock ? '?include_mock=true' : '';
  const endpoint = `${API_BASE_URL}/api/v1/runs/${encodeURIComponent(runId.trim())}/findings${query}`;

  try {
    const res = await fetch(endpoint, {
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
 * Request locator repair suggestions for a run finding (POST /api/v1/runs/{run_id}/repair)
 *
 * @param {string} runId - Run identifier
 * @param {string} [findingId] - Optional specific finding ID
 * @param {boolean} [verifyLive=false] - Whether to verify candidate locator against live target page
 * @returns {Promise<{ ok: boolean, data?: object[], error?: string, status?: number }>}
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
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
    });

    if (res.ok) {
      const repairData = await res.json();
      return { ok: true, data: repairData };
    }

    const errData = await res.json().catch(() => null);
    const errorMsg = parseApiErrorDetail(
      errData,
      `Failed to generate repair suggestions for run '${runId}'.`
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
export async function fetchVLMConfig(provider = null) {
  const query = provider ? `?provider=${encodeURIComponent(provider)}` : '';
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
 * Generate or fetch reviewable repair proposals (POST /api/v1/runs/{run_id}/proposals)
 */
export async function fetchRunProposals(runId, payload = null) {
  if (!runId || typeof runId !== 'string' || !runId.trim()) {
    return { ok: false, error: 'Cannot fetch proposals: invalid or empty run ID.' };
  }
  const cleanId = encodeURIComponent(runId.trim());
  const url = `${API_BASE_URL}/api/v1/runs/${cleanId}/proposals`;
  try {
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload || {}),
    });
    if (res.ok) {
      const data = await res.json();
      return { ok: true, data };
    }
    const errData = await res.json().catch(() => null);
    const msg = parseApiErrorDetail(errData, `Failed to generate proposals (HTTP ${res.status})`);
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
