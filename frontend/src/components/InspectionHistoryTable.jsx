import React, { useState, useMemo } from 'react';

/**
 * InspectionHistoryTable displays historical inspection runs retrieved from GET /api/v1/runs.
 * Allows users to browse past runs, inspect statuses, filter by URL/ID/Status/Date, and select runs for detailed inspection.
 */
export default function InspectionHistoryTable({
  runs,
  isLoading,
  error,
  onRefresh,
  onSelectRun,
  selectedRunId,
  findingsMap = null,
  onLoadRunFindings = null,
  onInspectInStudio = null,
  onExportHistoryCsv = null,
  onExportHistoryPdf = null,
  onExportRunCsv = null,
  onExportRunPdf = null,
  isExportingCsv = false,
  isExportingPdf = false,
  exportingRunId = null,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [dateFilter, setDateFilter] = useState('ALL'); // 'ALL' | 'today' | '7days' | '30days' | 'custom'
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [sortBy, setSortBy] = useState('newest'); // 'newest' | 'oldest' | 'status'
  const [copiedId, setCopiedId] = useState(null);

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
        return 'badge-neutral';
    }
  };

  const isTerminalStatus = (status) => {
    return ['completed', 'failed', 'cancelled'].includes(status?.toLowerCase());
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

  const handleCopyRunId = (e, runId) => {
    e.stopPropagation();
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(runId).catch(() => {});
    }
    setCopiedId(runId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const isWithinDateRange = (isoString) => {
    if (!isoString) return false;
    if (dateFilter === 'ALL') return true;

    const date = new Date(isoString);
    if (isNaN(date.getTime())) return true;

    const now = new Date();

    if (dateFilter === 'today') {
      const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      return date >= todayStart;
    }
    if (dateFilter === '7days') {
      const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
      return date >= sevenDaysAgo;
    }
    if (dateFilter === '30days') {
      const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
      return date >= thirtyDaysAgo;
    }
    if (dateFilter === 'custom') {
      if (customStartDate) {
        const start = new Date(customStartDate);
        start.setHours(0, 0, 0, 0);
        if (date < start) return false;
      }
      if (customEndDate) {
        const end = new Date(customEndDate);
        end.setHours(23, 59, 59, 999);
        if (date > end) return false;
      }
      return true;
    }
    return true;
  };

  const filteredRuns = useMemo(() => {
    const list = (runs || []).filter((run) => {
      const matchesSearch =
        !searchTerm ||
        run.run_id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        run.url?.toLowerCase().includes(searchTerm.toLowerCase());

      const matchesStatus =
        statusFilter === 'ALL' ||
        run.status?.toUpperCase() === statusFilter.toUpperCase();

      const matchesDate = isWithinDateRange(run.created_at);

      return matchesSearch && matchesStatus && matchesDate;
    });

    return list.sort((a, b) => {
      if (sortBy === 'oldest') {
        return new Date(a.created_at || 0) - new Date(b.created_at || 0);
      }
      if (sortBy === 'status') {
        return (a.status || '').localeCompare(b.status || '');
      }
      // default: newest first
      return new Date(b.created_at || 0) - new Date(a.created_at || 0);
    });
  }, [runs, searchTerm, statusFilter, dateFilter, customStartDate, customEndDate, sortBy]);

  const hasActiveFilters =
    Boolean(searchTerm) ||
    statusFilter !== 'ALL' ||
    dateFilter !== 'ALL' ||
    Boolean(customStartDate) ||
    Boolean(customEndDate);

  const handleResetFilters = () => {
    setSearchTerm('');
    setStatusFilter('ALL');
    setDateFilter('ALL');
    setCustomStartDate('');
    setCustomEndDate('');
    setSortBy('newest');
  };

  const renderFindingSummary = (run) => {
    const runFindings = findingsMap ? findingsMap[run.run_id] : null;
    if (runFindings === undefined || runFindings === null) {
      return (
        <span
          className="text-muted text-sm findings-cell-action"
          title={onLoadRunFindings ? 'Click to load findings for this run' : 'Select run to inspect findings'}
          onClick={(e) => {
            if (onLoadRunFindings) {
              e.stopPropagation();
              onLoadRunFindings(run.run_id);
            }
          }}
        >
          {onLoadRunFindings ? 'Load' : '—'}
        </span>
      );
    }

    if (runFindings.length === 0) {
      return <span className="badge badge-success badge-xs">0 defects</span>;
    }

    const critical = runFindings.filter((f) => f.severity?.toLowerCase() === 'critical').length;
    const high = runFindings.filter((f) => f.severity?.toLowerCase() === 'high').length;
    const medium = runFindings.filter((f) => f.severity?.toLowerCase() === 'medium').length;
    const low = runFindings.filter((f) => f.severity?.toLowerCase() === 'low').length;

    return (
      <div className="findings-summary-cell" title={`${runFindings.length} defect finding(s) recorded`}>
        <span className="findings-total-pill">{runFindings.length}</span>
        <div className="severity-mini-pills">
          {critical > 0 && <span className="badge badge-critical badge-xs">{critical}C</span>}
          {high > 0 && <span className="badge badge-high badge-xs">{high}H</span>}
          {medium > 0 && <span className="badge badge-medium badge-xs">{medium}M</span>}
          {low > 0 && <span className="badge badge-low badge-xs">{low}L</span>}
        </div>
      </div>
    );
  };

  return (
    <section className="card history-section" aria-label="Inspection Run History Table">
      <div className="card-header-with-actions">
        <div>
          <h2 className="card-title">Inspection Run Audit Table</h2>
          <p className="card-description">
            Complete historical audit log retrieved from PostgreSQL (<code>GET /api/v1/runs</code>).
          </p>
        </div>
        <div className="history-header-actions">
          {onExportHistoryPdf && (
            <button
              type="button"
              className="export-action-btn export-action-btn-pdf"
              onClick={onExportHistoryPdf}
              disabled={isExportingPdf}
              title="Export complete inspection history summary as PDF"
            >
              {isExportingPdf ? '⏳ Generating…' : '📄 History PDF'}
            </button>
          )}
          {onExportHistoryCsv && (
            <button
              type="button"
              className="export-action-btn export-action-btn-csv"
              onClick={onExportHistoryCsv}
              disabled={isExportingCsv}
              title="Export complete inspection history as CSV"
            >
              {isExportingCsv ? '⏳ Exporting…' : '📊 History CSV'}
            </button>
          )}
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
      </div>

      {/* Enhanced Filter / Search Toolbar */}
      <div className="history-toolbar">
        {/* Search Input */}
        <div className="history-search-group">
          <input
            type="text"
            className="form-input form-input-sm"
            placeholder="Search by Run ID or Target URL..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        {/* Status Filter */}
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

        {/* Date Filter */}
        <div className="history-filter-group">
          <label htmlFor="date-filter-select" className="filter-label">Date:</label>
          <select
            id="date-filter-select"
            className="form-input form-input-sm filter-select"
            value={dateFilter}
            onChange={(e) => setDateFilter(e.target.value)}
          >
            <option value="ALL">All Time</option>
            <option value="today">Today</option>
            <option value="7days">Last 7 Days</option>
            <option value="30days">Last 30 Days</option>
            <option value="custom">Custom Range</option>
          </select>
        </div>

        {/* Sort Order */}
        <div className="history-filter-group">
          <label htmlFor="sort-by-select" className="filter-label">Sort:</label>
          <select
            id="sort-by-select"
            className="form-input form-input-sm filter-select-compact"
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
            <option value="status">Status</option>
          </select>
        </div>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <button
            type="button"
            className="btn btn-secondary btn-xs btn-reset-filters"
            onClick={handleResetFilters}
            title="Clear all active search and filter constraints"
          >
            Reset Filters
          </button>
        )}
      </div>

      {/* Custom Date Range Picker Row (conditional) */}
      {dateFilter === 'custom' && (
        <div className="history-custom-date-row">
          <div className="custom-date-input-group">
            <label htmlFor="custom-date-start" className="filter-label-inline">From:</label>
            <input
              id="custom-date-start"
              type="date"
              className="form-input form-input-sm"
              value={customStartDate}
              onChange={(e) => setCustomStartDate(e.target.value)}
            />
          </div>
          <div className="custom-date-input-group">
            <label htmlFor="custom-date-end" className="filter-label-inline">To:</label>
            <input
              id="custom-date-end"
              type="date"
              className="form-input form-input-sm"
              value={customEndDate}
              onChange={(e) => setCustomEndDate(e.target.value)}
            />
          </div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="alert-box alert-error history-error" role="alert">
          <span>Failed to load run history: {error}</span>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
          >
            ↻ Retry Connection
          </button>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (!runs || runs.length === 0) ? (
        <div className="empty-state">
          <span className="spinner-sm" aria-hidden="true"></span>
          <p className="empty-state-text">Loading historical inspection runs from PostgreSQL...</p>
        </div>
      ) : filteredRuns.length === 0 ? (
        /* Empty state */
        <div className="empty-state">
          <div className="empty-state-icon" aria-hidden="true">📋</div>
          <p className="empty-state-title">
            {hasActiveFilters
              ? 'No Runs Match Your Search or Filter Criteria'
              : 'No Historical Inspection Runs Found'}
          </p>
          <p className="empty-state-text">
            {hasActiveFilters
              ? 'No runs match the specified query, status, or date range. Try clearing your filters.'
              : 'Start a new inspection to record your first run in PostgreSQL.'}
          </p>
          {hasActiveFilters && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleResetFilters}
            >
              Clear All Filters
            </button>
          )}
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
                <th>Viewports</th>
                <th>Created At</th>
                <th>Duration</th>
                {findingsMap && <th>Findings</th>}
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredRuns.map((run) => {
                const isSelected = selectedRunId === run.run_id;
                const isTerminal = isTerminalStatus(run.status);
                const duration = calculateDuration(run.created_at, run.completed_at);

                return (
                  <tr
                    key={run.run_id}
                    className={`history-row ${isSelected ? 'history-row-selected' : ''}`}
                    onClick={() => onSelectRun(run)}
                  >
                    <td>
                      <div className="run-id-cell-group">
                        <code className="run-id-pill" title={run.run_id}>
                          {run.run_id.length > 18
                            ? `${run.run_id.substring(0, 16)}...`
                            : run.run_id}
                        </code>
                        <button
                          type="button"
                          className="btn-copy-sm"
                          onClick={(e) => handleCopyRunId(e, run.run_id)}
                          title="Copy Run ID"
                        >
                          {copiedId === run.run_id ? '✓' : '📋'}
                        </button>
                      </div>
                    </td>
                    <td>
                      <span className="history-url-cell" title={run.url}>
                        {run.url}
                      </span>
                    </td>
                    <td>
                      {!isTerminal ? (
                        <span className="badge badge-active-run badge-xs" title="Live in-flight run in progress">
                          <span className="polling-pulse-dot" aria-hidden="true"></span>
                          {run.status.toUpperCase()}
                        </span>
                      ) : (
                        <span className={`badge ${getStatusBadgeClass(run.status)}`}>
                          {run.status.toUpperCase()}
                        </span>
                      )}
                    </td>
                    <td>
                      {/* Viewport pills for this run */}
                      {(() => {
                        const vps = Array.isArray(run.viewports) && run.viewports.length > 0
                          ? run.viewports
                          : run.viewport ? [run.viewport] : [];
                        if (vps.length === 0) return <span className="text-muted" style={{ fontSize: '0.75rem' }}>—</span>;
                        const icons = { desktop: '🖥️', tablet: '📱', mobile: '📲' };
                        return (
                          <div style={{ display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                            {vps.map((vp) => (
                              <span
                                key={vp}
                                className={`run-viewport-pill run-viewport-pill-${vp.toLowerCase()}`}
                                title={`${vp} viewport`}
                              >
                                {icons[vp.toLowerCase()] || '🖥️'}
                              </span>
                            ))}
                          </div>
                        );
                      })()}
                    </td>
                    <td className="timestamp-cell">
                      {formatTimestamp(run.created_at)}
                    </td>
                    <td className="timestamp-cell">
                      {duration ? (
                        <span className="duration-text">{duration}</span>
                      ) : isTerminal ? (
                        <span className="text-muted">—</span>
                      ) : (
                        <span className="text-muted" title="Run in progress">Running...</span>
                      )}
                    </td>
                    {findingsMap && (
                      <td className="findings-cell">
                        {renderFindingSummary(run)}
                      </td>
                    )}
                    <td>
                      <div className="history-row-actions">
                        <button
                          type="button"
                          className={`btn btn-xs ${isSelected ? 'btn-primary' : 'btn-secondary'}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectRun(run);
                          }}
                          title={`Select run ${run.run_id} for audit inspection`}
                        >
                          {isSelected ? '✓ Selected' : 'Inspect'}
                        </button>
                        {onInspectInStudio && (
                          <button
                            type="button"
                            className="btn btn-secondary btn-xs btn-open-studio"
                            onClick={(e) => {
                              e.stopPropagation();
                              onInspectInStudio(run);
                            }}
                            title="Open this run in the Live Inspection Studio"
                          >
                            Studio →
                          </button>
                        )}
                        {onExportRunPdf && (
                          <button
                            type="button"
                            className="btn btn-secondary btn-xs btn-export-row"
                            onClick={(e) => {
                              e.stopPropagation();
                              onExportRunPdf(run.run_id);
                            }}
                            disabled={exportingRunId === run.run_id}
                            title={`Download PDF report for run ${run.run_id}`}
                          >
                            {exportingRunId === run.run_id ? '...' : '📄 PDF'}
                          </button>
                        )}
                        {onExportRunCsv && (
                          <button
                            type="button"
                            className="btn btn-secondary btn-xs btn-export-row"
                            onClick={(e) => {
                              e.stopPropagation();
                              onExportRunCsv(run.run_id);
                            }}
                            disabled={exportingRunId === run.run_id}
                            title={`Download CSV for run ${run.run_id}`}
                          >
                            {exportingRunId === run.run_id ? '...' : '📊 CSV'}
                          </button>
                        )}
                      </div>
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
