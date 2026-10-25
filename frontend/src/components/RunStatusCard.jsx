import React, { useState } from 'react';

export default function RunStatusCard({
  run,
  onRefresh,
  isRefreshing,
  isAutoPolling,
  onToggleAutoPolling,
  onLookupRun,
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
              <button
                type="button"
                className={`btn btn-sm ${isAutoPolling ? 'btn-active-polling' : 'btn-secondary'}`}
                onClick={onToggleAutoPolling}
                disabled={isTerminalStatus}
                title={
                  isTerminalStatus
                    ? 'Polling stopped: Run has reached a terminal status.'
                    : isAutoPolling
                    ? 'Auto-refresh active every 4 seconds. Click to pause.'
                    : 'Click to enable automatic polling every 4 seconds.'
                }
              >
                {isAutoPolling ? (
                  <>
                    <span className="polling-pulse-dot"></span>
                    <span>Auto-Refresh: ON (4s)</span>
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
