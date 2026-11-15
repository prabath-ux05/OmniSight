import React from 'react';

/**
 * HomePage renders the polished, product-focused OmniSight landing dashboard.
 *
 * Communicates core platform capabilities:
 * - Multimodal Website Inspection
 * - Visual Defect Detection
 * - DOM & Layout Analysis
 * - Evidence-Based Repair Proposals
 * - Controlled Sandbox Repair
 * - Before/After Verification
 *
 * Displays a clean, user-friendly summary of recent inspection activity supported
 * strictly by real backend data, without technical monitoring panels or raw developer narration.
 */
export default function HomePage({
  runsList = [],
  isRunsLoading = false,
  runsError = '',
  onRefreshRuns = () => {},
  currentRun = null,
  onSelectView = () => {},
  onSelectRun = () => {},
}) {
  const getStatusBadgeClass = (status) => {
    const s = typeof status === 'string' ? status.trim().toLowerCase() : '';
    switch (s) {
      case 'completed':
        return 'badge-success';
      case 'failed':
      case 'error':
      case 'cancelled':
        return 'badge-danger';
      case 'capturing':
      case 'analyzing':
      case 'repair_pending':
      case 'repairing':
      case 'verifying':
        return 'badge-warning';
      case 'queued':
      default:
        return 'badge-neutral';
    }
  };

  const formatTimestamp = (isoString) => {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) return isoString;
      return date.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const recentRuns = Array.isArray(runsList) ? runsList.slice(0, 5) : [];

  return (
    <div className="home-view-container">
      {/* 1. Welcome / Hero Section */}
      <section className="shell-hero-card home-hero-banner" aria-label="Welcome Banner">
        <div className="home-hero-badge-row">
          <span className="shell-hero-badge">
            <span className="badge-glow-dot" aria-hidden="true"></span>
            OmniSight Platform
          </span>

          <span className="home-guest-pill" title="Autonomous self-healing and inspection workspace">
            <span className="guest-pill-icon" aria-hidden="true">🛡️</span>
            <span>Enterprise UI Reliability</span>
          </span>
        </div>

        <h1 className="shell-hero-title">Autonomous UI Quality &amp; Self-Healing Platform</h1>

        <p className="shell-hero-desc">
          OmniSight automatically inspects web applications for visual regressions, broken DOM elements,
          and responsive layout overflows using multimodal vision models. Generate robust self-healing
          locator proposals, verify repairs within an isolated controlled sandbox, and govern code changes
          with pull request safety gates.
        </p>

        <div className="shell-hero-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => onSelectView('inspection')}
          >
            🔍 Launch Live Inspection →
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onSelectView('history')}
          >
            📋 Review Inspection History ({runsList.length})
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onSelectView('proposals')}
          >
            🛡️ Repair Proposals
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onSelectView('repair')}
          >
            🔧 Repair Workspace
          </button>
        </div>
      </section>

      {/* 2. Active Session Card (Only when an active run is currently loaded in memory) */}
      {currentRun && (
        <section className="card home-active-run-banner" aria-label="Active Inspection Session">
          <div className="active-run-banner-content">
            <div className="active-run-info">
              <span className="active-run-pill">Current Inspection Session</span>
              <h3 className="active-run-title">
                Run <code>{currentRun.run_id ? String(currentRun.run_id) : '—'}</code>
              </h3>
              <p className="active-run-url" title={currentRun.url || ''}>
                Target: <code>{currentRun.url || '—'}</code>
              </p>
            </div>
            <div className="active-run-actions">
              <span className={`badge ${getStatusBadgeClass(currentRun.status)}`}>
                {typeof currentRun.status === 'string' && currentRun.status.trim()
                  ? currentRun.status.trim().toUpperCase()
                  : 'UNKNOWN'}
              </span>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => onSelectRun(currentRun)}
              >
                Open in Live Studio →
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  onSelectRun(currentRun);
                  onSelectView('proposals');
                }}
              >
                🛡️ Repair Proposals →
              </button>
            </div>
          </div>
        </section>
      )}

      {/* 3. Platform Capabilities Section (6 Feature Cards) */}
      <section className="home-capabilities-section" aria-label="Platform Capabilities">
        <div className="section-title-row">
          <div>
            <h2 className="section-heading">Platform Capabilities</h2>
            <p className="section-hint">An end-to-end multimodal inspection, analysis, and self-healing lifecycle</p>
          </div>
        </div>

        <div className="shell-grid-cards capabilities-grid">
          {/* Card 1: Multimodal Website Inspection */}
          <div className="shell-feature-card capability-card">
            <div className="feature-icon-wrapper icon-blue">
              <span className="shell-feature-icon" aria-hidden="true">🌐</span>
            </div>
            <h3 className="shell-feature-title">Multimodal Website Inspection</h3>
            <p className="shell-feature-desc">
              Headless browser automation drives deep navigation across desktop, tablet, and mobile
              viewport presets, capturing pixel-perfect full-page screenshots and structural DOM snapshots.
            </p>
            <div className="capability-card-footer">
              <span className="feature-tag">Playwright Headless</span>
              <span className="feature-tag">Multi-Viewport</span>
            </div>
          </div>

          {/* Card 2: Visual Defect Detection */}
          <div className="shell-feature-card capability-card">
            <div className="feature-icon-wrapper icon-amber">
              <span className="shell-feature-icon" aria-hidden="true">🎯</span>
            </div>
            <h3 className="shell-feature-title">Visual Defect Detection</h3>
            <p className="shell-feature-desc">
              Advanced multimodal vision models identify layout overflows, missing interactive elements,
              and broken image assets with pinpoint bounding-box coordinates and confidence scores.
            </p>
            <div className="capability-card-footer">
              <span className="feature-tag">Gemini VLM</span>
              <span className="feature-tag">Bounding Boxes</span>
            </div>
          </div>

          {/* Card 3: DOM & Layout Analysis */}
          <div className="shell-feature-card capability-card">
            <div className="feature-icon-wrapper icon-purple">
              <span className="shell-feature-icon" aria-hidden="true">📐</span>
            </div>
            <h3 className="shell-feature-title">DOM &amp; Layout Analysis</h3>
            <p className="shell-feature-desc">
              Deterministic DOM traversal inspects element geometries, scroll dimensions, and client
              rectangles to corroborate visual discrepancies directly against the live page tree.
            </p>
            <div className="capability-card-footer">
              <span className="feature-tag">DOM Traversal</span>
              <span className="feature-tag">Client Rects</span>
            </div>
          </div>

          {/* Card 4: Evidence-Based Repair Proposals */}
          <div
            className="shell-feature-card capability-card"
            role="button"
            tabIndex={0}
            onClick={() => onSelectView('proposals')}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelectView('proposals'); }}
            style={{ cursor: 'pointer' }}
            title="Navigate to Repair Proposals"
          >
            <div className="feature-icon-wrapper icon-cyan">
              <span className="shell-feature-icon" aria-hidden="true">💡</span>
            </div>
            <h3 className="shell-feature-title">Evidence-Based Repair Proposals</h3>
            <p className="shell-feature-desc">
              Synthesize resilient locator recommendations (data-testids, stable semantic IDs, accessible roles)
              accompanied by minimal unified diff patches for automated test suite repair.
            </p>
            <div className="capability-card-footer">
              <span className="feature-tag">Self-Healing</span>
              <span className="feature-tag">Unified Diff</span>
              <span className="btn-link btn-link-sm" style={{ marginLeft: 'auto' }}>Open Proposals →</span>
            </div>
          </div>

          {/* Card 5: Controlled Sandbox Repair */}
          <div
            className="shell-feature-card capability-card"
            role="button"
            tabIndex={0}
            onClick={() => onSelectView('repair')}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelectView('repair'); }}
            style={{ cursor: 'pointer' }}
            title="Navigate to Repair Workspace"
          >
            <div className="feature-icon-wrapper icon-emerald">
              <span className="shell-feature-icon" aria-hidden="true">🔒</span>
            </div>
            <h3 className="shell-feature-title">Controlled Sandbox Repair</h3>
            <p className="shell-feature-desc">
              Proposed repairs execute strictly within an isolated local sandbox. The live production
              website is never modified automatically, and original defect screenshots are preserved immutably.
            </p>
            <div className="capability-card-footer">
              <span className="feature-tag">Local Sandbox</span>
              <span className="feature-tag">Live Site Protected</span>
              <span className="btn-link btn-link-sm" style={{ marginLeft: 'auto' }}>Open Workspace →</span>
            </div>
          </div>

          {/* Card 6: Before/After Verification */}
          <div className="shell-feature-card capability-card">
            <div className="feature-icon-wrapper icon-indigo">
              <span className="shell-feature-icon" aria-hidden="true">⚖️</span>
            </div>
            <h3 className="shell-feature-title">Before / After Verification</h3>
            <p className="shell-feature-desc">
              Interactive side-by-side split views and slider comparisons contrast original defect evidence
              against repaired post-patch rendering under identical viewport dimensions.
            </p>
            <div className="capability-card-footer">
              <span className="feature-tag">Split-View</span>
              <span className="feature-tag">Interactive Slider</span>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Recent Inspection Activity Section (Supported strictly by real backend data) */}
      <section className="card home-activity-card" aria-label="Recent Activity">
        <div className="card-header-with-actions">
          <div>
            <h2 className="card-title">Recent Inspection Activity</h2>
            <p className="card-description">
              Recent automated inspection runs and defect detection history.
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefreshRuns}
            disabled={isRunsLoading}
            title="Refresh recent activity"
          >
            {isRunsLoading ? 'Refreshing…' : '↻ Refresh Activity'}
          </button>
        </div>

        {/* Error State */}
        {runsError && (
          <div className="alert-box alert-error home-activity-error" role="alert">
            <span>Failed to load recent activity: {runsError}</span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onRefreshRuns}
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading State */}
        {isRunsLoading && runsList.length === 0 ? (
          <div className="empty-state">
            <span className="spinner-sm" aria-hidden="true"></span>
            <p className="empty-state-text">Loading recent inspection runs…</p>
          </div>
        ) : runsList.length === 0 ? (
          /* Empty State */
          <div className="empty-state">
            <div className="empty-state-icon" aria-hidden="true">📋</div>
            <p className="empty-state-title">No Recent Inspection Activity</p>
            <p className="empty-state-text">
              No inspection runs found in the audit record. Open the Live Inspection Studio to initiate your first automated run.
            </p>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              style={{ marginTop: '1rem' }}
              onClick={() => onSelectView('inspection')}
            >
              Launch Live Inspection Studio →
            </button>
          </div>
        ) : (
          /* Populated State (Real Backend Data) */
          <>
            <div className="table-responsive">
              <table className="history-table recent-activity-table">
                <thead>
                  <tr>
                    <th>Run ID</th>
                    <th>Target URL</th>
                    <th>Status</th>
                    <th>Created At</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {recentRuns.map((run) => (
                    <tr key={run.run_id || Math.random()} className="history-row">
                      <td>
                        <span className="run-id-pill">{run.run_id ? String(run.run_id) : '—'}</span>
                      </td>
                      <td>
                        <span className="history-url-cell" title={run.url || ''}>
                          {run.url || '—'}
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${getStatusBadgeClass(run.status)}`}>
                          {typeof run.status === 'string' && run.status.trim()
                            ? run.status.trim().toUpperCase()
                            : 'UNKNOWN'}
                        </span>
                      </td>
                      <td>
                        <span className="timestamp-cell">
                          {formatTimestamp(run.created_at)}
                        </span>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => onSelectRun(run)}
                          title={`Inspect run ${run.run_id || '—'}`}
                        >
                          Inspect Run →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {runsList.length > 5 && (
              <div className="home-activity-footer">
                <button
                  type="button"
                  className="btn btn-link"
                  onClick={() => onSelectView('history')}
                >
                  View all {runsList.length} inspection runs in History →
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </div>
  );
}
