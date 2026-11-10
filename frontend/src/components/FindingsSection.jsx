import React, { useState, useMemo } from 'react';

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
  repairs = {},
  onSuggestRepair,
  repairingFindingId,
  onNavigateToRepair,
}) {
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [categoryFilter, setCategoryFilter] = useState('ALL');
  const [groupBy, setGroupBy] = useState('none'); // 'none' | 'category' | 'severity'

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

  // Extract available categories dynamically from existing findings
  const availableCategories = useMemo(() => {
    if (!isArray) return [];
    return Array.from(new Set(findings.map((f) => f.category).filter(Boolean)));
  }, [findings, isArray]);

  // Count findings by severity for badge indicators
  const severityCounts = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    if (!isArray) return counts;
    findings.forEach((f) => {
      const s = f.severity?.toLowerCase();
      if (counts[s] !== undefined) counts[s]++;
    });
    return counts;
  }, [findings, isArray]);

  // Filter findings by active category and severity filters
  const filteredFindings = useMemo(() => {
    if (!isArray) return [];
    return findings.filter((item) => {
      const matchSeverity =
        severityFilter === 'ALL' || item.severity?.toLowerCase() === severityFilter.toLowerCase();
      const matchCategory =
        categoryFilter === 'ALL' || item.category === categoryFilter;
      return matchSeverity && matchCategory;
    });
  }, [findings, isArray, severityFilter, categoryFilter]);

  // Group filtered findings when groupBy is active
  const groupedFindings = useMemo(() => {
    if (groupBy === 'none') return null;
    const groups = {};
    filteredFindings.forEach((item) => {
      const key = groupBy === 'category' ? getCategoryLabel(item.category) : (item.severity?.toUpperCase() || 'UNKNOWN');
      if (!groups[key]) groups[key] = [];
      groups[key].push(item);
    });
    return groups;
  }, [filteredFindings, groupBy]);

  const renderFindingCard = (item) => {
    const isSelected = selectedFindingId === item.finding_id;
    const hasConfidence = typeof item.confidence === 'number';
    const isMock = item.source === 'mock' || (item.description && item.description.includes('[MOCK]'));

    const isEligibleForRepair = item.category === 'missing_visible_element';
    const findingRepair = repairs ? repairs[item.finding_id] : null;
    const isRepairingThis = repairingFindingId === item.finding_id;

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
            {isEligibleForRepair && (
              findingRepair?.repaired ? (
                <span className="badge badge-repair-success" title="Verified alternative locator found in DOM">
                  ✓ Healed Locator
                </span>
              ) : findingRepair && !findingRepair.repaired ? (
                <span className="badge badge-repair-failed" title="No unique candidate found in DOM">
                  ⚠️ Checked
                </span>
              ) : (
                <span className="badge badge-repair-eligible" title="Eligible for Autonomous Locator Repair">
                  ⚡ Healable
                </span>
              )
            )}
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
          <div className="finding-footer-actions">
            {isEligibleForRepair && onSuggestRepair && (
              <button
                type="button"
                className="btn btn-repair-action btn-xs"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectFinding(item);
                  onSuggestRepair(item.finding_id);
                }}
                disabled={isRepairingThis}
                title="Suggest and validate repair candidates against captured DOM"
              >
                {isRepairingThis ? 'Repairing...' : (findingRepair ? 'Re-suggest Repair' : 'Suggest Repair')}
              </button>
            )}

            {onNavigateToRepair && (
              <button
                type="button"
                className="btn btn-secondary btn-xs btn-nav-repair"
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectFinding(item);
                  onNavigateToRepair(item);
                }}
                title="Navigate directly to Repair Workflow for this finding"
              >
                Repair in Workflow →
              </button>
            )}

            <span className="finding-view-evidence-hint">
              {isSelected ? 'Viewing Evidence' : 'View Details →'}
            </span>
          </div>
        </div>
      </div>
    );
  };

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

      {/* Findings Content Area */}
      {!isLoading && !findingsError && isArray && count > 0 && (
        <>
          {/* Interactive Severity & Category Filter Toolbar */}
          <div className="findings-filter-toolbar" aria-label="Findings Filters">
            <div className="filter-row">
              <div className="filter-group">
                <span className="filter-label">Severity:</span>
                <div className="filter-pills-row">
                  <button
                    type="button"
                    className={`btn-filter-pill ${severityFilter === 'ALL' ? 'active' : ''}`}
                    onClick={() => setSeverityFilter('ALL')}
                  >
                    All ({count})
                  </button>
                  {severityCounts.critical > 0 && (
                    <button
                      type="button"
                      className={`btn-filter-pill pill-critical ${severityFilter === 'critical' ? 'active' : ''}`}
                      onClick={() => setSeverityFilter(severityFilter === 'critical' ? 'ALL' : 'critical')}
                    >
                      Critical ({severityCounts.critical})
                    </button>
                  )}
                  {severityCounts.high > 0 && (
                    <button
                      type="button"
                      className={`btn-filter-pill pill-high ${severityFilter === 'high' ? 'active' : ''}`}
                      onClick={() => setSeverityFilter(severityFilter === 'high' ? 'ALL' : 'high')}
                    >
                      High ({severityCounts.high})
                    </button>
                  )}
                  {severityCounts.medium > 0 && (
                    <button
                      type="button"
                      className={`btn-filter-pill pill-medium ${severityFilter === 'medium' ? 'active' : ''}`}
                      onClick={() => setSeverityFilter(severityFilter === 'medium' ? 'ALL' : 'medium')}
                    >
                      Medium ({severityCounts.medium})
                    </button>
                  )}
                  {severityCounts.low > 0 && (
                    <button
                      type="button"
                      className={`btn-filter-pill pill-low ${severityFilter === 'low' ? 'active' : ''}`}
                      onClick={() => setSeverityFilter(severityFilter === 'low' ? 'ALL' : 'low')}
                    >
                      Low ({severityCounts.low})
                    </button>
                  )}
                </div>
              </div>

              <div className="filter-group-right">
                {/* Category Dropdown */}
                {availableCategories.length > 1 && (
                  <div className="select-wrapper">
                    <label htmlFor="findings-cat-filter" className="filter-label-inline">Category:</label>
                    <select
                      id="findings-cat-filter"
                      className="form-input form-input-sm filter-select-compact"
                      value={categoryFilter}
                      onChange={(e) => setCategoryFilter(e.target.value)}
                    >
                      <option value="ALL">All Categories</option>
                      {availableCategories.map((cat) => (
                        <option key={cat} value={cat}>
                          {getCategoryLabel(cat)}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Grouping Dropdown */}
                <div className="select-wrapper">
                  <label htmlFor="findings-group-by" className="filter-label-inline">Group by:</label>
                  <select
                    id="findings-group-by"
                    className="form-input form-input-sm filter-select-compact"
                    value={groupBy}
                    onChange={(e) => setGroupBy(e.target.value)}
                  >
                    <option value="none">No Grouping</option>
                    <option value="category">Category</option>
                    <option value="severity">Severity</option>
                  </select>
                </div>

                {/* Reset Filters */}
                {(severityFilter !== 'ALL' || categoryFilter !== 'ALL') && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-xs btn-reset-filters"
                    onClick={() => {
                      setSeverityFilter('ALL');
                      setCategoryFilter('ALL');
                    }}
                  >
                    Reset Filters
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Filter Empty State */}
          {filteredFindings.length === 0 ? (
            <div className="empty-state empty-state-filtered">
              <p className="empty-state-title">No Findings Match Active Filters</p>
              <p className="empty-state-text">
                No defects matched severity: <code>{severityFilter}</code> and category: <code>{categoryFilter}</code>.
              </p>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setSeverityFilter('ALL');
                  setCategoryFilter('ALL');
                }}
              >
                Clear Active Filters
              </button>
            </div>
          ) : groupBy !== 'none' && groupedFindings ? (
            /* Grouped Findings List */
            <div className="grouped-findings-container">
              {Object.entries(groupedFindings).map(([groupTitle, groupItems]) => (
                <div key={groupTitle} className="findings-group-section">
                  <div className="findings-group-header">
                    <h3 className="findings-group-title">{groupTitle}</h3>
                    <span className="findings-group-count">{groupItems.length}</span>
                  </div>
                  <div className="findings-list">
                    {groupItems.map(renderFindingCard)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* Flat Findings List */
            <div className="findings-list">
              {filteredFindings.map(renderFindingCard)}
            </div>
          )}
        </>
      )}
    </section>
  );
}
