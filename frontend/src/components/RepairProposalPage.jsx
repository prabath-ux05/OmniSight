import React, { useState, useMemo } from 'react';
import DefectHighlightOverlay from './DefectHighlightOverlay';
import VisualComparisonSplitView from './VisualComparisonSplitView';
import RepairAssistantChat from './RepairAssistantChat';
import { FindingRepairWorkflow, RunProposalsDashboard } from './RepairProposalWorkflow';
import { getArtifactUrl } from '../services/api';

/**
 * Extract filename from artifact path.
 */
function extractFilename(p, fallback) {
  if (!p) return null;
  const clean = p.replace(/\\/g, '/');
  const name = clean.substring(clean.lastIndexOf('/') + 1);
  return name || fallback;
}

/**
 * RepairProposalPage provides the single unified destination for:
 * 1. Proposal selection and review.
 * 2. Defect findings and affected element details.
 * 3. Original screenshots and highlighted evidence (DefectHighlightOverlay).
 * 4. DOM and artifact evidence links.
 * 5. Minimal unified diff patches and proposed changes.
 * 6. Controlled sandbox execution and live-page testing.
 * 7. Before/after split-view visual comparison (VisualComparisonSplitView).
 * 8. Empirical verification results.
 * 9. Explicit human approval and rejection governance.
 * 10. Contextual AI repair assistant chatbot (RepairAssistantChat).
 */
export default function RepairProposalPage({
  run = null,
  runsList = [],
  onSelectRun = () => {},
  findings = [],
  isFindingsLoading = false,
  selectedFinding = null,
  onSelectFinding = () => {},
  repairs = {},
  repairingFindingId = null,
  repairError = '',
  onSuggestRepair = async () => {},
  proposals = [],
  isProposalsLoading = false,
  selectedProposalId = null,
  onSelectProposal = () => {},
  onRefreshProposals = () => {},
  onApproveProposal = async () => false,
  onRejectProposal = async () => false,
  onCreateProposal = async () => false,
  onSelectView = () => {},
}) {
  // Collapsible AI Chatbot panel state (default open for convenience)
  const [isChatOpen, setIsChatOpen] = useState(true);

  // Evidence Preview tab: 'before' | 'after' | 'split'
  const [activePreviewTab, setActivePreviewTab] = useState('before');

  // Governance workflow tab: 'proposals-dashboard' | 'patch-pr'
  const [activeGovernanceTab, setActiveGovernanceTab] = useState('proposals-dashboard');

  // Fallback finding selection
  const currentFinding = useMemo(() => {
    if (selectedFinding) return selectedFinding;
    if (Array.isArray(findings) && findings.length > 0) return findings[0];
    return null;
  }, [selectedFinding, findings]);

  // Repair candidate for current finding
  const currentRepair = useMemo(() => {
    if (!currentFinding?.finding_id) return null;
    return repairs[currentFinding.finding_id] || null;
  }, [repairs, currentFinding?.finding_id]);

  // Proposal for current finding or selected proposal ID
  const currentProposal = useMemo(() => {
    if (!Array.isArray(proposals) || proposals.length === 0) return null;
    if (selectedProposalId) {
      const match = proposals.find((p) => p.proposal_id === selectedProposalId);
      if (match) return match;
    }
    if (currentFinding?.finding_id) {
      const match = proposals.find((p) => p.finding_id === currentFinding.finding_id);
      if (match) return match;
    }
    return proposals[0] || null;
  }, [proposals, selectedProposalId, currentFinding?.finding_id]);

  // Evidence screenshot & DOM snapshot paths
  const evidence = currentFinding?.evidence || {};
  const screenshotFilename = extractFilename(evidence.screenshot_path, 'before.png');
  const domFilename = extractFilename(evidence.dom_snapshot_path, 'dom.html');

  const beforeScreenshotUrl = run?.run_id && screenshotFilename
    ? getArtifactUrl(run.run_id, screenshotFilename)
    : null;

  const domSnapshotUrl = run?.run_id && domFilename
    ? getArtifactUrl(run.run_id, domFilename)
    : null;

  const availableRuns = Array.isArray(runsList) ? runsList : [];
  const activeProposalsCount = Array.isArray(proposals) ? proposals.length : 0;
  const activeFindingsCount = Array.isArray(findings) ? findings.length : 0;

  // Local live page verification trigger
  const [isVerifyingLive, setIsVerifyingLive] = useState(false);
  const handleTriggerLiveVerify = async () => {
    if (!run?.run_id || !currentFinding?.finding_id) return;
    setIsVerifyingLive(true);
    await onSuggestRepair(currentFinding.finding_id, true);
    setIsVerifyingLive(false);
    setActivePreviewTab('after');
  };

  return (
    <div className="repair-proposals-page-container shell-view-container" aria-label="Repair Proposals Page">
      {/* 1. Unified Hero Header */}
      <section className="shell-hero-card proposals-hero-card" aria-label="Repair Proposals Header">
        <div className="inspection-hero-header-row">
          <div className="inspection-hero-titles">
            <div className="inspection-hero-badge-row">
              <span className="shell-hero-badge">
                <span className="status-dot status-dot-online" aria-hidden="true"></span>
                Human-in-the-Loop Governance
              </span>
              <span className="badge badge-neutral">Autonomous Self-Healing</span>
              {run?.status && (
                <span className={`badge ${run.status === 'completed' ? 'badge-completed-run' : 'badge-active-run'}`}>
                  Run: {run.status.toUpperCase()}
                </span>
              )}
            </div>

            <h1 className="shell-hero-title">Repair Proposals &amp; Self-Healing Governance</h1>
            <p className="shell-hero-desc">
              Review self-healing locator recommendations, inspect defect evidence with visual bounding boxes,
              converse with the grounded AI assistant, execute safe minimal patches, and authorize pull requests.
            </p>
          </div>

          <div className="inspection-hero-actions">
            <button
              type="button"
              className={`btn btn-sm ${isChatOpen ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setIsChatOpen((prev) => !prev)}
              title="Toggle AI Repair Assistant panel"
            >
              🤖 {isChatOpen ? 'Hide AI Assistant' : 'Open AI Assistant'}
            </button>
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

      {/* 3. Empty State when No Run is Selected */}
      {!run ? (
        <section className="card proposals-empty-selection-card">
          <div className="empty-state">
            <span className="empty-icon">🛡️</span>
            <h3 className="empty-title">No Inspection Run Selected</h3>
            <p className="empty-state-text">
              Please choose an inspection run below to review its self-healing repair proposals and chat with the AI assistant,
              or launch a live inspection to audit a new website.
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
        <>
          {/* 4. Defect Findings Selector Bar */}
          {findings && findings.length > 0 ? (
            <div className="repair-finding-selector-card">
              <div className="finding-selector-header">
                <span className="finding-selector-title">Select Finding to Inspect &amp; Heal:</span>
                <span className="finding-selector-count">
                  {findings.length} defect{findings.length === 1 ? '' : 's'} recorded
                </span>
              </div>

              <div className="finding-pills-row">
                {findings.map((f, idx) => {
                  const isSelected = currentFinding?.finding_id === f.finding_id;
                  const sevClass = `badge-sev-${f.severity || 'medium'}`;
                  return (
                    <button
                      key={f.finding_id || idx}
                      type="button"
                      className={`finding-pill-btn ${isSelected ? 'active' : ''}`}
                      onClick={() => onSelectFinding(f)}
                    >
                      <span className={`finding-sev-dot ${sevClass}`}></span>
                      <span className="finding-pill-id">#{f.finding_id}</span>
                      <span className="finding-pill-cat">{f.category?.replace(/_/g, ' ')}</span>
                      {repairs[f.finding_id]?.repaired && (
                        <span className="finding-healed-check" title="Candidate locator synthesized">✓</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ) : run?.status === 'failed' ? (
            <div className="card repair-clean-run-card" style={{ borderColor: 'var(--color-danger, #ef4444)' }}>
              <div className="clean-check-icon" style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', color: '#ef4444' }}>✕</div>
              <h4 className="clean-title" style={{ color: '#ef4444' }}>Inspection Run Failed</h4>
              <p className="empty-state-text">
                Run <code>{run.run_id}</code> encountered an error during inspection: {run.error || run.message || 'Pipeline execution failed'}.
              </p>
            </div>
          ) : (
            <div className="card repair-clean-run-card">
              <div className="clean-check-icon">✓</div>
              <h4 className="clean-title">Zero Defects In This Run</h4>
              <p className="empty-state-text">
                Run <code>{run.run_id}</code> passed inspection cleanly with no locator regressions or visual defects.
              </p>
            </div>
          )}

          {/* 5. Selected Finding Detail Card */}
          {currentFinding && (
            <div className="repair-finding-detail-card">
              <div className="finding-detail-header">
                <div className="finding-detail-title-group">
                  <div className="finding-detail-badges">
                    <span className={`badge badge-sev-${currentFinding.severity || 'medium'}`}>
                      {(currentFinding.severity || 'medium').toUpperCase()}
                    </span>
                    <span className="badge badge-category">
                      {currentFinding.category?.replace(/_/g, ' ')}
                    </span>
                    <span className="finding-id-pill font-mono">
                      ID: {currentFinding.finding_id}
                    </span>
                  </div>
                  <h3 className="finding-detail-heading">{currentFinding.description}</h3>
                </div>

                <div className="finding-detail-actions">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={() => onSuggestRepair(currentFinding.finding_id, false)}
                    disabled={repairingFindingId === currentFinding.finding_id}
                  >
                    {repairingFindingId === currentFinding.finding_id
                      ? 'Synthesizing...'
                      : currentRepair?.repaired
                      ? '🔄 Re-Analyze Candidates'
                      : '⚡ Synthesize Locator Fix'}
                  </button>
                </div>
              </div>

              {/* Target Selector & Root Cause Details */}
              <div className="finding-meta-grid">
                <div className="finding-meta-item">
                  <span className="meta-label">Failed / Missing Selector:</span>
                  <div className="meta-selector-box">
                    <code className="font-mono selector-text">
                      {currentFinding.selector || 'Global layout scope'}
                    </code>
                  </div>
                </div>

                <div className="finding-meta-item">
                  <span className="meta-label">Detection Confidence:</span>
                  <span className="meta-val">
                    {typeof currentFinding.confidence === 'number'
                      ? `${Math.round(currentFinding.confidence * 100)}%`
                      : '—'}
                  </span>
                </div>

                <div className="finding-meta-item">
                  <span className="meta-label">Self-Healing Status:</span>
                  <span className="meta-val">
                    {currentRepair?.repaired ? (
                      <span className="text-success font-semibold">
                        ✓ Candidate Synthesized ({Math.round((currentRepair.confidence || 0) * 100)}% resilience)
                      </span>
                    ) : currentRepair ? (
                      <span className="text-warning">Repair Inconclusive</span>
                    ) : (
                      <span className="text-muted">Awaiting Synthesis</span>
                    )}
                  </span>
                </div>
              </div>

              {repairError && (
                <div className="alert-box alert-error" style={{ marginTop: '0.75rem' }}>
                  <span>{repairError}</span>
                </div>
              )}
            </div>
          )}

          {/* 6. Unified Two-Column Grid: Restored AI Chatbot + Evidence & Verification Preview */}
          <div className={`repair-workspace-split-grid ${!isChatOpen ? 'chat-collapsed' : ''}`}>
            {/* Left Column: Contextual Chatbot Assistant */}
            {isChatOpen && (
              <RepairAssistantChat
                run={run}
                finding={currentFinding}
                repair={currentRepair}
                proposal={currentProposal}
                isOpen={isChatOpen}
                onClose={() => setIsChatOpen(false)}
              />
            )}

            {/* Right Column: Visual Evidence & Verification Preview */}
            <div className="repair-preview-pane card">
              <div className="preview-card-header">
                <div className="preview-header-left">
                  <h4 className="preview-title">Visual Evidence &amp; Verification Preview</h4>
                  <p className="preview-subtitle">
                    Examine captured defect evidence and verified repair outcomes.
                  </p>
                </div>

                <div className="preview-tab-controls">
                  <button
                    type="button"
                    className={`preview-tab-btn ${activePreviewTab === 'before' ? 'active' : ''}`}
                    onClick={() => setActivePreviewTab('before')}
                  >
                    Original Evidence (Before)
                  </button>
                  <button
                    type="button"
                    className={`preview-tab-btn ${activePreviewTab === 'after' ? 'active' : ''}`}
                    onClick={() => setActivePreviewTab('after')}
                  >
                    Repaired Preview (After)
                  </button>
                  <button
                    type="button"
                    className={`preview-tab-btn ${activePreviewTab === 'split' ? 'active' : ''}`}
                    onClick={() => setActivePreviewTab('split')}
                  >
                    Split-View Comparison ↔
                  </button>
                </div>
              </div>

              {/* Tab 1: Before Evidence with Vector DefectHighlightOverlay */}
              {activePreviewTab === 'before' && (
                <div className="preview-content-box">
                  <div className="preview-meta-row">
                    <span className="preview-status-pill badge-danger">
                      Defective State (Before Patch)
                    </span>
                    {beforeScreenshotUrl && (
                      <a
                        href={beforeScreenshotUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-link btn-link-sm"
                      >
                        Open Full Screenshot ↗
                      </a>
                    )}
                  </div>

                  <div className="preview-viewport-box">
                    {beforeScreenshotUrl ? (
                      <DefectHighlightOverlay
                        imageSrc={beforeScreenshotUrl}
                        alt="Before Defect Viewport"
                        findings={findings}
                        selectedFindingId={currentFinding?.finding_id}
                        onSelectFinding={(fid) => {
                          const target = findings.find((f) => f.finding_id === fid);
                          if (target) onSelectFinding(target);
                        }}
                        viewport={currentFinding?.viewport || 'desktop'}
                        stage="before"
                      />
                    ) : (
                      <div className="preview-fallback-box">
                        <span className="fallback-icon">🖼️</span>
                        <h5 className="fallback-heading">Screenshot Artifact Not Available</h5>
                        <p className="fallback-text">
                          No visual screenshot artifact path was recorded for this finding.
                        </p>
                      </div>
                    )}
                  </div>

                  {/* DOM snapshot & affected element snippet */}
                  <div className="preview-artifact-links">
                    <div className="artifact-link-item">
                      <span className="artifact-label">DOM Snapshot:</span>
                      {domSnapshotUrl ? (
                        <a
                          href={domSnapshotUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-link btn-link-sm"
                        >
                          View Captured HTML ↗
                        </a>
                      ) : (
                        <span className="text-muted">None recorded</span>
                      )}
                    </div>

                    <div className="artifact-link-item">
                      <span className="artifact-label">Live Target:</span>
                      {run?.url ? (
                        <a
                          href={run.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="btn-link btn-link-sm"
                        >
                          Open Live Page ↗
                        </a>
                      ) : (
                        <span className="text-muted">—</span>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: After Evidence / Verification Preview */}
              {activePreviewTab === 'after' && (
                <div className="preview-content-box">
                  {currentRepair?.live_verification?.is_verified ||
                  currentProposal?.verification_status === 'verified_success' ? (
                    <div className="verification-success-box">
                      <div className="verification-header">
                        <span className="verification-check-icon">✓</span>
                        <div>
                          <h5 className="verification-title">Live Fresh-Page Verification Succeeded!</h5>
                          <span className="verification-badge badge-success">
                            Verified on Live Target
                          </span>
                        </div>
                      </div>

                      <div className="verification-details-grid">
                        <div className="verify-detail-item">
                          <span className="detail-label">Verified Target URL:</span>
                          <span className="detail-val font-mono">
                            {currentRepair?.live_verification?.target_url || run?.url}
                          </span>
                        </div>
                        <div className="verify-detail-item">
                          <span className="detail-label">Resolved Element Tag:</span>
                          <span className="detail-val font-mono">
                            &lt;{currentRepair?.live_verification?.resolved_tag || 'element'}&gt;
                          </span>
                        </div>
                        <div className="verify-detail-item">
                          <span className="detail-label">DOM Unique Matches:</span>
                          <span className="detail-val">
                            {currentRepair?.live_verification?.matches} (Exactly 1 expected)
                          </span>
                        </div>
                        <div className="verify-detail-item">
                          <span className="detail-label">Validation Message:</span>
                          <span className="detail-val">
                            {currentRepair?.live_verification?.validation_message}
                          </span>
                        </div>
                      </div>

                      <p className="verification-note">
                        Candidate locator <code>{currentRepair?.best_locator}</code> was tested against the live webpage and uniquely resolved the intended element.
                      </p>
                    </div>
                  ) : (
                    <div className="verification-pending-box">
                      <div className="pending-icon-row">
                        <span className="pending-icon">⏳</span>
                        <span className="badge badge-warning">Verification Pending</span>
                      </div>
                      <h5 className="pending-title">Post-Repair Preview Withheld</h5>
                      <p className="pending-desc">
                        OmniSight enforces strict empirical verification: a repaired preview is <strong>never displayed</strong> unless the backend executes a fresh browser session and confirms successful element resolution.
                      </p>

                      <div className="pending-status-checklist">
                        <div className="check-item">
                          <span className="check-bullet">•</span>
                          <span>Candidate Locator Synthesized: {currentRepair?.repaired ? '✓ Yes' : '— Pending'}</span>
                        </div>
                        <div className="check-item">
                          <span className="check-bullet">•</span>
                          <span>Snapshot DOM Resolution: {currentRepair?.validation?.is_valid ? '✓ Validated' : '— Pending'}</span>
                        </div>
                        <div className="check-item">
                          <span className="check-bullet">•</span>
                          <span>Live Page Browser Verification: {currentRepair?.live_verification?.attempted ? 'Attempted' : '— Not yet run'}</span>
                        </div>
                      </div>

                      <div className="pending-actions">
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={handleTriggerLiveVerify}
                          disabled={isVerifyingLive || !currentFinding?.finding_id}
                        >
                          {isVerifyingLive ? 'Testing Live Page...' : '🚀 Test Candidate Against Live Page'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab 3: Visual Comparison Split View */}
              {activePreviewTab === 'split' && (
                <div className="preview-content-box preview-split-box">
                  {currentProposal?.proposal_id || (proposals && proposals[0]?.proposal_id) ? (
                    <VisualComparisonSplitView
                      runId={run?.run_id}
                      proposalId={currentProposal?.proposal_id || proposals[0]?.proposal_id}
                      finding={currentFinding}
                      initialViewport={currentFinding?.viewport || 'desktop'}
                      onDecisionUpdated={() => {
                        if (onRefreshProposals) onRefreshProposals();
                      }}
                      onClose={() => setActivePreviewTab('before')}
                    />
                  ) : (
                    <div className="preview-fallback-box">
                      <span className="fallback-icon">🛡️</span>
                      <h5 className="fallback-heading">No Proposals Available for Split Comparison</h5>
                      <p className="fallback-text">
                        A repair proposal is required to compare before and after patch rendering.
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 7. Unified Human-in-the-Loop Governance & Proposal Review */}
          <div className="repair-governance-section" style={{ marginTop: '2rem' }}>
            <div className="governance-tab-bar">
              <button
                type="button"
                className={`gov-tab-btn ${activeGovernanceTab === 'proposals-dashboard' ? 'active' : ''}`}
                onClick={() => setActiveGovernanceTab('proposals-dashboard')}
              >
                📋 Run Proposals Review &amp; Decisions ({activeProposalsCount})
              </button>
              <button
                type="button"
                className={`gov-tab-btn ${activeGovernanceTab === 'patch-pr' ? 'active' : ''}`}
                onClick={() => setActiveGovernanceTab('patch-pr')}
              >
                🛠️ Single Finding Patch &amp; PR Workflow
              </button>
            </div>

            <div className="governance-tab-content">
              {activeGovernanceTab === 'proposals-dashboard' ? (
                <RunProposalsDashboard
                  run={run}
                  findings={findings}
                  proposals={proposals}
                  isLoading={isProposalsLoading}
                  selectedProposalId={selectedProposalId}
                  onSelectProposal={onSelectProposal}
                  onRefreshProposals={onRefreshProposals}
                  onApprove={onApproveProposal}
                  onReject={onRejectProposal}
                  onCreateProposal={onCreateProposal}
                />
              ) : (
                currentFinding ? (
                  <FindingRepairWorkflow
                    finding={currentFinding}
                    runId={run?.run_id}
                    repair={currentRepair}
                  />
                ) : (
                  <div className="empty-state">
                    <p className="empty-state-text">Select a finding above to generate a patch and review proposals.</p>
                  </div>
                )
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
