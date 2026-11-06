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
          model: 'gemini-1.5-flash',
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
