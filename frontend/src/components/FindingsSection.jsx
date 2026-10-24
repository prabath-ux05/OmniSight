import React from 'react';

export default function FindingsSection({
  findings,
  isLoading,
  selectedFindingId,
  onSelectFinding,
  runId,
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
        return category || 'Unknown';
    }
  };

  return (
    <section className="card findings-section">
      <div className="card-header-with-actions">
        <div>
          <h2 className="card-title">Defect Findings &amp; Visual Analysis</h2>
          <p className="card-description">
            UI anomalies detected by multimodal screenshot and DOM inspection.
          </p>
        </div>
        {findings && (
          <span className="findings-count-badge">
            {findings.length} {findings.length === 1 ? 'Finding' : 'Findings'}
          </span>
        )}
      </div>

      {isLoading && (
        <div className="loading-container">
          <span className="spinner-md"></span>
          <p className="loading-text">Loading findings for run {runId}...</p>
        </div>
      )}

      {!isLoading && !runId && (
        <div className="empty-state">
          <p className="empty-state-text">
            No inspection run selected. Start an inspection to analyze UI defects.
          </p>
        </div>
      )}

      {!isLoading && runId && (!findings || findings.length === 0) && (
        <div className="empty-state empty-state-clean">
          <div className="clean-check-icon">✓</div>
          <h3 className="clean-title">No UI Defects Detected</h3>
          <p className="empty-state-text">
            All visual elements and layouts passed inspection for run <code>{runId}</code>.
          </p>
        </div>
      )}

      {!isLoading && findings && findings.length > 0 && (
        <div className="findings-list">
          {findings.map((item) => {
            const isSelected = selectedFindingId === item.finding_id;
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
                    {item.source === 'mock' && (
                      <span className="badge badge-source-mock" title="Generated mock finding for early testing">
                        MOCK DATA
                      </span>
                    )}
                  </div>
                  <span className="finding-confidence">
                    Confidence: {item.confidence ? `${Math.round(item.confidence * 100)}%` : 'N/A'}
                  </span>
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
