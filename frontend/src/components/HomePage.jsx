import React from 'react';
import InspectionForm from './InspectionForm';

/**
 * HomePage renders the polished OmniSight landing view.
 *
 * Features:
 * - Introduction, welcome banner & primary calls to action
 * - Guest mode support (no authentication required)
 * - URL input & inspection dispatch via reused InspectionForm
 * - Quick navigation to Inspection, History, Repair Workflow, and About
 * - System overview & recent activity supported strictly by real backend API data
 */
export default function HomePage({
  health,
  isHealthLoading,
  onRefreshHealth,
  runsList = [],
  isRunsLoading = false,
  runsError = '',
  onRefreshRuns = () => {},
  currentRun = null,
  onStartInspection,
  isRunLoading = false,
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
      {/* 1. Welcome & Introduction Hero Banner */}
      <section className="shell-hero-card home-hero-banner" aria-label="Welcome Banner">
        <div className="home-hero-badge-row">
          <span className="shell-hero-badge">
            <span
              className={`status-dot ${health?.status === 'ok' ? 'status-dot-online' : 'status-dot-offline'}`}
              aria-hidden="true"
            ></span>
            OmniSight Multimodal Platform
          </span>

          <span className="home-guest-pill" title="Guest mode is active for all inspection tools">
            <span className="guest-pill-icon" aria-hidden="true">👤</span>
            <span>Guest Session Active</span>
          </span>
        </div>

        <h1 className="shell-hero-title">Autonomous UI Quality &amp; Self-Healing Agent</h1>

        <p className="shell-hero-desc">
          OmniSight automatically inspects web applications for visual regressions, broken DOM elements,
          and layout overflows using multimodal vision models. Generate robust self-healing locator patches
          and manage pull request governance with safety gates.
        </p>

        <div className="home-guest-callout">
          <p className="home-guest-callout-text">
            <strong>Guest Mode:</strong> Full access enabled without sign-in. Launch real-time inspections,
            audit past runs, and review repair proposals directly.
          </p>
        </div>

        <div className="shell-hero-actions">
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => onSelectView('inspection')}
          >
            Open Live Inspection Studio →
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onSelectView('history')}
          >
            Browse Run History ({runsList.length})
          </button>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => onSelectView('repair')}
          >
            Review Repair Proposals
          </button>
        </div>
      </section>

      {/* 2. System Overview Bar (Real Backend API Data Only) */}
      <section className="home-overview-section" aria-label="System Overview">
        <div className="home-overview-grid">
          {/* Backend Health Box */}
          <div className="home-overview-card">
            <div className="overview-card-header">
              <span className="overview-card-label">Backend Service</span>
              <button
                type="button"
                className="btn-link overview-ping-btn"
                onClick={onRefreshHealth}
                disabled={isHealthLoading}
                title="Ping backend health"
              >
                {isHealthLoading ? 'Pinging...' : '↻ Ping'}
              </button>
            </div>
            <div className="overview-card-body">
              <span
                className="overview-card-value"
                style={{ color: health?.status === 'ok' ? '#10b981' : '#ef4444' }}
              >
                {health?.status === 'ok' ? 'ONLINE' : (isHealthLoading ? 'CHECKING...' : 'OFFLINE')}
              </span>
              <span className="overview-card-subtext">
                {health?.version ? `FastAPI v${health.version}` : (health?.error || 'Service Unreachable')}
              </span>
            </div>
          </div>

          {/* Database Connection Box */}
          <div className="home-overview-card">
            <div className="overview-card-header">
              <span className="overview-card-label">Audit Database</span>
              <span className="overview-card-chip">PostgreSQL</span>
            </div>
            <div className="overview-card-body">
              {isRunsLoading ? (
                <>
                  <span className="overview-card-value" style={{ color: '#3b82f6' }}>
                    QUERYING...
                  </span>
                  <span className="overview-card-subtext">Fetching recorded runs...</span>
                </>
              ) : runsError ? (
                <>
                  <span className="overview-card-value" style={{ color: '#ef4444' }}>
                    UNREACHABLE
                  </span>
                  <span className="overview-card-subtext">Run queries failed</span>
                </>
              ) : runsList.length > 0 ? (
                <>
                  <span className="overview-card-value" style={{ color: '#10b981' }}>
                    CONNECTED
                  </span>
                  <span className="overview-card-subtext">
                    {runsList.length} {runsList.length === 1 ? 'run' : 'runs'} queried
                  </span>
                </>
              ) : (
                <>
                  <span className="overview-card-value" style={{ color: '#10b981' }}>
                    ONLINE (0 RUNS)
                  </span>
                  <span className="overview-card-subtext">Query succeeded (0 runs)</span>
                </>
              )}
            </div>
          </div>

          {/* Total Recorded Runs Box */}
          <div className="home-overview-card">
            <div className="overview-card-header">
              <span className="overview-card-label">Recorded Runs</span>
              <button
                type="button"
                className="btn-link overview-ping-btn"
                onClick={onRefreshRuns}
                disabled={isRunsLoading}
                title="Refresh run count from PostgreSQL"
              >
                {isRunsLoading ? 'Refreshing...' : '↻ Refresh'}
              </button>
            </div>
            <div className="overview-card-body">
              <span className="overview-card-value">
                {isRunsLoading ? '...' : runsList.length}
              </span>
              <span className="overview-card-subtext">
                Audited in PostgreSQL
              </span>
            </div>
          </div>

          {/* Active Run Box */}
          <div className="home-overview-card">
            <div className="overview-card-header">
              <span className="overview-card-label">Active Run</span>
              {currentRun && (
                <button
                  type="button"
                  className="btn-link overview-ping-btn"
                  onClick={() => onSelectView('inspection')}
                >
                  View Studio →
                </button>
              )}
            </div>
            <div className="overview-card-body">
              <span className="overview-card-value overview-run-id">
                {currentRun?.run_id
                  ? (typeof currentRun.run_id === 'string'
                      ? (currentRun.run_id.length > 8 ? currentRun.run_id.slice(0, 8) + '...' : currentRun.run_id)
                      : String(currentRun.run_id))
                  : 'NONE'}
              </span>
              <span className="overview-card-subtext">
                {currentRun
                  ? (typeof currentRun.status === 'string' && currentRun.status.trim()
                      ? `Status: ${currentRun.status.trim().toUpperCase()}`
                      : 'Status: UNKNOWN')
                  : 'Studio Idle'}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Active Run Banner (If an active run is currently loaded) */}
      {currentRun && (
        <section className="card home-active-run-banner" aria-label="Current Run Notification">
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
            </div>
          </div>
        </section>
      )}

      {/* 4. Inspection Launch Form (Reusing InspectionForm) */}
      <section className="home-inspection-section" aria-label="Dispatch New Inspection">
        <InspectionForm
          onSubmit={onStartInspection}
          isLoading={isRunLoading}
        />
      </section>

      {/* 5. Quick Navigation to Key Modules */}
      <section className="home-navigation-section" aria-label="Quick Navigation">
        <div className="section-title-row">
          <h2 className="section-heading">Platform Modules &amp; Workflows</h2>
          <span className="section-hint">Explore core capabilities and audit logs</span>
        </div>

        <div className="shell-grid-cards">
          {/* Card 1: Live Inspection Studio */}
          <div className="shell-feature-card home-module-card">
            <span className="shell-feature-icon" aria-hidden="true">🔍</span>
            <h3 className="shell-feature-title">Live Inspection Studio</h3>
            <p className="shell-feature-desc">
              Execute real-time browser automation sessions with Playwright, review full-page screenshots,
              and inspect multimodal vision defect findings with localized bounding boxes.
            </p>
            <button
              type="button"
              className="btn btn-secondary btn-sm home-card-btn"
              onClick={() => onSelectView('inspection')}
            >
              Open Inspection Studio →
            </button>
          </div>

          {/* Card 2: Run History & Audit */}
          <div className="shell-feature-card home-module-card">
            <span className="shell-feature-icon" aria-hidden="true">📋</span>
            <h3 className="shell-feature-title">Run History &amp; Audit</h3>
            <p className="shell-feature-desc">
              Browse the complete audit log of all historical inspection runs persisted in PostgreSQL.
              Filter by URL or Run ID and review terminal completion statuses.
            </p>
            <button
              type="button"
              className="btn btn-secondary btn-sm home-card-btn"
              onClick={() => onSelectView('history')}
            >
              View Run History ({runsList.length}) →
            </button>
          </div>

          {/* Card 3: Repair Proposal Workflow */}
          <div className="shell-feature-card home-module-card">
            <span className="shell-feature-icon" aria-hidden="true">🛡️</span>
            <h3 className="shell-feature-title">Repair Workflow &amp; Governance</h3>
            <p className="shell-feature-desc">
              Evaluate self-healing locator suggestions with confidence scoring, heuristic fallback,
              and developer approval gates for safe pull request dispatch.
            </p>
            <button
              type="button"
              className="btn btn-secondary btn-sm home-card-btn"
              onClick={() => onSelectView('repair')}
            >
              Review Repair Proposals →
            </button>
          </div>

          {/* Card 4: Architecture & Documentation */}
          <div className="shell-feature-card home-module-card">
            <span className="shell-feature-icon" aria-hidden="true">ℹ️</span>
            <h3 className="shell-feature-title">About &amp; Architecture</h3>
            <p className="shell-feature-desc">
              Learn about OmniSight's technical architecture, including the FastAPI orchestration layer,
              Playwright browser agent, Gemini VLM vision model, and PostgreSQL database.
            </p>
            <button
              type="button"
              className="btn btn-secondary btn-sm home-card-btn"
              onClick={() => onSelectView('about')}
            >
              Read System Overview →
            </button>
          </div>
        </div>
      </section>

      {/* 6. Recent Activity Section (Supported by Real API Data) */}
      <section className="card home-activity-card" aria-label="Recent Activity">
        <div className="card-header-with-actions">
          <div>
            <h2 className="card-title">Recent Activity</h2>
            <p className="card-description">
              Recent inspection runs recorded in PostgreSQL (<code>GET /api/v1/runs</code>).
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefreshRuns}
            disabled={isRunsLoading}
            title="Refresh recent activity"
          >
            {isRunsLoading ? 'Refreshing...' : '↻ Refresh Activity'}
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
            <p className="empty-state-text">Loading recent activity from backend...</p>
          </div>
        ) : runsList.length === 0 ? (
          /* Empty State */
          <div className="empty-state">
            <div className="empty-state-icon" aria-hidden="true">📋</div>
            <p className="empty-state-title">No Recent Activity Recorded</p>
            <p className="empty-state-text">
              No inspection runs found in the backend database. Select a demo state or enter a custom URL above
              and click <strong>Start Inspection</strong> to launch your first run.
            </p>
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
