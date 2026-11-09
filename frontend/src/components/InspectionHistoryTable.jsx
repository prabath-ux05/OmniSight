import React, { useState, useEffect } from 'react';

/**
 * InspectionHistoryTable displays historical inspection runs retrieved from GET /api/v1/runs.
 * Allows users to browse past runs, inspect statuses, filter by URL/ID, and select runs for detailed inspection.
 */
export default function InspectionHistoryTable({
  runs,
  isLoading,
  error,
  onRefresh,
  onSelectRun,
  selectedRunId,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');

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

  const filteredRuns = (runs || []).filter((run) => {
    const matchesSearch =
      !searchTerm ||
      run.run_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      run.url?.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus =
      statusFilter === 'ALL' ||
      run.status?.toUpperCase() === statusFilter;

    return matchesSearch && matchesStatus;
  });

  return (
    <section className="card history-section">
      <div className="card-header-with-actions">
        <div>
          <h2 className="card-title">Inspection Run History</h2>
          <p className="card-description">
            Audit log of all inspection runs persisted in PostgreSQL (<code>GET /api/v1/runs</code>).
          </p>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onRefresh}
          disabled={isLoading}
          title="Refresh run history from backend"
        >
          {isLoading ? 'Refreshing...' : '↻ Refresh History'}
        </button>
      </div>

      {/* Filter / Search Bar */}
      <div className="history-toolbar">
        <div className="history-search-group">
          <input
            type="text"
            className="form-input form-input-sm"
            placeholder="Search by Run ID or Target URL..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="history-filter-group">
          <label htmlFor="status-filter-select" className="filter-label">Status:</label>
          <select
            id="status-filter-select"
            className="form-input form-input-sm filter-select"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">Completed</option>
            <option value="QUEUED">Queued</option>
            <option value="CAPTURING">Capturing</option>
            <option value="ANALYZING">Analyzing</option>
            <option value="FAILED">Failed</option>
            <option value="CANCELLED">Cancelled</option>
          </select>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="alert-box alert-error history-error">
          <span>Failed to load run history: {error}</span>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (!runs || runs.length === 0) ? (
        <div className="empty-state">
          <span className="spinner-sm"></span>
          <p className="empty-state-text">Loading historical inspection runs from PostgreSQL...</p>
        </div>
      ) : filteredRuns.length === 0 ? (
        /* Empty state */
        <div className="empty-state">
          <div className="empty-state-icon">📋</div>
          <p className="empty-state-title">No Historical Inspection Runs Found</p>
          <p className="empty-state-text">
            {searchTerm || statusFilter !== 'ALL'
              ? 'No runs match your current search or filter criteria. Try clearing filters.'
              : 'Start a new inspection using the form above to record your first run in PostgreSQL.'}
          </p>
        </div>
      ) : (
        /* Runs Table */
        <div className="table-responsive">
          <table className="history-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Target URL</th>
                <th>Status</th>
                <th>Created At</th>
                <th>Completed At</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((run) => {
                const isSelected = selectedRunId === run.run_id;
                return (
                  <tr
                    key={run.run_id}
                    className={`history-row ${isSelected ? 'history-row-selected' : ''}`}
                    onClick={() => onSelectRun(run)}
                  >
                    <td>
                      <code className="run-id-pill" title={run.run_id}>
                        {run.run_id.length > 18
                          ? `${run.run_id.substring(0, 16)}...`
                          : run.run_id}
                      </code>
                    </td>
                    <td>
                      <span className="history-url-cell" title={run.url}>
                        {run.url}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${getStatusBadgeClass(run.status)}`}>
                        {run.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="timestamp-cell">
                      {formatTimestamp(run.created_at)}
                    </td>
                    <td className="timestamp-cell">
                      {run.completed_at ? formatTimestamp(run.completed_at) : (
                        <span className="text-muted">In progress</span>
                      )}
                    </td>
                    <td>
                      <button
                        type="button"
                        className={`btn btn-xs ${isSelected ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectRun(run);
                        }}
                      >
                        {isSelected ? '✓ Selected' : 'Inspect'}
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
