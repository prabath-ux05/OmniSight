import React from 'react';

export default function FindingsSection({
  findings,
  isLoading,
  selectedFindingId,
  onSelectFinding,
  runId,
  includeMock,
  onToggleMockFindings,
  onRefreshFindings,
  findingsError,
}) {
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
        return category || 'Unknown Category';
    }
  };

  const isArray = Array.isArray(findings);
  const count = isArray ? findings.length : 0;

  return (
    <section className="card findings-section">
      <div className="card-header-with-actions">
        <div>
          <h2 className="card-title">Defect Findings &amp; Visual Analysis</h2>
          <p className="card-description">
            Retrieved from <code>GET /api/v1/runs/{'{run_id}'}/findings</code>.
          </p>
        </div>

        {runId && (
          <div className="findings-header-actions">
            <button
              type="button"
              className={`btn btn-sm ${includeMock ? 'btn-active-mock' : 'btn-secondary'}`}
              onClick={onToggleMockFindings}
              title={
                includeMock
                  ? 'Switch to clean inspection results (empty list)'
                  : 'Load mock defect findings (?include_mock=true) for development testing'
              }
            >
              {includeMock ? 'Mode: Mock Findings' : 'Mode: Clean Run'}
            </button>

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onRefreshFindings}
              disabled={isLoading}
              title="Refresh findings from backend"
            >
              {isLoading ? 'Loading...' : 'Refresh'}
            </button>

            <span className="findings-count-badge">
              {count} {count === 1 ? 'Finding' : 'Findings'}
            </span>
          </div>
        )}
      </div>

      {/* Loading Indicator */}
      {isLoading && (
        <div className="loading-container">
          <span className="spinner-md"></span>
          <p className="loading-text">Fetching defect findings for run {runId}...</p>
        </div>
      )}

      {/* Request or Malformed Response Error */}
      {!isLoading && findingsError && (
        <div className="alert alert-error" role="alert">
          <div className="alert-content">
            <span className="alert-message">{findingsError}</span>
          </div>
        </div>
      )}

      {/* No Run Selected */}
      {!isLoading && !findingsError && !runId && (
        <div className="empty-state">
          <p className="empty-state-text">
            No inspection run selected. Start an inspection or look up a Run ID to view detected UI defects.
          </p>
        </div>
      )}

      {/* Clean Run: Zero Findings */}
      {!isLoading && !findingsError && runId && isArray && count === 0 && (
        <div className="empty-state empty-state-clean">
          <div className="clean-check-icon">✓</div>
          <h3 className="clean-title">No UI Defects Detected</h3>
          <p className="empty-state-text">
            All visual elements and layouts passed inspection for run <code>{runId}</code>.
          </p>
          <div className="test-hint-box">
            <span className="test-hint-label">Testing Tip:</span>
            <span className="test-hint-text">
              To test the findings viewer layout with simulated defects, click the <strong>Mode: Clean Run</strong> button above to toggle mock findings.
            </span>
          </div>
        </div>
      )}

      {/* Non-empty Findings List */}
      {!isLoading && !findingsError && isArray && count > 0 && (
        <div className="findings-list">
          {findings.map((item) => {
            const isSelected = selectedFindingId === item.finding_id;
            const hasConfidence = typeof item.confidence === 'number';
            const isMock = item.source === 'mock' || (item.description && item.description.includes('[MOCK]'));

            return (
              <div
                key={item.finding_id}
                className={`finding-card ${isSelected ? 'finding-card-selected' : ''}`}
                onClick={() => onSelectFinding(item)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    onSelectFinding(item);
                  }
                }}
              >
                <div className="finding-header">
                  <div className="finding-badges">
                    <span className={`badge ${getSeverityBadgeClass(item.severity)}`}>
                      {item.severity ? item.severity.toUpperCase() : 'UNKNOWN'}
                    </span>
                    <span className="badge badge-category">
                      {getCategoryLabel(item.category)}
                    </span>
                    {isMock && (
                      <span
                        className="badge badge-source-mock"
                        title="Simulated test finding — not real model output"
                      >
                        [MOCK DATA]
                      </span>
                    )}
                  </div>

                  {hasConfidence && (
                    <span className="finding-confidence">
                      Confidence: {Math.round(item.confidence * 100)}%
                    </span>
                  )}
                </div>

                <div className="finding-body">
                  <p className="finding-description">{item.description}</p>
                  {item.selector && (
                    <div className="finding-selector-container">
                      <span className="selector-label">DOM Selector:</span>
                      <code className="finding-selector">{item.selector}</code>
                    </div>
                  )}
                </div>

                <div className="finding-footer">
                  <span className="finding-id-tag">ID: {item.finding_id}</span>
                  <span className="finding-view-evidence-hint">
                    {isSelected ? 'Viewing Evidence' : 'Click to inspect evidence →'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
