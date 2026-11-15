import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import {
  ROUTES,
  parseRoute,
  formatRoute,
  navigateRoute,
} from './router.js';

describe('OmniSight Navigation & Browser History Scenarios', () => {
  describe('Scenario A: Inspection to Repair Proposal', () => {
    it('navigates from completed inspection to the corresponding repair proposal', () => {
      const completedRunId = 'run_completed_789';
      const proposalId = 'prop_auto_001';

      // 1. Initial state at Live Inspection Studio
      const initialRoute = parseRoute('/inspection');
      assert.equal(initialRoute.view, ROUTES.INSPECTION);

      // 2. Inspection completed -> destination URL is formatted with run and proposal IDs
      const targetUrl = formatRoute({
        view: ROUTES.PROPOSALS,
        runId: completedRunId,
        proposalId,
      });
      assert.equal(targetUrl, `/runs/${completedRunId}/proposals/${proposalId}`);

      // 3. Destination route parses correctly and preserves identifiers
      const destRoute = parseRoute(targetUrl);
      assert.equal(destRoute.view, ROUTES.PROPOSALS);
      assert.equal(destRoute.runId, completedRunId);
      assert.equal(destRoute.proposalId, proposalId);
    });

    it('handles completed run without pre-generated proposals gracefully', () => {
      const completedRunId = 'run_clean_999';

      const targetUrl = formatRoute({
        view: ROUTES.PROPOSALS,
        runId: completedRunId,
      });
      assert.equal(targetUrl, `/runs/${completedRunId}/proposals`);

      const destRoute = parseRoute(targetUrl);
      assert.equal(destRoute.view, ROUTES.PROPOSALS);
      assert.equal(destRoute.runId, completedRunId);
      assert.equal(destRoute.proposalId, null);
    });
  });

  describe('Scenario B: Repair Proposal Navigation', () => {
    it('navigates to Repair Proposals from main menu', () => {
      const menuRoute = parseRoute('/proposals');
      assert.equal(menuRoute.view, ROUTES.PROPOSALS);
      assert.equal(menuRoute.proposalId, null);
    });

    it('opens a specific proposal and preserves proposal details', () => {
      const targetUrl = formatRoute({
        view: ROUTES.PROPOSALS,
        runId: 'run_audit_444',
        proposalId: 'prop_specific_333',
      });
      const parsed = parseRoute(targetUrl);
      assert.equal(parsed.view, ROUTES.PROPOSALS);
      assert.equal(parsed.runId, 'run_audit_444');
      assert.equal(parsed.proposalId, 'prop_specific_333');
    });
  });

  describe('Scenario C: Browser Back Navigation Sequence', () => {
    it('correctly parses history trail Home -> Live Studio -> Inspection Results -> Repair Proposal in reverse', () => {
      // History trail sequence
      const historyStack = [
        formatRoute({ view: ROUTES.HOME }),
        formatRoute({ view: ROUTES.INSPECTION }),
        formatRoute({ view: ROUTES.RESULTS, runId: 'run_seq_101' }),
        formatRoute({ view: ROUTES.PROPOSALS, runId: 'run_seq_101', proposalId: 'prop_seq_202' }),
      ];

      assert.deepEqual(historyStack, [
        '/',
        '/inspection',
        '/inspection/run_seq_101',
        '/runs/run_seq_101/proposals/prop_seq_202',
      ]);

      // Pop 1: Back from Repair Proposal to Inspection Results
      const backStep1 = parseRoute(historyStack[2]);
      assert.equal(backStep1.view, ROUTES.RESULTS);
      assert.equal(backStep1.runId, 'run_seq_101');

      // Pop 2: Back from Inspection Results to Live Studio
      const backStep2 = parseRoute(historyStack[1]);
      assert.equal(backStep2.view, ROUTES.INSPECTION);
      assert.equal(backStep2.runId, null);

      // Pop 3: Back from Live Studio to Home
      const backStep3 = parseRoute(historyStack[0]);
      assert.equal(backStep3.view, ROUTES.HOME);
    });
  });

  describe('Scenario D: Browser Forward Navigation Sequence', () => {
    it('correctly restores visited pages and context when stepping forward', () => {
      const historyStack = [
        formatRoute({ view: ROUTES.HOME }),
        formatRoute({ view: ROUTES.INSPECTION }),
        formatRoute({ view: ROUTES.RESULTS, runId: 'run_seq_101' }),
        formatRoute({ view: ROUTES.PROPOSALS, runId: 'run_seq_101', proposalId: 'prop_seq_202' }),
      ];

      // Forward step 1: Home -> Live Studio
      const fwdStep1 = parseRoute(historyStack[1]);
      assert.equal(fwdStep1.view, ROUTES.INSPECTION);

      // Forward step 2: Live Studio -> Inspection Results (restores runId)
      const fwdStep2 = parseRoute(historyStack[2]);
      assert.equal(fwdStep2.view, ROUTES.RESULTS);
      assert.equal(fwdStep2.runId, 'run_seq_101');

      // Forward step 3: Inspection Results -> Repair Proposal (restores proposalId)
      const fwdStep3 = parseRoute(historyStack[3]);
      assert.equal(fwdStep3.view, ROUTES.PROPOSALS);
      assert.equal(fwdStep3.runId, 'run_seq_101');
      assert.equal(fwdStep3.proposalId, 'prop_seq_202');
    });
  });

  describe('Scenario E: Direct Route and Refresh', () => {
    it('correctly parses direct deep-link to valid Repair Proposal URL on refresh', () => {
      const directUrl = '/runs/run_deep_555/proposals/prop_target_777';
      const parsed = parseRoute(directUrl);

      assert.equal(parsed.view, ROUTES.PROPOSALS);
      assert.equal(parsed.runId, 'run_deep_555');
      assert.equal(parsed.proposalId, 'prop_target_777');
    });

    it('correctly handles direct query-param deep-link on refresh', () => {
      const directQueryUrl = '/proposals?runId=run_query_111&proposalId=prop_query_222';
      const parsed = parseRoute(directQueryUrl);

      assert.equal(parsed.view, ROUTES.PROPOSALS);
      assert.equal(parsed.runId, 'run_query_111');
      assert.equal(parsed.proposalId, 'prop_query_222');
    });

    it('gracefully falls back on malformed or invalid direct route without throwing', () => {
      const malformedUrl = '////unknown-route///???invalid=';
      const parsed = parseRoute(malformedUrl);

      assert.equal(parsed.view, ROUTES.HOME);
    });
  });
});
