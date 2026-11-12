import React from 'react';
import InspectionForm from './InspectionForm';
import RunStatusCard from './RunStatusCard';
import FindingsSection from './FindingsSection';
import EvidenceSection from './EvidenceSection';

/**
 * InspectionPage provides the dedicated, polished Live Inspection Studio.
 *
 * Requirements met:
 * 1. Dedicated layout conforming to shared design system.
 * 2. URL input & start inspection action (reuses InspectionForm).
 * 3. Run status, stage progress, and polling controls (reuses RunStatusCard).
 * 4. Filterable & groupable defect findings (reuses FindingsSection).
 * 5. Affected element details, screenshot & DOM evidence (reuses EvidenceSection).
 * 6. Finding navigation to repair workflow.
 * 7. Comprehensive loading, empty, error, and completed states.
 * 8. Clear visual distinction between active in-flight runs and historical completed runs.
 */
export default function InspectionPage({
  onStartInspection,
  isRunLoading,
  currentRun,
  onRefreshRun,
  isAutoPolling,
  onToggleAutoPolling,
  onLookupRun,
  onExecutePipeline,
  isExecuting,
  findings,
  isFindingsLoading,
  findingsError,
  selectedFinding,
  onSelectFinding,
  includeMockFindings,
  onToggleMockFindings,
  onRefreshFindings,
  repairs,
  onSuggestRepair,
  repairingFindingId,
  repairError,
  proposalsCount = 0,
  onNavigateToRepair,
  onSelectView,
}) {
  const rawStatus = currentRun?.status;
  const normalizedStatus = typeof rawStatus === 'string' ? rawStatus.trim().toLowerCase() : '';
  const statusUpper = normalizedStatus ? normalizedStatus.toUpperCase() : 'UNKNOWN';

  const TERMINAL_STATUSES = ['completed', 'failed', 'cancelled'];
  const isTerminal = Boolean(currentRun && TERMINAL_STATUSES.includes(normalizedStatus));
  const isActive = Boolean(currentRun && !isTerminal && normalizedStatus);

  return (
    <div className="inspection-studio-container">
      {/* 1. Inspection Studio Header Banner */}
      <section className="shell-hero-card inspection-studio-hero" aria-label="Inspection Studio Header">
        <div className="inspection-hero-header-row">
          <div className="inspection-hero-titles">
            <div className="inspection-hero-badge-row">
              <span className="shell-hero-badge">
                <span className="status-dot status-dot-online" aria-hidden="true"></span>
                OmniSight Studio
              </span>

              {/* Status distinction: Active vs Historical vs Idle */}
              {currentRun ? (
                isActive ? (
                  <span className="badge badge-active-run" title="Inspection pipeline is currently executing">
                    <span className="polling-pulse-dot" aria-hidden="true"></span>
                    Live Pipeline In Progress ({statusUpper})
                  </span>
                ) : normalizedStatus === 'completed' ? (
                  <span className="badge badge-completed-run" title="Inspection completed and audited in PostgreSQL">
                    ✓ Audited Run (Completed)
                  </span>
                ) : (
                  <span className="badge badge-terminal-run" title={`Terminal status: ${statusUpper}`}>
                    ✕ Terminal Run ({statusUpper})
                  </span>
                )
              ) : (
                <span className="badge badge-idle-studio" title="No inspection run currently loaded">
                  Studio Idle — Ready for Target URL
                </span>
              )}
            </div>

            <h1 className="shell-hero-title">Live Inspection Studio</h1>
            <p className="shell-hero-desc">
              Execute real-time browser sessions with Playwright, detect visual and DOM discrepancies
              using multimodal vision models, and inspect localized evidence artifacts.
            </p>
          </div>

          <div className="inspection-hero-actions">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onSelectView('history')}
              title="Browse historical audit log of runs"
            >
              📋 Browse Run History →
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onSelectView('repair')}
              title="Review repair proposals and pull request governance"
            >
              🛡️ Repair Workflow ({proposalsCount}) →
            </button>
          </div>
        </div>
      </section>

      {/* 2. Inspection Launch Form (Reusing InspectionForm) */}
      <section className="inspection-form-wrapper" aria-label="Target URL Dispatch">
        <InspectionForm
          onSubmit={onStartInspection}
          isLoading={isRunLoading}
        />
      </section>

      {/* 3. Run Status & Execution Lifecycle Card (Reusing RunStatusCard) */}
      <section className="inspection-status-wrapper" aria-label="Run Status Card">
        <RunStatusCard
          run={currentRun}
          onRefresh={onRefreshRun}
          isRefreshing={isRunLoading}
          isAutoPolling={isAutoPolling}
          onToggleAutoPolling={onToggleAutoPolling}
          onLookupRun={onLookupRun}
          onExecutePipeline={onExecutePipeline}
          isExecuting={isExecuting}
        />
      </section>

      {/* 4. Split Grid: Filterable Findings & Evidence Preview */}
      <div className="dashboard-split-grid inspection-split-grid" aria-label="Findings and Evidence Split View">
        <FindingsSection
          findings={findings}
          isLoading={isFindingsLoading}
          selectedFindingId={selectedFinding?.finding_id}
          onSelectFinding={onSelectFinding}
          runId={currentRun?.run_id}
          runStatus={currentRun?.status}
          runError={currentRun?.error}
          includeMock={includeMockFindings}
          onToggleMockFindings={onToggleMockFindings}
          onRefreshFindings={onRefreshFindings}
          findingsError={findingsError}
          repairs={repairs}
          onSuggestRepair={onSuggestRepair}
          repairingFindingId={repairingFindingId}
          onNavigateToRepair={onNavigateToRepair}
        />

        <EvidenceSection
          finding={selectedFinding}
          runId={currentRun?.run_id}
          repair={selectedFinding ? repairs[selectedFinding.finding_id] : null}
          isRepairing={selectedFinding && repairingFindingId === selectedFinding.finding_id}
          repairError={repairError}
          onSuggestRepair={(verifyLive) => selectedFinding && onSuggestRepair(selectedFinding.finding_id, verifyLive)}
          onNavigateToRepair={onNavigateToRepair}
        />
      </div>

      {/* 5. Self-Healing Repair Proposals Banner (If active run exists) */}
      {currentRun && (
        <section className="card proposals-shortcut-card" aria-label="Repair Proposals Shortcut">
          <div className="shortcut-content">
            <div>
              <h3 className="shortcut-title">Self-Healing Repair Proposals</h3>
              <p className="shortcut-desc">
                {proposalsCount > 0
                  ? `${proposalsCount} repair proposal(s) recorded for run '${currentRun.run_id ? String(currentRun.run_id) : '—'}'. Review, authorize, and submit PR fixes with human-in-the-loop governance.`
                  : `No repair proposals drafted yet for run '${currentRun.run_id ? String(currentRun.run_id) : '—'}'. Discover resilient locators and create PR branches in the Repair Workflow.`}
              </p>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => onNavigateToRepair ? onNavigateToRepair() : onSelectView('repair')}
            >
              Go to Repair Workflow ({proposalsCount}) →
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
