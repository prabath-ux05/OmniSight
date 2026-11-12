/**
 * Polling resilience and findings view state resolution helpers.
 */

export const MAX_CONSECUTIVE_POLL_ERRORS = 20;

/**
 * Resolves the display state for the Findings section.
 *
 * Guaranteed rules:
 * 1. 'loading' when isLoading is true.
 * 2. 'error' when findingsError is present.
 * 3. 'no_run' when runId is not set.
 * 4. 'has_findings' when count > 0.
 * 5. 'failed' when runStatus is 'failed' or runError is present.
 * 6. 'in_progress' when runStatus is 'queued', 'capturing', or 'analyzing'.
 * 7. 'clean' ONLY when runStatus is 'completed' AND no runError exists.
 * 8. 'pending' when run status is unknown, null, or interrupted.
 *
 * @param {object} params
 * @returns {'loading' | 'error' | 'no_run' | 'has_findings' | 'failed' | 'in_progress' | 'pending' | 'clean'}
 */
export function getFindingsViewState({
  isLoading = false,
  findingsError = null,
  runId = null,
  count = 0,
  runStatus = null,
  runError = null,
} = {}) {
  if (isLoading) return 'loading';
  if (findingsError) return 'error';
  if (!runId) return 'no_run';

  const normalizedStatus = typeof runStatus === 'string' ? runStatus.trim().toLowerCase() : '';
  const hasError = Boolean(runError && String(runError).trim());

  // Failed status or execution error takes strict priority over count > 0
  if (normalizedStatus === 'failed' || hasError) {
    return 'failed';
  }

  // Active findings take priority for non-failed runs
  if (count > 0) {
    return 'has_findings';
  }

  // Active in-progress execution stages
  if (normalizedStatus === 'queued' || normalizedStatus === 'capturing' || normalizedStatus === 'analyzing') {
    return 'in_progress';
  }

  // Clean run ONLY when completed AND no error
  if (normalizedStatus === 'completed' && !hasError) {
    return 'clean';
  }

  // Interrupted, unconfirmed, or unknown status (e.g. null, aborted, cancelled)
  return 'pending';
}
