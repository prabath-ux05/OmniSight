import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  ROUTES,
  parseRoute,
  formatRoute,
  navigateRoute,
  subscribeToNavigation,
} from './router.js';

describe('OmniSight Client-Side Router', () => {
  describe('Route Parsing (parseRoute)', () => {
    it('parses root "/" as home view', () => {
      const res = parseRoute('/');
      assert.equal(res.view, ROUTES.HOME);
      assert.equal(res.runId, null);
    });

    it('parses "/home" as home view', () => {
      const res = parseRoute('/home');
      assert.equal(res.view, ROUTES.HOME);
    });

    it('parses "/inspection" as inspection view (Live Studio)', () => {
      const res = parseRoute('/inspection');
      assert.equal(res.view, ROUTES.INSPECTION);
      assert.equal(res.runId, null);
    });

    it('parses "/live" as inspection view', () => {
      const res = parseRoute('/live');
      assert.equal(res.view, ROUTES.INSPECTION);
    });

    it('parses "/inspection/run_abc123" as results view with runId', () => {
      const res = parseRoute('/inspection/run_abc123');
      assert.equal(res.view, ROUTES.RESULTS);
      assert.equal(res.runId, 'run_abc123');
    });

    it('parses "/results/run_test_456" as results view with runId', () => {
      const res = parseRoute('/results/run_test_456');
      assert.equal(res.view, ROUTES.RESULTS);
      assert.equal(res.runId, 'run_test_456');
    });

    it('parses "/history" as history view', () => {
      const res = parseRoute('/history');
      assert.equal(res.view, ROUTES.HISTORY);
    });

    it('parses "/proposals" as proposals view', () => {
      const res = parseRoute('/proposals');
      assert.equal(res.view, ROUTES.PROPOSALS);
      assert.equal(res.proposalId, null);
    });

    it('parses "/proposals/prop_999" as proposals view with proposalId', () => {
      const res = parseRoute('/proposals/prop_999');
      assert.equal(res.view, ROUTES.PROPOSALS);
      assert.equal(res.proposalId, 'prop_999');
    });

    it('parses "/runs/run_123/proposals" as proposals view with runId', () => {
      const res = parseRoute('/runs/run_123/proposals');
      assert.equal(res.view, ROUTES.PROPOSALS);
      assert.equal(res.runId, 'run_123');
    });

    it('parses "/runs/run_123/proposals/prop_555" as proposals view with both runId and proposalId', () => {
      const res = parseRoute('/runs/run_123/proposals/prop_555');
      assert.equal(res.view, ROUTES.PROPOSALS);
      assert.equal(res.runId, 'run_123');
      assert.equal(res.proposalId, 'prop_555');
    });

    it('parses "/repair" as repair workspace view', () => {
      const res = parseRoute('/repair');
      assert.equal(res.view, ROUTES.REPAIR);
    });

    it('parses "/repair/run_777" as repair view with runId', () => {
      const res = parseRoute('/repair/run_777');
      assert.equal(res.view, ROUTES.REPAIR);
      assert.equal(res.runId, 'run_777');
    });

    it('parses "/repair/run_777/find_888" as repair view with runId and findingId', () => {
      const res = parseRoute('/repair/run_777/find_888');
      assert.equal(res.view, ROUTES.REPAIR);
      assert.equal(res.runId, 'run_777');
      assert.equal(res.findingId, 'find_888');
    });

    it('parses "/profile", "/about", and "/settings"', () => {
      assert.equal(parseRoute('/profile').view, ROUTES.PROFILE);
      assert.equal(parseRoute('/about').view, ROUTES.ABOUT);
      assert.equal(parseRoute('/settings').view, ROUTES.SETTINGS);
    });

    it('extracts query parameters for runId, proposalId, and findingId', () => {
      const res = parseRoute('/proposals?runId=run_abc&proposalId=prop_xyz&findingId=find_1');
      assert.equal(res.view, ROUTES.PROPOSALS);
      assert.equal(res.runId, 'run_abc');
      assert.equal(res.proposalId, 'prop_xyz');
      assert.equal(res.findingId, 'find_1');
    });

    it('falls back to hash deep-links (e.g. #/proposals/prop_1)', () => {
      const res = parseRoute('/index.html#/proposals/prop_hash_1');
      assert.equal(res.view, ROUTES.PROPOSALS);
      assert.equal(res.proposalId, 'prop_hash_1');
    });

    it('gracefully handles unknown routes by defaulting to home', () => {
      const res = parseRoute('/some/unknown/nested/route');
      assert.equal(res.view, ROUTES.HOME);
    });
  });

  describe('Route Formatting (formatRoute)', () => {
    it('formats home route to "/"', () => {
      assert.equal(formatRoute({ view: ROUTES.HOME }), '/');
    });

    it('formats inspection studio route to "/inspection"', () => {
      assert.equal(formatRoute({ view: ROUTES.INSPECTION }), '/inspection');
    });

    it('formats results route with runId to "/inspection/run_123"', () => {
      assert.equal(formatRoute({ view: ROUTES.RESULTS, runId: 'run_123' }), '/inspection/run_123');
    });

    it('formats history route to "/history"', () => {
      assert.equal(formatRoute({ view: ROUTES.HISTORY }), '/history');
    });

    it('formats proposals route without params to "/proposals"', () => {
      assert.equal(formatRoute({ view: ROUTES.PROPOSALS }), '/proposals');
    });

    it('formats proposals route with runId to "/runs/run_123/proposals"', () => {
      assert.equal(formatRoute({ view: ROUTES.PROPOSALS, runId: 'run_123' }), '/runs/run_123/proposals');
    });

    it('formats proposals route with proposalId to "/proposals/prop_456"', () => {
      assert.equal(formatRoute({ view: ROUTES.PROPOSALS, proposalId: 'prop_456' }), '/proposals/prop_456');
    });

    it('formats proposals route with both runId and proposalId', () => {
      assert.equal(
        formatRoute({ view: ROUTES.PROPOSALS, runId: 'run_123', proposalId: 'prop_456' }),
        '/runs/run_123/proposals/prop_456'
      );
    });

    it('formats repair workspace route with runId and findingId', () => {
      assert.equal(
        formatRoute({ view: ROUTES.REPAIR, runId: 'run_123', findingId: 'find_001' }),
        '/repair/run_123/find_001'
      );
    });

    it('formats profile route to "/profile"', () => {
      assert.equal(formatRoute({ view: ROUTES.PROFILE }), '/profile');
    });
  });

  describe('History and Navigation Helpers', () => {
    it('returns target URL when calling navigateRoute in Node environment', () => {
      const target = navigateRoute({ view: ROUTES.PROPOSALS, runId: 'run_x', proposalId: 'prop_y' });
      assert.equal(target, '/runs/run_x/proposals/prop_y');
    });

    it('subscribeToNavigation returns a no-op unsubscription function in non-browser environments', () => {
      const unsubscribe = subscribeToNavigation(() => {});
      assert.equal(typeof unsubscribe, 'function');
      unsubscribe();
    });
  });
});
