/**
 * OmniSight Dashboard API Service
 *
 * Centralizes all communication between the React frontend and the FastAPI backend.
 * Uses environment configuration (VITE_API_BASE_URL) rather than hardcoded URLs.
 */

const RAW_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
// Strip trailing slashes for predictable endpoint concatenation
const API_BASE_URL = RAW_BASE_URL.replace(/\/+$/, '');

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
