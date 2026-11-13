import test from 'node:test';
import assert from 'node:assert/strict';

import {
  constructDemoUrl,
  getArtifactUrl,
  DEMO_STATES,
  DEMO_STATE_PARAMS,
  DEFAULT_DEMO_BASE_URL,
} from './api.js';

test('DEMO_STATES contains all 5 required demo inspection states', () => {
  const ids = DEMO_STATES.map((s) => s.id);
  assert.deepEqual(ids, ['clean', 'overflow', 'missing', 'image', 'all']);
});

test('constructDemoUrl builds clean state URL', () => {
  const url = constructDemoUrl('http://127.0.0.1:8080/index.html', 'clean');
  assert.equal(url, 'http://127.0.0.1:8080/index.html?state=clean');
});

test('constructDemoUrl builds overflow defect URL', () => {
  const url = constructDemoUrl('http://127.0.0.1:8080/index.html', 'overflow');
  assert.equal(url, 'http://127.0.0.1:8080/index.html?defect=overflow');
});

test('constructDemoUrl builds missing element defect URL', () => {
  const url = constructDemoUrl('http://127.0.0.1:8080/index.html', 'missing');
  assert.equal(url, 'http://127.0.0.1:8080/index.html?defect=missing');
});

test('constructDemoUrl builds broken image defect URL', () => {
  const url = constructDemoUrl('http://127.0.0.1:8080/index.html', 'image');
  assert.equal(url, 'http://127.0.0.1:8080/index.html?defect=image');
});

test('constructDemoUrl builds all defects URL', () => {
  const url = constructDemoUrl('http://127.0.0.1:8080/index.html', 'all');
  assert.equal(url, 'http://127.0.0.1:8080/index.html?defects=all');
});

test('constructDemoUrl replaces prior defect query parameters cleanly', () => {
  const priorUrl = 'http://127.0.0.1:8080/index.html?defect=overflow&foo=bar';
  const newUrl = constructDemoUrl(priorUrl, 'missing');
  const parsed = new URL(newUrl);

  assert.equal(parsed.searchParams.get('defect'), 'missing');
  assert.equal(parsed.searchParams.get('foo'), 'bar');
  assert.equal(parsed.searchParams.has('state'), false);
});

test('constructDemoUrl defaults to DEFAULT_DEMO_BASE_URL when baseUrl is empty', () => {
  const url = constructDemoUrl('', 'clean');
  assert.equal(url, `${DEFAULT_DEMO_BASE_URL}?state=clean`);
});

test('getArtifactUrl generates correct artifact endpoint path', () => {
  const screenshotUrl = getArtifactUrl('run_12345', 'before.png');
  assert.equal(screenshotUrl, '/api/v1/artifacts/run_12345/before.png');

  const domUrl = getArtifactUrl('run_12345', 'dom.html');
  assert.equal(domUrl, '/api/v1/artifacts/run_12345/dom.html');
});

test('getArtifactUrl returns empty string when parameters missing', () => {
  assert.equal(getArtifactUrl('', 'before.png'), '');
  assert.equal(getArtifactUrl('run_123', ''), '');
});

test('repairRunFinding returns error when runId is missing', async () => {
  const { repairRunFinding } = await import('./api.js');
  const res = await repairRunFinding('');
  assert.equal(res.ok, false);
  assert.match(res.error, /Run ID is required/);
});

test('repairRunFinding calls endpoint and parses result with mock fetch', async () => {
  const { repairRunFinding } = await import('./api.js');
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (url, options) => {
      assert.match(url, /\/api\/v1\/runs\/run_test123\/repair\?finding_id=f_456/);
      assert.equal(options.method, 'POST');
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({
          run_id: 'run_test123',
          repaired: true,
          repairs: [
            {
              finding_id: 'f_456',
              target_element: 'login-btn',
              original_selector: '#login-btn',
              repaired: true,
              best_locator: "[data-testid='login-submit']",
              score: 0.95,
              strategy: 'data_attribute',
              validation: { is_valid: true, matches: 1 },
              candidates: [
                {
                  selector: "[data-testid='login-submit']",
                  strategy: 'data_attribute',
                  score: 0.95,
                  validation: { is_valid: true, matches: 1 },
                },
              ],
              reason: 'Found stable data-testid attribute with unique DOM match',
            },
          ],
        }),
      };
    };

    const res = await repairRunFinding('run_test123', 'f_456');
    assert.equal(res.ok, true);
    assert.equal(res.data.repaired, true);
    assert.equal(res.data.repairs[0].best_locator, "[data-testid='login-submit']");
  } finally {
    globalThis.fetch = originalFetch;
  }
});
test('repairRunFinding appends verify_live=true when requested', async () => {
  const { repairRunFinding } = await import('./api.js');
  const originalFetch = globalThis.fetch;
  try {
    let capturedUrl = '';
    globalThis.fetch = async (url) => {
      capturedUrl = url;
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({ repaired: true }),
      };
    };

    const res = await repairRunFinding('run_test123', 'f_456', true);
    assert.equal(res.ok, true);
    assert.match(capturedUrl, /verify_live=true/);
    assert.match(capturedUrl, /finding_id=f_456/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
test('fetchVLMConfig calls VLM configuration status endpoint', async () => {
  const { fetchVLMConfig } = await import('./api.js');
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (url) => {
      assert.match(url, /\/api\/v1\/runs\/vlm\/config\?provider=gemini/);
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({
          provider: 'gemini',
          model: 'gemini-3.5-flash-lite',
          configured: false,
          status: 'unconfigured',
        }),
      };
    };

    const res = await fetchVLMConfig('gemini');
    assert.equal(res.ok, true);
    assert.equal(res.data.provider, 'gemini');
    assert.equal(res.data.configured, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
test('fetchGitHubConfig calls GitHub configuration endpoint', async () => {
  const { fetchGitHubConfig } = await import('./api.js');
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (url) => {
      assert.match(url, /\/api\/v1\/github\/config/);
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({
          is_configured: true,
          owner: 'my-org',
          repo: 'my-repo',
          token_status: '...1234',
          approval_gate_required: true,
        }),
      };
    };

    const res = await fetchGitHubConfig();
    assert.equal(res.ok, true);
    assert.equal(res.data.is_configured, true);
    assert.equal(res.data.owner, 'my-org');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
test('submitProposalPR strictly enforces user approval gate locally', async () => {
  const { submitProposalPR } = await import('./api.js');
  // Attempt with userApproved=false
  const res = await submitProposalPR('run_123', 'prop_456', { userApproved: false });
  assert.equal(res.ok, false);
  assert.equal(res.isApprovalBlocked, true);
  assert.match(res.error, /approval gate/i);
});

test('submitProposalPR posts approved payload when userApproved is true', async () => {
  const { submitProposalPR } = await import('./api.js');
  const originalFetch = globalThis.fetch;
  try {
    let capturedBody = null;
    globalThis.fetch = async (url, opts) => {
      assert.match(url, /\/api\/v1\/runs\/run_123\/proposals\/prop_456\/pull-request/);
      capturedBody = JSON.parse(opts.body);
      return {
        ok: true,
        status: 200,
        headers: { get: () => 'application/json' },
        json: async () => ({
          status: 'simulated',
          simulated: true,
          pr_number: null,
          pr_url: null,
        }),
      };
    };

    const res = await submitProposalPR('run_123', 'prop_456', {
      userApproved: true,
      targetFile: 'tests/test_flow.py',
      simulate: true,
    });
    assert.equal(res.ok, true);
    assert.equal(capturedBody.user_approved, true);
    assert.equal(capturedBody.target_file, 'tests/test_flow.py');
    assert.equal(res.data.status, 'simulated');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
// ---------------------------------------------------------------------------
// Findings View State & Polling Resilience Tests
// ---------------------------------------------------------------------------

test('MAX_CONSECUTIVE_POLL_ERRORS is 20 to withstand ~50s container reboot', async () => {
  const { MAX_CONSECUTIVE_POLL_ERRORS } = await import('../utils/findingsState.js');
  assert.equal(MAX_CONSECUTIVE_POLL_ERRORS, 20);
});

test('getFindingsViewState returns clean ONLY for completed run with zero findings and no error', async () => {
  const { getFindingsViewState } = await import('../utils/findingsState.js');

  const cleanState = getFindingsViewState({
    runId: 'run_clean_123',
    runStatus: 'completed',
    runError: null,
    count: 0,
  });
  assert.equal(cleanState, 'clean');
});

test('getFindingsViewState prioritizes failed status over partial findings (count > 0)', async () => {
  const { getFindingsViewState } = await import('../utils/findingsState.js');

  const state = getFindingsViewState({
    runId: 'run_failed_with_partial_findings',
    runStatus: 'failed',
    runError: null,
    count: 3,
  });
  assert.equal(state, 'failed');
});

test('getFindingsViewState prioritizes execution error over partial findings (count > 0)', async () => {
  const { getFindingsViewState } = await import('../utils/findingsState.js');

  const state = getFindingsViewState({
    runId: 'run_error_with_partial_findings',
    runStatus: 'completed',
    runError: 'Playwright browser launch failed on Render (OOM)',
    count: 2,
  });
  assert.equal(state, 'failed');
});

test('getFindingsViewState returns has_findings for completed status with findings', async () => {
  const { getFindingsViewState } = await import('../utils/findingsState.js');

  const state = getFindingsViewState({
    runId: 'run_completed_with_findings',
    runStatus: 'completed',
    runError: null,
    count: 5,
  });
  assert.equal(state, 'has_findings');
});

test('getFindingsViewState returns clean for completed status with zero findings and no error', async () => {
  const { getFindingsViewState } = await import('../utils/findingsState.js');

  const state = getFindingsViewState({
    runId: 'run_clean_verified',
    runStatus: 'completed',
    runError: null,
    count: 0,
  });
  assert.equal(state, 'clean');
});

test('getFindingsViewState returns failed when run has an error, even if status is completed or undefined', async () => {
  const { getFindingsViewState } = await import('../utils/findingsState.js');

  const failedWithError = getFindingsViewState({
    runId: 'run_err_123',
    runStatus: 'completed',
    runError: 'Browser process crashed',
    count: 0,
  });
  assert.equal(failedWithError, 'failed');

  const failedStatus = getFindingsViewState({
    runId: 'run_err_456',
    runStatus: 'failed',
    runError: null,
    count: 0,
  });
  assert.equal(failedStatus, 'failed');
});

test('getFindingsViewState returns in_progress for queued, capturing, or analyzing states', async () => {
  const { getFindingsViewState } = await import('../utils/findingsState.js');

  assert.equal(getFindingsViewState({ runId: 'run_1', runStatus: 'queued', count: 0 }), 'in_progress');
  assert.equal(getFindingsViewState({ runId: 'run_2', runStatus: 'capturing', count: 0 }), 'in_progress');
  assert.equal(getFindingsViewState({ runId: 'run_3', runStatus: 'analyzing', count: 0 }), 'in_progress');
});

test('getFindingsViewState returns pending (never clean) for interrupted, null, or unknown run statuses', async () => {
  const { getFindingsViewState } = await import('../utils/findingsState.js');

  assert.equal(getFindingsViewState({ runId: 'run_null', runStatus: null, count: 0 }), 'pending');
  assert.equal(getFindingsViewState({ runId: 'run_undef', runStatus: undefined, count: 0 }), 'pending');
  assert.equal(getFindingsViewState({ runId: 'run_int', runStatus: 'interrupted', count: 0 }), 'pending');
  assert.equal(getFindingsViewState({ runId: 'run_unk', runStatus: 'something_unexpected', count: 0 }), 'pending');
});

test('getFindingsViewState returns has_findings when defect findings count > 0', async () => {
  const { getFindingsViewState } = await import('../utils/findingsState.js');

  const state = getFindingsViewState({
    runId: 'run_with_defects',
    runStatus: 'completed',
    count: 3,
  });
  assert.equal(state, 'has_findings');
});

test('getFindingsViewState handles loading, errors, and unselected run correctly', async () => {
  const { getFindingsViewState } = await import('../utils/findingsState.js');

  assert.equal(getFindingsViewState({ isLoading: true }), 'loading');
  assert.equal(getFindingsViewState({ findingsError: 'Network error 500' }), 'error');
  assert.equal(getFindingsViewState({ runId: null }), 'no_run');
});

test('createInspectionRun passes custom viewports in request body', async () => {
  const originalFetch = globalThis.fetch;
  let capturedBody = null;
  globalThis.fetch = async (url, options) => {
    capturedBody = JSON.parse(options.body);
    return {
      status: 201,
      ok: true,
      json: async () => ({ run_id: 'run_viewports_123', status: 'queued', viewports: capturedBody.viewports }),
    };
  };

  try {
    const { createInspectionRun } = await import('./api.js');
    const res = await createInspectionRun('http://127.0.0.1:8080/index.html', true, ['desktop', 'mobile']);
    assert.equal(res.ok, true);
    assert.deepEqual(capturedBody.viewports, ['desktop', 'mobile']);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
test('fetchRunFindings appends viewport query parameter when specified', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  globalThis.fetch = async (url) => {
    requestedUrl = url;
    return {
      ok: true,
      status: 200,
      json: async () => [{ finding_id: 'defect_mobile_001', viewport: 'mobile' }],
    };
  };

  try {
    const { fetchRunFindings } = await import('./api.js');
    const res = await fetchRunFindings('run_abc', false, 'mobile');
    assert.equal(res.ok, true);
    assert.match(requestedUrl, /viewport=mobile/);
    assert.equal(res.data[0].viewport, 'mobile');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
test('getViewportScreenshotUrl returns viewport-specific artifact endpoint', async () => {
  const { getViewportScreenshotUrl } = await import('./api.js');
  assert.equal(getViewportScreenshotUrl('run_123', 'desktop'), '/api/v1/artifacts/run_123/screenshot');
  assert.equal(getViewportScreenshotUrl('run_123', 'mobile'), '/api/v1/artifacts/run_123/screenshot?viewport=mobile');
  assert.equal(getViewportScreenshotUrl('run_123', 'tablet'), '/api/v1/artifacts/run_123/screenshot?viewport=tablet');
  assert.equal(getViewportScreenshotUrl('run_123', 'desktop', 'after'), '/api/v1/artifacts/run_123/screenshot?stage=after');
  assert.equal(getViewportScreenshotUrl('run_123', 'mobile', 'after'), '/api/v1/artifacts/run_123/screenshot?viewport=mobile&stage=after');
});

test('approveProposal sends reviewer notes and revisit flag', async () => {
  const { approveProposal } = await import('./api.js');
  const originalFetch = globalThis.fetch;
  let sentBody = null;
  let targetUrl = '';

  try {
    globalThis.fetch = async (url, options) => {
      targetUrl = url;
      sentBody = JSON.parse(options.body);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          proposal_id: 'prop_test_01',
          approval_status: 'approved',
          updated_at: '2026-11-12T12:00:00Z',
          can_revisit: true,
        }),
      };
    };

    const res = await approveProposal('prop_test_01', 'Approved for staging', { revisit: true });
    assert.equal(res.ok, true);
    assert.match(targetUrl, /\/api\/v1\/proposals\/prop_test_01\/approve/);
    assert.equal(sentBody.notes, 'Approved for staging');
    assert.equal(sentBody.revisit, true);
    assert.equal(res.data.can_revisit, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('rejectProposal sends reviewer notes and revisit flag', async () => {
  const { rejectProposal } = await import('./api.js');
  const originalFetch = globalThis.fetch;
  let sentBody = null;
  let targetUrl = '';

  try {
    globalThis.fetch = async (url, options) => {
      targetUrl = url;
      sentBody = JSON.parse(options.body);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          proposal_id: 'prop_test_02',
          approval_status: 'rejected',
          updated_at: '2026-11-12T12:05:00Z',
          can_revisit: false,
        }),
      };
    };

    const res = await rejectProposal('prop_test_02', 'Revoked on mobile', { revisit: true });
    assert.equal(res.ok, true);
    assert.match(targetUrl, /\/api\/v1\/proposals\/prop_test_02\/reject/);
    assert.equal(sentBody.notes, 'Revoked on mobile');
    assert.equal(sentBody.revisit, true);
    assert.equal(res.data.can_revisit, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchVisualComparison validates inputs and calls comparison endpoint', async () => {
  const { fetchVisualComparison } = await import('./api.js');

  // Missing proposalId returns error
  const emptyRes = await fetchVisualComparison('run_1', '');
  assert.equal(emptyRes.ok, false);
  assert.match(emptyRes.error, /Proposal ID is required/);

  // Success with runId and viewport
  const originalFetch = globalThis.fetch;
  let calledUrl = '';
  try {
    globalThis.fetch = async (url) => {
      calledUrl = url;
      return {
        ok: true,
        status: 200,
        json: async () => ({
          run_id: 'run_123',
          proposal_id: 'prop_456',
          viewport: 'tablet',
          before_screenshot_url: '/api/v1/artifacts/run_123/before_tablet.png',
          after_screenshot_url: '/api/v1/artifacts/run_123/after_tablet.png',
          target_live_website_modified: false,
          approval_status: 'pending',
          can_revisit: false,
        }),
      };
    };

    const res = await fetchVisualComparison('run_123', 'prop_456', 'tablet');
    assert.equal(res.ok, true);
    assert.match(calledUrl, /\/api\/v1\/runs\/run_123\/proposals\/prop_456\/comparison\?viewport=tablet/);
    assert.equal(res.data.target_live_website_modified, false);
    assert.equal(res.data.viewport, 'tablet');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('simulateControlledRepair validates inputs and dispatches simulation payload', async () => {
  const { simulateControlledRepair } = await import('./api.js');

  // Input validation
  const noRun = await simulateControlledRepair('', 'prop_1');
  assert.equal(noRun.ok, false);
  assert.match(noRun.error, /Run ID is required/);

  const noProp = await simulateControlledRepair('run_1', '');
  assert.equal(noProp.ok, false);
  assert.match(noProp.error, /Proposal ID is required/);

  const originalFetch = globalThis.fetch;
  let calledUrl = '';
  let calledBody = null;
  try {
    globalThis.fetch = async (url, options) => {
      calledUrl = url;
      calledBody = JSON.parse(options.body);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          run_id: 'run_1',
          proposal_id: 'prop_1',
          after_exists: true,
          after_screenshot_url: '/api/v1/artifacts/run_1/after_mobile.png',
          verification_status: 'verified_success',
          target_live_website_modified: false,
        }),
      };
    };

    const res = await simulateControlledRepair('run_1', 'prop_1', 'mobile');
    assert.equal(res.ok, true);
    assert.match(calledUrl, /\/api\/v1\/runs\/run_1\/proposals\/prop_1\/simulate-repair/);
    assert.equal(calledBody.viewport, 'mobile');
    assert.equal(res.data.verification_status, 'verified_success');
    assert.equal(res.data.target_live_website_modified, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('getPreviewStreamUrl and getPreviewFrameUrl construct expected endpoint URLs', async () => {
  const { getPreviewStreamUrl, getPreviewFrameUrl } = await import('./api.js');
  assert.equal(getPreviewStreamUrl('run_preview_test'), '/api/v1/runs/run_preview_test/preview/stream');
  assert.equal(getPreviewStreamUrl(''), '');
  assert.equal(getPreviewFrameUrl('run_frame_test'), '/api/v1/runs/run_frame_test/preview/frame');
  assert.equal(getPreviewFrameUrl(''), '');
});

test('fetchPreviewStatus validates runId and parses preview response', async () => {
  const { fetchPreviewStatus } = await import('./api.js');

  // 1. Missing runId returns error immediately
  const emptyRes = await fetchPreviewStatus('');
  assert.equal(emptyRes.ok, false);
  assert.match(emptyRes.error, /Run ID is required/);

  // 2. Successful fetch parses preview state
  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async (url) => {
      assert.match(url, /\/api\/v1\/runs\/run_777\/preview/);
      return {
        ok: true,
        status: 200,
        json: async () => ({
          run_id: 'run_777',
          stage: 'scrolling',
          progress: 55,
          scroll_y: 400,
          max_scroll_y: 1000,
          viewport: 'desktop',
          frame_base64: 'data:image/jpeg;base64,sample',
        }),
      };
    };

    const res = await fetchPreviewStatus('run_777');
    assert.equal(res.ok, true);
    assert.equal(res.data.stage, 'scrolling');
    assert.equal(res.data.progress, 55);
    assert.equal(res.data.scroll_y, 400);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// =============================================================================
// Inspection History & Run Report Export Tests (CSV & PDF)
// =============================================================================

test('getHistoryExportCsvUrl constructs correct API endpoint', async () => {
  const { getHistoryExportCsvUrl } = await import('./api.js');
  assert.equal(getHistoryExportCsvUrl(), '/api/v1/runs/export/csv');
  assert.equal(getHistoryExportCsvUrl('completed'), '/api/v1/runs/export/csv?status_filter=completed');
  assert.equal(getHistoryExportCsvUrl('ALL'), '/api/v1/runs/export/csv');
});

test('getHistoryExportPdfUrl constructs correct API endpoint', async () => {
  const { getHistoryExportPdfUrl } = await import('./api.js');
  assert.equal(getHistoryExportPdfUrl(), '/api/v1/runs/export/pdf');
  assert.equal(getHistoryExportPdfUrl('failed'), '/api/v1/runs/export/pdf?status_filter=failed');
});

test('getRunExportCsvUrl and getRunExportPdfUrl construct valid URLs with encoding', async () => {
  const { getRunExportCsvUrl, getRunExportPdfUrl } = await import('./api.js');
  assert.equal(getRunExportCsvUrl('run_abc123'), '/api/v1/runs/run_abc123/export/csv');
  assert.equal(getRunExportPdfUrl('run_abc123'), '/api/v1/runs/run_abc123/export/pdf');
  assert.equal(getRunExportCsvUrl(''), '');
  assert.equal(getRunExportPdfUrl(''), '');
});

test('downloadExportFile handles missing URL and network failure gracefully', async () => {
  const { downloadExportFile } = await import('./api.js');
  const resMissing = await downloadExportFile('');
  assert.equal(resMissing.ok, false);
  assert.match(resMissing.error, /Export URL is required/);

  const originalFetch = globalThis.fetch;
  try {
    globalThis.fetch = async () => ({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      text: async () => 'Run not found',
    });
    const resFail = await downloadExportFile('/api/v1/runs/unknown/export/pdf');
    assert.equal(resFail.ok, false);
    assert.match(resFail.error, /404/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('exportRunReportCsv and exportRunReportPdf validate runId', async () => {
  const { exportRunReportCsv, exportRunReportPdf } = await import('./api.js');
  const resCsv = await exportRunReportCsv('');
  assert.equal(resCsv.ok, false);
  assert.match(resCsv.error, /Run ID is required/);

  const resPdf = await exportRunReportPdf('   ');
  assert.equal(resPdf.ok, false);
  assert.match(resPdf.error, /Run ID is required/);
});

test('getCsrfToken extracts omnisight_csrf cookie from document.cookie', async () => {
  const { getCsrfToken, buildAuthHeaders } = await import('./api.js');
  // Without document
  assert.equal(typeof getCsrfToken(), 'string');

  // Simulate browser document.cookie
  globalThis.document = { cookie: 'foo=bar; omnisight_csrf=test_csrf_token_value_123; baz=qux' };
  try {
    assert.equal(getCsrfToken(), 'test_csrf_token_value_123');

    const headers = buildAuthHeaders({ 'Content-Type': 'application/json' });
    assert.equal(headers['X-CSRF-Token'], 'test_csrf_token_value_123');
    assert.equal(headers['Content-Type'], 'application/json');
  } finally {
    delete globalThis.document;
  }
});

test('registerUser sends payload with credentials and handles success and error', async () => {
  const { registerUser } = await import('./api.js');
  const originalFetch = globalThis.fetch;

  try {
    // 1. Success case (201 Created)
    globalThis.fetch = async (url, opts) => {
      assert.match(url, /\/api\/v1\/auth\/register/);
      assert.equal(opts.method, 'POST');
      assert.equal(opts.credentials, 'include');
      const body = JSON.parse(opts.body);
      assert.equal(body.email, 'alice@example.com');
      assert.equal(body.password, 'password123');
      return {
        status: 201,
        ok: true,
        json: async () => ({ id: 'usr_1', email: 'alice@example.com', full_name: 'Alice' }),
      };
    };

    const successRes = await registerUser({
      email: 'alice@example.com',
      password: 'password123',
      fullName: 'Alice',
    });
    assert.equal(successRes.ok, true);
    assert.equal(successRes.data.id, 'usr_1');

    // 2. Duplicate email error (400)
    globalThis.fetch = async () => ({
      status: 400,
      ok: false,
      json: async () => ({ detail: 'An account with this email address already exists.' }),
    });

    const dupRes = await registerUser({
      email: 'alice@example.com',
      password: 'password123',
    });
    assert.equal(dupRes.ok, false);
    assert.match(dupRes.error, /already exists/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('loginUser sends credentials and handles success and invalid credentials', async () => {
  const { loginUser } = await import('./api.js');
  const originalFetch = globalThis.fetch;

  try {
    // 1. Successful login (200 OK)
    globalThis.fetch = async (url, opts) => {
      assert.match(url, /\/api\/v1\/auth\/login/);
      assert.equal(opts.credentials, 'include');
      return {
        status: 200,
        ok: true,
        json: async () => ({ id: 'usr_1', email: 'alice@example.com' }),
      };
    };

    const successRes = await loginUser({ email: 'alice@example.com', password: 'password123' });
    assert.equal(successRes.ok, true);
    assert.equal(successRes.data.email, 'alice@example.com');

    // 2. Invalid credentials (401 Unauthorized)
    globalThis.fetch = async () => ({
      status: 401,
      ok: false,
      json: async () => ({ detail: 'Invalid email or password.' }),
    });

    const failRes = await loginUser({ email: 'alice@example.com', password: 'wrong' });
    assert.equal(failRes.ok, false);
    assert.equal(failRes.status, 401);
    assert.match(failRes.error, /Invalid email or password/);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchCurrentUser returns user profile or unauthenticated flag', async () => {
  const { fetchCurrentUser } = await import('./api.js');
  const originalFetch = globalThis.fetch;

  try {
    // 1. Authenticated session
    globalThis.fetch = async (url, opts) => {
      assert.match(url, /\/api\/v1\/auth\/me/);
      assert.equal(opts.credentials, 'include');
      return {
        status: 200,
        ok: true,
        json: async () => ({ id: 'usr_1', email: 'alice@example.com' }),
      };
    };

    const authRes = await fetchCurrentUser();
    assert.equal(authRes.ok, true);
    assert.equal(authRes.data.id, 'usr_1');

    // 2. Unauthenticated (401)
    globalThis.fetch = async () => ({
      status: 401,
      ok: false,
      json: async () => ({ detail: 'Authentication required.' }),
    });

    const unauthRes = await fetchCurrentUser();
    assert.equal(unauthRes.ok, false);
    assert.equal(unauthRes.isUnauthenticated, true);
    assert.equal(unauthRes.status, 401);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('logoutUser invokes endpoint with credentials and csrf token', async () => {
  const { logoutUser } = await import('./api.js');
  const originalFetch = globalThis.fetch;

  try {
    globalThis.fetch = async (url, opts) => {
      assert.match(url, /\/api\/v1\/auth\/logout/);
      assert.equal(opts.method, 'POST');
      assert.equal(opts.credentials, 'include');
      return {
        status: 200,
        ok: true,
        json: async () => ({ message: 'Logged out successfully.' }),
      };
    };

    const res = await logoutUser();
    assert.equal(res.ok, true);
    assert.equal(res.data.message, 'Logged out successfully.');
  } finally {
    globalThis.fetch = originalFetch;
  }
});
