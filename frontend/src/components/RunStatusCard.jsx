import React, { useState } from 'react';

export default function RunStatusCard({
  run,
  onRefresh,
  isRefreshing,
  isAutoPolling,
  onToggleAutoPolling,
  onLookupRun,
  onExecutePipeline,
  isExecuting,
}) {
  const [lookupId, setLookupId] = useState('');
  const [lookupError, setLookupError] = useState('');

  const handleLookupSubmit = (e) => {
    e.preventDefault();
    const cleanId = lookupId.trim();
    if (!cleanId) {
      setLookupError('Please enter a run ID to look up.');
      return;
    }
    setLookupError('');
    onLookupRun(cleanId);
  };

  const getStatusBadgeClass = (status) => {
    switch (status?.toLowerCase()) {
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
        return 'badge-info';
    }
  };

  const isTerminalStatus = run && ['completed', 'failed', 'cancelled'].includes(run.status);
  const isActiveRun = run && !isTerminalStatus;

  // Derive execution stage from backend status without inventing mock data
  const getStageState = (stageKey) => {
    if (!run) return 'pending';
    const s = run.status?.toLowerCase();
    if (s === 'failed' || s === 'cancelled') {
      if (stageKey === 'queued' && s === 'queued') return 'failed';
      if (stageKey === 'capturing' && (s === 'capturing' || s === 'failed')) return 'failed';
      if (stageKey === 'analyzing' && s === 'analyzing') return 'failed';
      return 'failed';
    }
    switch (stageKey) {
      case 'queued':
        return s === 'queued' ? 'active' : 'completed';
      case 'capturing':
        if (s === 'queued') return 'pending';
        if (s === 'capturing') return 'active';
        return 'completed';
      case 'analyzing':
        if (s === 'queued' || s === 'capturing') return 'pending';
        if (s === 'analyzing' || s === 'repair_pending' || s === 'repairing' || s === 'verifying') return 'active';
        return 'completed';
      case 'completed':
        return s === 'completed' ? 'completed' : 'pending';
      default:
        return 'pending';
    }
  };

  const calculateDuration = (startIso, endIso) => {
    if (!startIso || !endIso) return null;
    try {
      const ms = new Date(endIso).getTime() - new Date(startIso).getTime();
      if (isNaN(ms) || ms < 0) return null;
      return `${(ms / 1000).toFixed(1)}s`;
    } catch {
      return null;
    }
  };

  const duration = run ? calculateDuration(run.created_at, run.completed_at) : null;

  return (
    <section className="card run-status-section">
      <div className="card-header-with-actions">
        <div>
          <h2 className="card-title">Run Status &amp; Execution Metadata</h2>
          <p className="card-description">
            Live lifecycle details retrieved from <code>GET /api/v1/runs/{'{run_id}'}</code>.
          </p>
        </div>

        <div className="run-status-controls">
          {run && (
            <>
              {run.status === 'queued' && onExecutePipeline && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => onExecutePipeline(run.run_id)}
                  disabled={isExecuting || isRefreshing}
                  title="Trigger integrated Browser Agent capture and Vision Engine analysis"
                >
                  {isExecuting ? 'Executing Pipeline...' : '▶ Execute Pipeline'}
                </button>
              )}
              <button
                type="button"
                className={`btn btn-sm ${isAutoPolling ? 'btn-active-polling' : 'btn-secondary'}`}
                onClick={onToggleAutoPolling}
                disabled={isTerminalStatus}
                title={
                  isTerminalStatus
                    ? 'Polling stopped: Run has reached a terminal status.'
                    : isAutoPolling
                    ? 'Auto-refresh active every 2.5 seconds. Click to pause.'
                    : 'Click to enable automatic polling every 2.5 seconds.'
                }
              >
                {isAutoPolling ? (
                  <>
                    <span className="polling-pulse-dot"></span>
                    <span>Auto-Refresh: ON (2.5s)</span>
                  </>
                ) : (
                  <span>Auto-Refresh: OFF</span>
                )}
              </button>

              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onRefresh(run.run_id)}
                disabled={isRefreshing}
                title="Manually fetch latest status from backend"
              >
                {isRefreshing ? 'Refreshing...' : 'Refresh Status'}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Distinction: Active Run vs Completed/Historical Run */}
      {run && (
        <div className="run-mode-banner">
          <div className="run-mode-left">
            {isActiveRun ? (
              <span className="badge badge-active-run">
                <span className="polling-pulse-dot" aria-hidden="true"></span>
                ACTIVE RUN IN PROGRESS
              </span>
            ) : run.status === 'completed' ? (
              <span className="badge badge-completed-run">
                ✓ HISTORICAL AUDIT (COMPLETED)
              </span>
            ) : (
              <span className="badge badge-terminal-run">
                ✕ TERMINAL RUN ({run.status.toUpperCase()})
              </span>
            )}
            <span className="run-id-highlight"><code>{run.run_id}</code></span>
          </div>

          {duration && (
            <span className="run-duration-pill" title="Execution duration between created_at and completed_at">
              ⏱ Execution Time: {duration}
            </span>
          )}
        </div>
      )}

      {/* Pipeline Stages Progress Tracker (Derived strictly from real run.status) */}
      {run && (
        <div className="pipeline-tracker-box">
          <div className="pipeline-tracker-header">
            <span className="tracker-title">Inspection Pipeline Stages:</span>
            <span className="tracker-status-text">Status: <code>{run.status}</code></span>
          </div>
          <div className="pipeline-steps-row">
            <div className={`pipeline-step pipeline-step-${getStageState('queued')}`}>
              <div className="step-number">1</div>
              <div className="step-label">Queued</div>
            </div>
            <div className="step-connector"></div>
            <div className={`pipeline-step pipeline-step-${getStageState('capturing')}`}>
              <div className="step-number">2</div>
              <div className="step-label">Browser Capture</div>
            </div>
            <div className="step-connector"></div>
            <div className={`pipeline-step pipeline-step-${getStageState('analyzing')}`}>
              <div className="step-number">3</div>
              <div className="step-label">Vision Analysis</div>
            </div>
            <div className="step-connector"></div>
            <div className={`pipeline-step pipeline-step-${getStageState('completed')}`}>
              <div className="step-number">4</div>
              <div className="step-label">Complete</div>
            </div>
          </div>
        </div>
      )}

      {/* Quick Lookup Bar */}
      <form onSubmit={handleLookupSubmit} className="lookup-form">
        <label htmlFor="lookup-run-id" className="lookup-label">
          Look up Run by ID:
        </label>
        <div className="lookup-input-row">
          <input
            id="lookup-run-id"
            type="text"
            className="text-input text-input-sm status-mono"
            placeholder="e.g. run_a1b2c3d4 or run_unknown_test"
            value={lookupId}
            onChange={(e) => {
              setLookupId(e.target.value);
              if (lookupError) setLookupError('');
            }}
            disabled={isRefreshing}
          />
          <button
            type="submit"
            className="btn btn-secondary btn-sm"
            disabled={isRefreshing || !lookupId.trim()}
          >
            {isRefreshing ? 'Fetching...' : 'Fetch Run'}
          </button>
        </div>
        {lookupError && <p className="field-error-text">{lookupError}</p>}
      </form>

      {!run ? (
        <div className="empty-state">
          <p className="empty-state-text">
            No inspection run currently selected. Initiate a website inspection above, or enter an existing Run ID to check its real-time status.
          </p>
        </div>
      ) : (
        <>
          <div className="status-grid">
            <div className="status-item">
              <span className="status-label">Run Identifier</span>
              <span className="status-value status-mono">{run.run_id}</span>
            </div>

            <div className="status-item">
              <span className="status-label">Current Status</span>
              <div>
                <span className={`badge ${getStatusBadgeClass(run.status)}`}>
                  {run.status.toUpperCase()}
                </span>
              </div>
            </div>

            <div className="status-item">
              <span className="status-label">Target Website URL</span>
              <span className="status-value status-url" title={run.url}>
                <a href={run.url} target="_blank" rel="noopener noreferrer">
                  {run.url}
                </a>
              </span>
            </div>

            <div className="status-item">
              <span className="status-label">Created At (UTC)</span>
              <span className="status-value">
                {run.created_at ? new Date(run.created_at).toLocaleString() : 'N/A'}
              </span>
            </div>

            {run.completed_at && (
              <div className="status-item">
                <span className="status-label">Completed At (UTC)</span>
                <span className="status-value">
                  {new Date(run.completed_at).toLocaleString()}
                </span>
              </div>
            )}

            {duration && (
              <div className="status-item">
                <span className="status-label">Total Duration</span>
                <span className="status-value status-mono">{duration}</span>
              </div>
            )}
          </div>

          {/* Backend Message Banner */}
          {run.message && (
            <div className="status-message-banner">
              <span className="message-label">Backend Message:</span>
              <span className="message-text">{run.message}</span>
            </div>
          )}

          {/* Execution Failure Banner */}
          {(run.error || run.status === 'failed') && (
            <div className="status-error-banner" role="alert">
              <div className="status-error-icon">✕</div>
              <div>
                <strong className="error-label">Execution Failure Reported:</strong>
                <p className="error-text">
                  {run.error || 'The run encountered a failure during execution.'}
                </p>
              </div>
            </div>
          )}

          {/* Terminal state notification */}
          {isTerminalStatus && (
            <div className="terminal-status-notice">
              <span>Run has reached terminal state (<code>{run.status}</code>). Auto-refresh stopped.</span>
            </div>
          )}
        </>
      )}
    </section>
  );
}
