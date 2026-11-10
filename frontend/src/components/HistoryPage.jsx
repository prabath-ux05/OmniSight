import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import InspectionHistoryTable from './InspectionHistoryTable';
import { fetchRunFindings } from '../services/api';

/**
 * HistoryPage renders the dedicated, polished OmniSight Run History & Audit view.
 *
 * Requirements met:
 * 1. Dedicated layout conforming to shared design system and application shell.
 * 2. Previous inspection runs displayed using actual backend data (GET /api/v1/runs).
 * 3. Shows Run ID, URL, Created At, Completed At, Duration, Status, Finding count, and Severity summary where supported.
 * 4. Useful search and filtering by URL, ID, status, and date range.
 * 5. In-place inspection of selected historical run findings, and navigation to Live Studio for full evidence.
 * 6. Clear visual distinction between historical/completed runs and currently active inspections.
 * 7. Comprehensive loading, empty, error, and retry states.
 * 8. Responsive and consistent with light, dark, and system themes.
 */
export default function HistoryPage({
  runs = [],
  isLoading = false,
  error = '',
  onRefresh = () => {},
  onSelectRun = () => {},
  selectedRunId = null,
  currentRun = null,
  findings = null,
  isFindingsLoading = false,
  onSelectView = () => {},
  includeMockFindings = false,
}) {
  const [selectedHistoricalRun, setSelectedHistoricalRun] = useState(null);
  const [findingsCache, setFindingsCache] = useState({});
  const [findingsErrors, setFindingsErrors] = useState({});
  const [isLoadingRunFindings, setIsLoadingRunFindings] = useState(false);
  const [copiedSelector, setCopiedSelector] = useState(null);

  const copyTimeoutRef = useRef(null);
  const pendingRequestsRef = useRef(new Set());
  const activeRequestedRunIdRef = useRef(null);

  // Clean up any pending copy selector timeout on unmount
  useEffect(() => {
    return () => {
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current);
      }
    };
  }, []);

  // Synchronize selected run from props or runs list defensively
  useEffect(() => {
    if (!Array.isArray(runs) || runs.length === 0) return;

    if (selectedRunId) {
      const matched = runs.find((r) => r.run_id === selectedRunId);
      if (matched) {
        setSelectedHistoricalRun(matched);
        return;
      }
    }

    setSelectedHistoricalRun((prev) => {
      if (!prev) return runs[0];
      const updated = runs.find((r) => r.run_id === prev.run_id);
      return updated || runs[0];
    });
  }, [selectedRunId, runs]);

  // Synchronize findings for currentRun when supplied from App
  useEffect(() => {
    if (currentRun?.run_id && Array.isArray(findings)) {
      setFindingsCache((prev) => ({
        ...prev,
        [currentRun.run_id]: findings,
      }));
    }
  }, [currentRun?.run_id, findings]);

  // Fetch real findings for a run on demand with defensive error handling & conflict prevention
  const loadFindingsForRun = useCallback(async (runId) => {
    if (!runId || findingsCache[runId] || pendingRequestsRef.current.has(runId)) return;

    pendingRequestsRef.current.add(runId);
    activeRequestedRunIdRef.current = runId;
    setIsLoadingRunFindings(true);
    setFindingsErrors((prev) => {
      if (!prev[runId]) return prev;
      const copy = { ...prev };
      delete copy[runId];
      return copy;
    });

    try {
      const result = await fetchRunFindings(runId, includeMockFindings);
      if (result.ok && Array.isArray(result.data)) {
        setFindingsCache((prev) => ({
          ...prev,
          [runId]: result.data,
        }));
      } else {
        setFindingsErrors((prev) => ({
          ...prev,
          [runId]: result.error || `Failed to retrieve defect findings for run '${runId}'.`,
        }));
      }
    } catch (err) {
      setFindingsErrors((prev) => ({
        ...prev,
        [runId]: err?.message || `Failed to retrieve defect findings for run '${runId}'.`,
      }));
    } finally {
      pendingRequestsRef.current.delete(runId);
      if (activeRequestedRunIdRef.current === runId) {
        setIsLoadingRunFindings(false);
      }
    }
  }, [findingsCache, includeMockFindings]);

  // Handle row selection on History page (read-only; never triggers execution)
  const handleSelectHistoricalRun = (run) => {
    setSelectedHistoricalRun(run);
    if (!findingsCache[run.run_id]) {
      loadFindingsForRun(run.run_id);
    }
  };

  // Open run directly in Live Inspection Studio
  const handleInspectInStudio = (run) => {
    onSelectRun(run);
    onSelectView('inspection');
  };

  // Load findings for initially selected run if not cached
  useEffect(() => {
    if (selectedHistoricalRun?.run_id && !findingsCache[selectedHistoricalRun.run_id]) {
      loadFindingsForRun(selectedHistoricalRun.run_id);
    }
  }, [selectedHistoricalRun?.run_id, findingsCache, loadFindingsForRun]);

  const handleCopySelector = (selector) => {
    if (!selector) return;
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(selector).catch(() => {});
    }
    setCopiedSelector(selector);
    if (copyTimeoutRef.current) {
      clearTimeout(copyTimeoutRef.current);
    }
    copyTimeoutRef.current = setTimeout(() => {
      setCopiedSelector(null);
      copyTimeoutRef.current = null;
    }, 2000);
  };

  // Real overview metrics calculated strictly from actual backend runs
  const stats = useMemo(() => {
    const total = runs.length;
    const completed = runs.filter((r) => {
      const s = typeof r.status === 'string' ? r.status.trim().toLowerCase() : '';
      return s === 'completed';
    }).length;
    const inProgress = runs.filter((r) => {
      const s = typeof r.status === 'string' ? r.status.trim().toLowerCase() : '';
      return ['queued', 'capturing', 'analyzing', 'repair_pending', 'repairing', 'verifying'].includes(s);
    }).length;
    const failed = runs.filter((r) => {
      const s = typeof r.status === 'string' ? r.status.trim().toLowerCase() : '';
      return ['failed', 'cancelled', 'error'].includes(s);
    }).length;
    return { total, completed, inProgress, failed };
  }, [runs]);

  // Calculate duration between created_at and completed_at
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

  const getSeverityBadgeClass = (severity) => {
    switch (severity?.toLowerCase()) {
      case 'critical':
        return 'badge-critical';
      case 'high':
        return 'badge-high';
      case 'medium':
        return 'badge-medium';
      case 'low':
      default:
        return 'badge-low';
    }
  };

  const getCategoryLabel = (category) => {
    switch (category) {
      case 'layout_overflow':
        return 'Layout Overflow';
      case 'missing_visible_element':
        return 'Missing Element';
      case 'broken_image':
        return 'Broken Image';
      default:
        return category || 'Unknown';
    }
  };

  // Selected run finding breakdown
  const selectedRunFindings = selectedHistoricalRun ? findingsCache[selectedHistoricalRun.run_id] : null;
  const selectedRunError = selectedHistoricalRun ? findingsErrors[selectedHistoricalRun.run_id] : null;
  const isSelectedLoading = Boolean(
    selectedHistoricalRun &&
    isLoadingRunFindings &&
    activeRequestedRunIdRef.current === selectedHistoricalRun.run_id
  );

  const selectedStatus = typeof selectedHistoricalRun?.status === 'string'
    ? selectedHistoricalRun.status.trim().toLowerCase()
    : '';
  const isSelectedTerminal = ['completed', 'failed', 'cancelled'].includes(selectedStatus);
  const isSelectedActive = Boolean(selectedHistoricalRun && !isSelectedTerminal && selectedStatus);

  const selectedDuration = selectedHistoricalRun
    ? calculateDuration(selectedHistoricalRun.created_at, selectedHistoricalRun.completed_at)
    : null;

  return (
    <div className="history-page-container">
      {/* 1. History Page Hero Banner */}
      <section className="shell-hero-card history-hero-banner" aria-label="History Page Header">
        <div className="history-hero-header-row">
          <div className="history-hero-titles">
            <span className="shell-hero-badge">
              <span className="status-dot status-dot-online" aria-hidden="true"></span>
              OmniSight Audit &amp; History
            </span>
            <h1 className="shell-hero-title">Inspection Run History &amp; Audit Log</h1>
            <p className="shell-hero-desc">
              Audit past web inspections persisted in PostgreSQL. Filter across target URLs,
              lifecycle statuses, and creation dates, and inspect visual defect findings and evidence.
            </p>
          </div>

          <div className="history-hero-actions">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => onSelectView('inspection')}
            >
              🔍 Open Live Studio →
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                if (selectedHistoricalRun) onSelectRun(selectedHistoricalRun);
                onSelectView('repair');
              }}
            >
              🛡️ Repair Workflow →
            </button>
          </div>
        </div>

        {/* Real Overview Metric Tiles (strictly actual backend data) */}
        <div className="history-stats-grid">
          <div className="history-stat-card">
            <span className="history-stat-label">Total Audited Runs</span>
            <span className="history-stat-val">{isLoading ? '...' : stats.total}</span>
            <span className="history-stat-sub">Persisted in PostgreSQL</span>
          </div>

          <div className="history-stat-card">
            <span className="history-stat-label">Completed Inspections</span>
            <span className="history-stat-val" style={{ color: '#10b981' }}>
              {isLoading ? '...' : stats.completed}
            </span>
            <span className="history-stat-sub">Terminal verified</span>
          </div>

          <div className="history-stat-card">
            <span className="history-stat-label">In-Flight Runs</span>
            <span className="history-stat-val" style={{ color: '#3b82f6' }}>
              {isLoading ? '...' : stats.inProgress}
            </span>
            <span className="history-stat-sub">Live pipeline active</span>
          </div>

          <div className="history-stat-card">
            <span className="history-stat-label">Failed / Cancelled</span>
            <span className="history-stat-val" style={{ color: stats.failed > 0 ? '#ef4444' : 'var(--text-dim)' }}>
              {isLoading ? '...' : stats.failed}
            </span>
            <span className="history-stat-sub">Execution anomalies</span>
          </div>
        </div>
      </section>

      {/* 2. Active In-Flight Run Notification (if a run is actively executing) */}
      {currentRun && (() => {
        const s = typeof currentRun.status === 'string' ? currentRun.status.trim().toLowerCase() : '';
        const isCurrentActive = !['completed', 'failed', 'cancelled'].includes(s) && s;
        if (!isCurrentActive) return null;
        return (
          <section className="card history-active-run-alert" aria-label="Active Run Notification">
            <div className="active-run-alert-content">
              <div className="active-run-alert-info">
                <span className="badge badge-active-run">
                  <span className="polling-pulse-dot" aria-hidden="true"></span>
                  LIVE IN-FLIGHT INSPECTION
                </span>
                <h3 className="active-run-alert-title">
                  Run <code>{currentRun.run_id ? String(currentRun.run_id) : '—'}</code> is currently active
                </h3>
                <p className="active-run-alert-desc">
                  Target: <code>{currentRun.url || '—'}</code> &bull; Status: <strong>{typeof currentRun.status === 'string' && currentRun.status.trim() ? currentRun.status.trim().toUpperCase() : 'ACTIVE'}</strong> &bull; Real-time auto-polling is active.
                </p>
              </div>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => handleInspectInStudio(currentRun)}
              >
                Open Live Studio →
              </button>
            </div>
          </section>
        );
      })()}

      {/* 3. Reused InspectionHistoryTable Component */}
      <InspectionHistoryTable
        runs={runs}
        isLoading={isLoading}
        error={error}
        onRefresh={onRefresh}
        onSelectRun={handleSelectHistoricalRun}
        selectedRunId={selectedHistoricalRun?.run_id || selectedRunId}
        findingsMap={findingsCache}
        onLoadRunFindings={loadFindingsForRun}
        onInspectInStudio={handleInspectInStudio}
      />

      {/* 4. Selected Historical Run Audit Inspector Panel */}
      {selectedHistoricalRun && (
        <section className="card history-run-inspector-card" aria-label="Selected Run Audit Details">
          <div className="card-header-with-actions">
            <div>
              <div className="inspector-badge-row">
                {isSelectedActive ? (
                  <span className="badge badge-active-run">
                    <span className="polling-pulse-dot" aria-hidden="true"></span>
                    ACTIVE RUN ({typeof selectedHistoricalRun.status === 'string' && selectedHistoricalRun.status.trim() ? selectedHistoricalRun.status.trim().toUpperCase() : 'UNKNOWN'})
                  </span>
                ) : selectedStatus === 'completed' ? (
                  <span className="badge badge-completed-run">
                    ✓ AUDITED RUN (COMPLETED)
                  </span>
                ) : (
                  <span className="badge badge-terminal-run">
                    ✕ TERMINAL RUN ({typeof selectedHistoricalRun.status === 'string' && selectedHistoricalRun.status.trim() ? selectedHistoricalRun.status.trim().toUpperCase() : 'UNKNOWN'})
                  </span>
                )}
                <span className="inspector-id-pill">
                  <code>{selectedHistoricalRun.run_id ? String(selectedHistoricalRun.run_id) : '—'}</code>
                </span>
              </div>
              <h2 className="card-title inspector-title">
                Audit Details: {selectedHistoricalRun.run_id ? String(selectedHistoricalRun.run_id) : '—'}
              </h2>
            </div>

            <div className="inspector-header-actions">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => handleInspectInStudio(selectedHistoricalRun)}
                title="Open this run in the Live Inspection Studio to view screenshots and DOM snapshots"
              >
                Inspect in Studio →
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  onSelectRun(selectedHistoricalRun);
                  onSelectView('repair');
                }}
                title="Open repair proposals review for this run"
              >
                Repair Workflow →
              </button>
            </div>
          </div>

          {/* Details Meta Grid */}
          <div className="inspector-meta-grid">
            <div className="meta-item">
              <span className="meta-label">Target Website URL</span>
              <span className="meta-value meta-url" title={selectedHistoricalRun.url}>
                <a href={selectedHistoricalRun.url} target="_blank" rel="noopener noreferrer">
                  {selectedHistoricalRun.url} ↗
                </a>
              </span>
            </div>

            <div className="meta-item">
              <span className="meta-label">Created At (UTC)</span>
              <span className="meta-value">{formatTimestamp(selectedHistoricalRun.created_at)}</span>
            </div>

            <div className="meta-item">
              <span className="meta-label">Completed At (UTC)</span>
              <span className="meta-value">
                {selectedHistoricalRun.completed_at
                  ? formatTimestamp(selectedHistoricalRun.completed_at)
                  : (isSelectedActive ? 'In progress' : '—')}
              </span>
            </div>

            <div className="meta-item">
              <span className="meta-label">Execution Duration</span>
              <span className="meta-value">
                {selectedDuration ? <code>{selectedDuration}</code> : (isSelectedActive ? 'Running...' : '—')}
              </span>
            </div>

            <div className="meta-item">
              <span className="meta-label">Finding Count</span>
              <span className="meta-value">
                {isSelectedLoading ? (
                  <span className="text-muted">Loading findings...</span>
                ) : selectedRunError ? (
                  <span style={{ color: '#ef4444' }}>Query error</span>
                ) : selectedRunFindings ? (
                  <strong>{selectedRunFindings.length} defect(s) recorded</strong>
                ) : (
                  <button
                    type="button"
                    className="btn-link"
                    onClick={() => loadFindingsForRun(selectedHistoricalRun.run_id)}
                  >
                    Load Findings
                  </button>
                )}
              </span>
            </div>

            <div className="meta-item">
              <span className="meta-label">Severity Summary</span>
              <div className="meta-value">
                {selectedRunFindings && selectedRunFindings.length > 0 ? (
                  <div className="inspector-severity-pills">
                    {(() => {
                      const crit = selectedRunFindings.filter((f) => f.severity?.toLowerCase() === 'critical').length;
                      const high = selectedRunFindings.filter((f) => f.severity?.toLowerCase() === 'high').length;
                      const med = selectedRunFindings.filter((f) => f.severity?.toLowerCase() === 'medium').length;
                      const low = selectedRunFindings.filter((f) => f.severity?.toLowerCase() === 'low').length;
                      return (
                        <>
                          {crit > 0 && <span className="badge badge-critical">{crit} Critical</span>}
                          {high > 0 && <span className="badge badge-high">{high} High</span>}
                          {med > 0 && <span className="badge badge-medium">{med} Medium</span>}
                          {low > 0 && <span className="badge badge-low">{low} Low</span>}
                        </>
                      );
                    })()}
                  </div>
                ) : selectedRunFindings && selectedRunFindings.length === 0 ? (
                  <span className="badge badge-success">✓ Clean Run (0 defects)</span>
                ) : (
                  <span className="text-muted">—</span>
                )}
              </div>
            </div>
          </div>

          {/* Failure message if run failed */}
          {selectedHistoricalRun.error && (
            <div className="alert-box alert-error inspector-error-box" role="alert">
              <strong>Execution Failure Reported:</strong>
              <p className="inspector-error-text">{selectedHistoricalRun.error}</p>
            </div>
          )}

          {/* Findings List Preview for Selected Run */}
          <div className="inspector-findings-container">
            <h3 className="inspector-section-heading">
              Recorded Findings ({selectedRunFindings ? selectedRunFindings.length : (selectedRunError ? 'Error' : '...')})
            </h3>

            {isSelectedLoading ? (
              <div className="empty-state">
                <span className="spinner-sm" aria-hidden="true"></span>
                <p className="empty-state-text">Fetching recorded defect findings for run {selectedHistoricalRun.run_id}...</p>
              </div>
            ) : selectedRunError ? (
              <div className="alert-box alert-error" role="alert" style={{ margin: '1rem 0' }}>
                <p style={{ margin: '0 0 0.5rem 0' }}>
                  <strong>Failed to retrieve findings:</strong> {selectedRunError}
                </p>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => loadFindingsForRun(selectedHistoricalRun.run_id)}
                >
                  ↻ Retry Loading Findings
                </button>
              </div>
            ) : selectedRunFindings && selectedRunFindings.length > 0 ? (
              <div className="inspector-findings-list">
                {selectedRunFindings.map((finding) => (
                  <div key={finding.finding_id} className="inspector-finding-item">
                    <div className="inspector-finding-header">
                      <div className="inspector-finding-badges">
                        <span className={`badge ${getSeverityBadgeClass(finding.severity)}`}>
                          {finding.severity?.toUpperCase()}
                        </span>
                        <span className="badge badge-category">
                          {getCategoryLabel(finding.category)}
                        </span>
                        {typeof finding.confidence === 'number' && (
                          <span className="finding-confidence">
                            Confidence: {Math.round(finding.confidence * 100)}%
                          </span>
                        )}
                      </div>
                      <span className="finding-id-tag">ID: {finding.finding_id}</span>
                    </div>

                    <p className="inspector-finding-desc">{finding.description}</p>

                    {finding.selector && (
                      <div className="inspector-finding-selector-row">
                        <span className="selector-label">DOM Selector:</span>
                        <code className="finding-selector">{finding.selector}</code>
                        <button
                          type="button"
                          className="btn btn-secondary btn-xs btn-copy-inline"
                          onClick={() => handleCopySelector(finding.selector)}
                          title="Copy selector"
                        >
                          {copiedSelector === finding.selector ? '✓ Copied' : 'Copy'}
                        </button>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : selectedRunFindings && selectedRunFindings.length === 0 ? (
              <div className="empty-state empty-state-clean">
                <div className="clean-check-icon">✓</div>
                <h4 className="clean-title">Zero Defects Detected</h4>
                <p className="empty-state-text">
                  This inspection run completed cleanly with no visual regressions or broken DOM elements.
                </p>
              </div>
            ) : (
              <div className="empty-state">
                <p className="empty-state-text">
                  Click <strong>Load Findings</strong> above to inspect defect details for this run.
                </p>
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
