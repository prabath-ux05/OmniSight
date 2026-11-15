import React, { useMemo } from 'react';
import { RunProposalsDashboard } from './RepairProposalWorkflow';

/**
 * RepairProposalPage provides the dedicated, first-class Repair Proposal review
 * and approval governance interface.
 *
 * Supported features:
 * 1. Dedicated layout conforming to OmniSight shared design system.
 * 2. Active run context with run switching and direct URL route synchronization.
 * 3. Human-in-the-Loop proposal review (approve, reject, notes, unified diff).
 * 4. Visual Before/After split-view comparison with interactive slider.
 * 5. Selected proposal highlighting and deep-linking support.
 * 6. Graceful fallbacks for missing run IDs or empty proposals.
 */
export default function RepairProposalPage({
  run = null,
  runsList = [],
  onSelectRun = () => {},
  findings = [],
  proposals = [],
  isLoading = false,
  selectedProposalId = null,
  onSelectProposal = () => {},
  onRefreshProposals = () => {},
  onApproveProposal = async () => false,
  onRejectProposal = async () => false,
  onCreateProposal = async () => false,
  onSelectView = () => {},
  onNavigateToRepair = () => {},
}) {
  // If no run is actively passed but runsList has runs, allow quick selection
  const availableRuns = Array.isArray(runsList) ? runsList : [];

  const activeProposalsCount = Array.isArray(proposals) ? proposals.length : 0;
  const activeFindingsCount = Array.isArray(findings) ? findings.length : 0;

  return (
    <div className="repair-proposals-page-container shell-view-container">
      {/* 1. Dedicated Hero Header */}
      <section className="shell-hero-card proposals-hero-card" aria-label="Repair Proposals Header">
        <div className="inspection-hero-header-row">
          <div className="inspection-hero-titles">
            <div className="inspection-hero-badge-row">
              <span className="shell-hero-badge">
                <span className="status-dot status-dot-online" aria-hidden="true"></span>
                Human-in-the-Loop Governance
              </span>
              <span className="badge badge-neutral">PR Authorization Gate</span>
              {run?.status && (
                <span className={`badge ${run.status === 'completed' ? 'badge-completed-run' : 'badge-active-run'}`}>
                  Run: {run.status.toUpperCase()}
                </span>
              )}
            </div>

            <h1 className="shell-hero-title">Repair Proposals &amp; Pull Request Governance</h1>
            <p className="shell-hero-desc">
              Review autonomous self-healing locator fixes, inspect minimal unified diffs,
              authorize automated pull requests, and empirically verify patches across viewports.
            </p>
          </div>

          <div className="inspection-hero-actions">
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onSelectView('inspection')}
              title="Return to Live Inspection Studio"
            >
              🔍 Live Studio →
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onSelectView('repair')}
              title="Open the interactive Locator Synthesizer & Assistant"
            >
              🔧 Repair Workspace →
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => onSelectView('history')}
              title="Browse historical audit log of runs"
            >
              📋 Run History →
            </button>
          </div>
        </div>

        {/* 2. Run Context & Switcher Strip */}
        <div className="repair-run-context-bar" style={{ marginTop: '1.25rem' }}>
          <div className="context-item">
            <span className="context-label">Inspection Run:</span>
            {run?.run_id ? (
              <span className="context-val font-mono">{run.run_id}</span>
            ) : (
              <span className="context-val text-muted">No run selected</span>
            )}
          </div>

          <div className="context-item context-url-item">
            <span className="context-label">Target URL:</span>
            {run?.url ? (
              <a
                href={run.url}
                target="_blank"
                rel="noopener noreferrer"
                className="context-link"
                title={run.url}
              >
                {run.url} ↗
              </a>
            ) : (
              <span className="context-val text-muted">—</span>
            )}
          </div>

          <div className="context-item">
            <span className="context-label">Recorded Defects:</span>
            <span className="context-val badge-neutral">{activeFindingsCount}</span>
          </div>

          <div className="context-item">
            <span className="context-label">Proposals:</span>
            <span className="context-val badge-neutral">{activeProposalsCount}</span>
          </div>

          {availableRuns.length > 1 && (
            <div className="context-item context-switch-item">
              <label htmlFor="proposals-run-switcher" className="context-label">Switch Run:</label>
              <select
                id="proposals-run-switcher"
                className="form-select form-select-xs"
                value={run?.run_id || ''}
                onChange={(e) => {
                  const target = availableRuns.find((r) => r.run_id === e.target.value);
                  if (target) onSelectRun(target);
                }}
              >
                {availableRuns.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id} ({r.status || 'unknown'})
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>
      </section>

      {/* 3. Main Proposals View Body */}
      {!run ? (
        <section className="card proposals-empty-selection-card">
          <div className="empty-state">
            <span className="empty-icon">🛡️</span>
            <h3 className="empty-title">No Inspection Run Selected</h3>
            <p className="empty-state-text">
              Please choose a completed inspection run to review its self-healing repair proposals,
              or launch a fresh live inspection to detect defects.
            </p>
            {availableRuns.length > 0 ? (
              <div className="empty-run-picker" style={{ marginTop: '1.25rem' }}>
                <p style={{ fontWeight: 600, marginBottom: '0.75rem', fontSize: '0.9rem' }}>
                  Available Runs from History:
                </p>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                  {availableRuns.slice(0, 5).map((r) => (
                    <button
                      key={r.run_id}
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => onSelectRun(r)}
                    >
                      {r.run_id} ({r.status})
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="empty-action-group" style={{ marginTop: '1.25rem' }}>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => onSelectView('inspection')}
                >
                  🚀 Launch Live Inspection
                </button>
              </div>
            )}
          </div>
        </section>
      ) : (
        <RunProposalsDashboard
          run={run}
          findings={findings}
          proposals={proposals}
          isLoading={isLoading}
          selectedProposalId={selectedProposalId}
          onSelectProposal={onSelectProposal}
          onRefreshProposals={onRefreshProposals}
          onApprove={onApproveProposal}
          onReject={onRejectProposal}
          onCreateProposal={onCreateProposal}
        />
      )}
    </div>
  );
}
