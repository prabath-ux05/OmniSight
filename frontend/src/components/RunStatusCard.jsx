import React from 'react';

export default function RunStatusCard({ run, onRefresh, isRefreshing }) {
  if (!run) {
    return (
      <section className="card run-status-section">
        <div className="card-header">
          <h2 className="card-title">Run Status</h2>
        </div>
        <div className="empty-state">
          <p className="empty-state-text">
            No active inspection run. Initiate an inspection above to view real-time execution status and metadata.
          </p>
        </div>
      </section>
    );
  }

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'completed':
        return 'badge-success';
      case 'failed':
      case 'error':
        return 'badge-danger';
      case 'capturing':
      case 'analyzing':
      case 'repairing':
        return 'badge-warning';
      case 'queued':
      default:
        return 'badge-info';
    }
  };

  const formattedDate = run.created_at
    ? new Date(run.created_at).toLocaleString()
    : 'Just now';

  return (
    <section className="card run-status-section">
      <div className="card-header-with-actions">
        <div>
          <h2 className="card-title">Run Status &amp; Execution Metadata</h2>
          <p className="card-description">Lifecycle details for the current inspection run.</p>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => onRefresh(run.run_id)}
          disabled={isRefreshing}
          title="Poll latest run status from backend"
        >
          {isRefreshing ? 'Refreshing...' : 'Refresh Status'}
        </button>
      </div>

      <div className="status-grid">
        <div className="status-item">
          <span className="status-label">Run ID</span>
          <span className="status-value status-mono">{run.run_id}</span>
        </div>
        <div className="status-item">
          <span className="status-label">Current State</span>
          <div>
            <span className={`badge ${getStatusBadgeClass(run.status)}`}>
              {run.status.toUpperCase()}
            </span>
          </div>
        </div>
        <div className="status-item">
          <span className="status-label">Target URL</span>
          <span className="status-value status-url" title={run.url}>
            <a href={run.url} target="_blank" rel="noopener noreferrer">
              {run.url}
            </a>
          </span>
        </div>
        <div className="status-item">
          <span className="status-label">Initiated At</span>
          <span className="status-value">{formattedDate}</span>
        </div>
      </div>

      {run.message && (
        <div className="status-message-banner">
          <span className="message-label">Backend Message:</span>
          <span className="message-text">{run.message}</span>
        </div>
      )}

      {run.error && (
        <div className="status-error-banner">
          <span className="error-label">Execution Failure:</span>
          <span className="error-text">{run.error}</span>
        </div>
      )}
    </section>
  );
}
