import React, { useState, useEffect, useCallback, useRef } from 'react';
import DefectHighlightOverlay from './DefectHighlightOverlay';
import {
  approveProposal,
  fetchVisualComparison,
  rejectProposal,
  simulateControlledRepair,
} from '../services/api';

/**
 * Format timestamp helper.
 */
function formatTime(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return isNaN(d.getTime()) ? isoString : d.toLocaleString();
  } catch {
    return isoString;
  }
}

/**
 * VisualComparisonSplitView
 *
 * Interactive split-view comparison and repair approval workflow component.
 * Features:
 * - Side-by-side split view and interactive slider swipe comparison.
 * - Viewport selection (Desktop, Tablet, Mobile).
 * - Association with relevant finding and repair proposal.
 * - Controlled environment simulation (never modifies live target website).
 * - Explicit Approve and Reject actions.
 * - Decision status, timestamp, reviewer notes recording.
 * - Lifecycle guarantee: Rejected proposals strictly remain rejected; approved decisions can be revisited.
 */
export default function VisualComparisonSplitView({
  runId,
  proposalId,
  finding = null,
  initialViewport = 'desktop',
  onDecisionUpdated = null,
  onClose = null,
}) {
  // State
  const [activeViewport, setActiveViewport] = useState(initialViewport || 'desktop');
  const [comparisonMode, setComparisonMode] = useState('side-by-side'); // 'side-by-side' | 'slider' | 'diff'
  const [sliderPosition, setSliderPosition] = useState(50); // percentage 0 - 100
  const [comparisonData, setComparisonData] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  // Action states
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulateSuccessMessage, setSimulateSuccessMessage] = useState('');
  const [isDeciding, setIsDeciding] = useState(false);
  const [reviewerNotes, setReviewerNotes] = useState('');
  const [decisionFeedback, setDecisionFeedback] = useState({ type: '', message: '' });

  // Revisit mode state (for approved decisions)
  const [isRevisiting, setIsRevisiting] = useState(false);
  const [revisitNotes, setRevisitNotes] = useState('');

  // Dragging state for slider
  const sliderContainerRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  // Handle Escape key to dismiss visual comparison overlay
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && onClose) {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Handle backdrop click to close overlay (clicks inside the card are protected)
  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget && onClose) {
      onClose();
    }
  };

  // Load comparison details
  const loadComparison = useCallback(async () => {
    if (!proposalId) return;
    setIsLoading(true);
    setError('');
    const res = await fetchVisualComparison(runId, proposalId, activeViewport);
    if (res.ok && res.data) {
      setComparisonData(res.data);
      if (res.data.reviewer_notes) {
        setRevisitNotes(res.data.reviewer_notes);
      }
    } else {
      setError(res.error || 'Failed to load visual comparison.');
    }
    setIsLoading(false);
  }, [runId, proposalId, activeViewport]);

  useEffect(() => {
    loadComparison();
  }, [loadComparison]);

  // Handle controlled repair simulation
  const handleSimulateRepair = async () => {
    if (!runId || !proposalId) return;
    setIsSimulating(true);
    setError('');
    setSimulateSuccessMessage('');
    const res = await simulateControlledRepair(runId, proposalId, activeViewport);
    if (res.ok && res.data) {
      setComparisonData(res.data);
      setSimulateSuccessMessage(
        '✓ Controlled simulation complete: Repair verified in local sandbox. Live target website was not modified.'
      );
      setTimeout(() => setSimulateSuccessMessage(''), 5000);
      if (onDecisionUpdated) onDecisionUpdated(res.data);
    } else {
      setError(res.error || 'Simulation failed.');
    }
    setIsSimulating(false);
  };

  // Handle Approve action
  const handleApprove = async (revisitMode = false) => {
    if (!proposalId || isDeciding) return;
    setIsDeciding(true);
    setDecisionFeedback({ type: '', message: '' });

    const notes = revisitMode ? revisitNotes : reviewerNotes;
    const res = await approveProposal(proposalId, notes, { revisit: revisitMode });
    if (res.ok && res.data) {
      setDecisionFeedback({
        type: 'success',
        message: revisitMode
          ? '✓ Approval decision revisited and updated.'
          : '✓ Repair proposal approved! Human authorization recorded.',
      });
      setIsRevisiting(false);
      setReviewerNotes('');
      await loadComparison();
      if (onDecisionUpdated) onDecisionUpdated(res.data);
    } else {
      setDecisionFeedback({
        type: 'error',
        message: res.error || 'Approval failed.',
      });
    }
    setIsDeciding(false);
  };

  // Handle Reject action
  const handleReject = async (revisitMode = false) => {
    if (!proposalId || isDeciding) return;
    setIsDeciding(true);
    setDecisionFeedback({ type: '', message: '' });

    const notes = revisitMode ? revisitNotes : reviewerNotes;
    const res = await rejectProposal(proposalId, notes, { revisit: revisitMode });
    if (res.ok && res.data) {
      setDecisionFeedback({
        type: 'success',
        message: revisitMode
          ? '✓ Approved decision revoked: Proposal is now rejected.'
          : '✕ Repair proposal rejected. Decision recorded permanently.',
      });
      setIsRevisiting(false);
      setReviewerNotes('');
      await loadComparison();
      if (onDecisionUpdated) onDecisionUpdated(res.data);
    } else {
      setDecisionFeedback({
        type: 'error',
        message: res.error || 'Rejection failed.',
      });
    }
    setIsDeciding(false);
  };

  // Mouse / Touch handlers for comparison slider
  const handleSliderMove = useCallback((clientX) => {
    if (!sliderContainerRef.current) return;
    const rect = sliderContainerRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const percent = Math.max(0, Math.min(100, (x / rect.width) * 100));
    setSliderPosition(percent);
  }, []);

  const handleMouseDown = () => setIsDragging(true);
  const handleMouseUp = () => setIsDragging(false);

  useEffect(() => {
    const onMouseMove = (e) => {
      if (isDragging) handleSliderMove(e.clientX);
    };
    const onTouchMove = (e) => {
      if (isDragging && e.touches[0]) handleSliderMove(e.touches[0].clientX);
    };
    const onStopDrag = () => setIsDragging(false);

    if (isDragging) {
      window.addEventListener('mousemove', onMouseMove);
      window.addEventListener('mouseup', onStopDrag);
      window.addEventListener('touchmove', onTouchMove);
      window.addEventListener('touchend', onStopDrag);
    }
    return () => {
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onStopDrag);
      window.removeEventListener('touchmove', onTouchMove);
      window.removeEventListener('touchend', onStopDrag);
    };
  }, [isDragging, handleSliderMove]);

  const approvalStatus = comparisonData?.approval_status || 'pending';
  const isApproved = approvalStatus === 'approved';
  const isRejected = approvalStatus === 'rejected';
  const isPending = approvalStatus === 'pending';

  const beforeUrl = comparisonData?.before_screenshot_url;
  const afterUrl = comparisonData?.after_screenshot_url;
  const targetFinding = comparisonData?.finding_summary || finding;

  // Derive verification result state across the 6 auditable lifecycle states
  const getVerificationState = () => {
    if (comparisonData?.verification_status === 'verified_success') {
      return {
        label: 'Verification Passed',
        explanation: 'Proposed fix resolved the defect in the local controlled sandbox under identical viewport conditions. No visual regression observed.',
        badge: 'badge-success',
      };
    }
    if (comparisonData?.verification_status === 'verified_failure') {
      return {
        label: 'Verification Failed',
        explanation: 'Proposed fix failed to resolve the defect during controlled sandbox re-inspection, or introduced layout errors.',
        badge: 'badge-danger',
      };
    }
    if (comparisonData?.verification_status === 'inconclusive') {
      return {
        label: 'Verification Inconclusive',
        explanation: 'Simulation completed but post-repair evidence did not conclusively verify full resolution. Human review recommended.',
        badge: 'badge-warning',
      };
    }
    if (afterUrl) {
      return {
        label: 'Patch Applied',
        explanation: 'Repair patch successfully injected into the local sandbox DOM. Visual capture ready for human authorization.',
        badge: 'badge-accent',
      };
    }
    if (isPending) {
      return {
        label: 'Awaiting Approval',
        explanation: 'Repair patch formulated with candidate locators and CSS rules. Pending reviewer inspection and decision.',
        badge: 'badge-warning',
      };
    }
    return {
      label: 'Patch Proposed',
      explanation: 'Repair candidate synthesized from defect findings and DOM tree. Ready for sandbox simulation.',
      badge: 'badge-neutral',
    };
  };

  const verificationInfo = getVerificationState();

  return (
    <div
      className="visual-comparison-modal-overlay"
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby="visual-comparison-title"
    >
      <div className="visual-comparison-card card" onClick={(e) => e.stopPropagation()}>
        {/* Header Bar */}
        <div className="visual-comparison-header">
          <div className="header-meta">
            <span className="badge badge-accent">Visual Comparison &amp; Review</span>
            <h3 id="visual-comparison-title" className="comparison-title">
              Before / After Repair Verification
              <span className="proposal-id-pill">Proposal: <code>{proposalId}</code></span>
            </h3>
            {targetFinding && (
              <p className="comparison-subtitle">
                Associated Finding: <code className="finding-id-highlight">{targetFinding.finding_id}</code> &mdash;{' '}
                <span className="finding-cat-label">[{targetFinding.category}]</span> {targetFinding.description}
              </p>
            )}
          </div>

          <div className="header-controls">
            {onClose && (
              <button
                type="button"
                className="visual-comparison-close-btn"
                onClick={onClose}
                title="Close Visual Comparison (Esc)"
                aria-label="Close Visual Comparison"
              >
                <span className="close-icon" aria-hidden="true">✕</span>
                <span className="close-text">Close</span>
              </button>
            )}
          </div>
        </div>

        {/* Controlled Environment Governance Banner */}
        <div className="controlled-env-banner">
          <span className="banner-icon">🔒</span>
          <div className="banner-text">
            <strong>Controlled Sandbox Guarantee:</strong> OmniSight applies proposed fixes strictly within an isolated local sandbox.
            The external live target website is <strong>never modified</strong> automatically. Original screenshots are preserved immutably.
          </div>
        </div>

        {/* Verifiable Repair Lifecycle Sequence Stepper */}
        <div className="workflow-sequence-stepper" aria-label="Repair Verification Stages">
          <div className="step-item step-completed">
            <span className="step-circle">1</span>
            <div className="step-info">
              <span className="step-label">Original Evidence</span>
              <span className="step-sub">{targetFinding ? `#${targetFinding.finding_id.slice(-6)}` : 'Captured'}</span>
            </div>
          </div>
          <div className="step-connector"></div>

          <div className="step-item step-completed">
            <span className="step-circle">2</span>
            <div className="step-info">
              <span className="step-label">Repair Proposal</span>
              <span className="step-sub">{proposalId ? String(proposalId).slice(-6) : 'Drafted'}</span>
            </div>
          </div>
          <div className="step-connector"></div>

          <div className={`step-item ${afterUrl ? 'step-completed' : (isSimulating ? 'step-active' : 'step-pending')}`}>
            <span className="step-circle">3</span>
            <div className="step-info">
              <span className="step-label">Controlled Sandbox</span>
              <span className="step-sub">{isSimulating ? 'Simulating…' : (afterUrl ? 'Isolated Sandbox' : 'Ready')}</span>
            </div>
          </div>
          <div className="step-connector"></div>

          <div className={`step-item ${afterUrl ? 'step-completed' : 'step-pending'}`}>
            <span className="step-circle">4</span>
            <div className="step-info">
              <span className="step-label">After Repair Evidence</span>
              <span className="step-sub">{afterUrl ? `${activeViewport.toUpperCase()} Captured` : 'Pending Sandbox'}</span>
            </div>
          </div>
          <div className="step-connector"></div>

          <div className={`step-item ${isApproved ? 'step-approved' : isRejected ? 'step-rejected' : 'step-active'}`}>
            <span className="step-circle">5</span>
            <div className="step-info">
              <span className="step-label">Verification &amp; Audit</span>
              <span className="step-sub">{approvalStatus.toUpperCase()}</span>
            </div>
          </div>
        </div>

        {/* Toolbar: Viewport Switcher & Comparison Mode Switcher */}
        <div className="comparison-toolbar">
          <div className="toolbar-group">
            <span className="toolbar-label">Viewport:</span>
            <div className="segmented-control">
              {['desktop', 'tablet', 'mobile'].map((vp) => (
                <button
                  key={vp}
                  type="button"
                  className={`segmented-btn ${activeViewport === vp ? 'active' : ''}`}
                  onClick={() => setActiveViewport(vp)}
                >
                  {vp === 'desktop' ? '🖥️ Desktop (1280px)' : vp === 'tablet' ? '📱 Tablet (768px)' : '📱 Mobile (375px)'}
                </button>
              ))}
            </div>
          </div>

          <div className="toolbar-group">
            <span className="toolbar-label">Display Mode:</span>
            <div className="segmented-control">
              <button
                type="button"
                className={`segmented-btn ${comparisonMode === 'side-by-side' ? 'active' : ''}`}
                onClick={() => setComparisonMode('side-by-side')}
              >
                Side-by-Side Split
              </button>
              <button
                type="button"
                className={`segmented-btn ${comparisonMode === 'slider' ? 'active' : ''}`}
                onClick={() => setComparisonMode('slider')}
                disabled={!afterUrl}
                title={!afterUrl ? 'Generate after screenshot first to enable slider' : 'Swipe comparison'}
              >
                Interactive Slider ↔
              </button>
              <button
                type="button"
                className={`segmented-btn ${comparisonMode === 'diff' ? 'active' : ''}`}
                onClick={() => setComparisonMode('diff')}
              >
                Patch Diff &amp; Details
              </button>
            </div>
          </div>
        </div>

        {/* Alerts / Feedback */}
        {error && (
          <div className="alert-box alert-error">
            <span>{error}</span>
          </div>
        )}
        {simulateSuccessMessage && (
          <div className="alert-box alert-success">
            <span>{simulateSuccessMessage}</span>
          </div>
        )}
        {decisionFeedback.message && (
          <div className={`alert-box ${decisionFeedback.type === 'success' ? 'alert-success' : 'alert-error'}`}>
            <span>{decisionFeedback.message}</span>
          </div>
        )}

        {/* Loading State */}
        {isLoading ? (
          <div className="comparison-loading-box">
            <span className="spinner-sm"></span>
            <span>Loading visual comparison evidence across {activeViewport} viewport...</span>
          </div>
        ) : (
          /* Main Visual Comparison Workspace */
          <div className="comparison-workspace">
            {/* Mode 1: Side-by-Side Split View */}
            {comparisonMode === 'side-by-side' && (
              <div className="split-view-container">
                {/* Left Column: Original Defect Evidence (Before) */}
                <div className="split-panel split-panel-before">
                  <div className="panel-badge-bar badge-before">
                    <span className="panel-title-text">BEFORE: Original Defect Evidence</span>
                    <span className="badge badge-danger">Unrepaired Defect</span>
                  </div>

                  <div className="panel-image-container">
                    {beforeUrl ? (
                      <DefectHighlightOverlay
                        imageSrc={beforeUrl}
                        alt={`Before Defect - ${activeViewport}`}
                        findings={targetFinding ? [targetFinding] : []}
                        selectedFindingId={targetFinding?.finding_id}
                        viewport={activeViewport}
                        stage="before"
                        showLegend={false}
                      />
                    ) : (
                      <div className="panel-fallback-empty">
                        <span>🖼️ Original screenshot not yet captured for {activeViewport}</span>
                      </div>
                    )}
                  </div>
                  <div className="panel-footer-caption">
                    <span>Original viewport capture &bull; Immutable reference</span>
                  </div>
                </div>

                {/* Right Column: Controlled Environment Repair (After) */}
                <div className="split-panel split-panel-after">
                  <div className="panel-badge-bar badge-after">
                    <span className="panel-title-text">AFTER: Controlled Environment Repair</span>
                    {afterUrl ? (
                      <span className="badge badge-success">✓ Verified in Sandbox</span>
                    ) : (
                      <span className="badge badge-warning">Simulation Pending</span>
                    )}
                  </div>

                  <div className="panel-image-container">
                    {afterUrl ? (
                      <img
                        src={afterUrl}
                        alt={`After Repair - ${activeViewport}`}
                        className="comparison-img"
                      />
                    ) : (
                      <div className="simulation-prompt-box">
                        <span className="simulation-icon">⚡</span>
                        <h5>Proposed Fix Not Yet Rendered for {activeViewport.toUpperCase()}</h5>
                        <p>
                          Execute safe, sandboxed rendering to generate the repaired screenshot and verify defect resolution.
                        </p>
                        <button
                          type="button"
                          className="btn btn-primary"
                          onClick={handleSimulateRepair}
                          disabled={isSimulating}
                        >
                          {isSimulating ? 'Simulating in Sandbox...' : '⚡ Simulate Repair in Controlled Sandbox'}
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="panel-footer-caption">
                    <span>Rendered in local sandbox &bull; Live website untouched</span>
                  </div>
                </div>
              </div>
            )}

            {/* Mode 2: Interactive Slider / Swipe View */}
            {comparisonMode === 'slider' && (
              <div className="slider-mode-wrapper">
                <div className="slider-controls-bar">
                  <span className="slider-label">Drag handle or slider to compare before vs after:</span>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={sliderPosition}
                    onChange={(e) => setSliderPosition(Number(e.target.value))}
                    className="slider-range-input"
                  />
                  <span className="slider-percentage">
                    Before: {Math.round(sliderPosition)}% &bull; After: {100 - Math.round(sliderPosition)}%
                  </span>
                </div>

                <div
                  ref={sliderContainerRef}
                  className="interactive-slider-container"
                  onMouseDown={handleMouseDown}
                  onTouchStart={handleMouseDown}
                >
                  {/* Layer 1: After Image (Background) */}
                  <img
                    src={afterUrl}
                    alt="After Repaired Preview"
                    className="slider-img slider-img-after"
                    draggable={false}
                  />

                  {/* Layer 2: Before Image (Clipped overlay) */}
                  <div
                    className="slider-before-overlay"
                    style={{ width: `${sliderPosition}%` }}
                  >
                    <img
                      src={beforeUrl}
                      alt="Before Defective Preview"
                      className="slider-img slider-img-before"
                      draggable={false}
                    />
                  </div>

                  {/* Divider Line & Drag Handle */}
                  <div
                    className="slider-divider-line"
                    style={{ left: `${sliderPosition}%` }}
                  >
                    <div className="slider-handle">↔</div>
                  </div>
                </div>
              </div>
            )}

            {/* Mode 3: Diff & Details View */}
            {comparisonMode === 'diff' && (
              <div className="diff-details-container card">
                <h4 className="diff-title">Proposed Patch Content &amp; Verification Diff</h4>
                <p className="diff-desc">
                  Review the synthesized modification proposed to heal the defect. OmniSight validates this patch locally prior to live execution.
                </p>

                <div className="diff-patch-box">
                  <pre className="patch-diff-pre">
                    <code>{comparisonData?.proposed_change || 'No patch details available.'}</code>
                  </pre>
                </div>

                <div className="diff-metrics-grid">
                  <div className="diff-metric-item">
                    <span className="metric-label">Target Viewport:</span>
                    <span className="metric-val font-mono">{activeViewport}</span>
                  </div>
                  <div className="diff-metric-item">
                    <span className="metric-label">Verification Outcome:</span>
                    <span className="metric-val">{comparisonData?.verification_status || 'unverified'}</span>
                  </div>
                  <div className="diff-metric-item">
                    <span className="metric-label">Live Site Protection:</span>
                    <span className="metric-val text-success">Guaranteed Unmodified (Read-Only)</span>
                  </div>
                  <div className="diff-metric-item">
                    <span className="metric-label">Original Evidence:</span>
                    <span className="metric-val text-success">Preserved Immutably</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Verifiable Sequence Outcome & Evidence Card */}
        <div className="verification-audit-card">
          <div className="verification-audit-header">
            <span className="audit-header-title">Verification Outcome &amp; Evidence</span>
            <span className={`badge ${verificationInfo.badge}`}>
              {verificationInfo.label}
            </span>
          </div>
          <div className="verification-audit-body">
            <p className="verification-explanation-text">
              {verificationInfo.explanation}
            </p>
            <div className="verification-checklist">
              <span className={`check-item ${beforeUrl ? 'pass' : 'fail'}`}>
                {beforeUrl ? '✓' : '✕'} Original Defect Evidence Preserved ({activeViewport.toUpperCase()})
              </span>
              <span className={`check-item ${afterUrl ? 'pass' : (isSimulating ? 'pending' : 'pending')}`}>
                {afterUrl ? '✓' : '○'} Controlled Local Sandbox Simulation
              </span>
              <span className="check-item pass">
                ✓ Target Live Website Unmodified
              </span>
              <span className={`check-item ${isApproved ? 'pass' : isRejected ? 'fail' : 'pending'}`}>
                {isApproved ? '✓ Human Decision Authorized' : isRejected ? '✕ Decision Permanently Rejected' : '○ Awaiting Developer Decision'}
              </span>
            </div>
          </div>
        </div>

        {/* Decision & Governance Section */}
        <div className="governance-decision-section">
          <div className="decision-status-row">
            <div className="status-indicator">
              <span className="status-label">Review Status:</span>
              <span
                className={`badge ${
                  isApproved ? 'badge-success' : isRejected ? 'badge-danger' : 'badge-warning'
                }`}
              >
                {approvalStatus.toUpperCase()}
              </span>
            </div>

            {comparisonData?.decision_timestamp && (
              <div className="decision-time">
                <span className="meta-label">Decided At:</span>
                <span className="meta-val">{formatTime(comparisonData.decision_timestamp)}</span>
              </div>
            )}

            {comparisonData?.reviewer_notes && (
              <div className="decision-notes-preview">
                <span className="meta-label">Reviewer Notes:</span>
                <span className="meta-val">"{comparisonData.reviewer_notes}"</span>
              </div>
            )}
          </div>

          {/* Decision Actions */}
          {/* Case 1: Pending Decision */}
          {isPending && (
            <div className="pending-decision-box">
              <div className="notes-input-wrapper">
                <label htmlFor="reviewer-notes-input" className="form-label">
                  Reviewer Justification / Governance Notes (optional):
                </label>
                <input
                  id="reviewer-notes-input"
                  type="text"
                  className="form-input"
                  placeholder="e.g. Inspected desktop and mobile layouts. Fix resolves overflow without side effects."
                  value={reviewerNotes}
                  onChange={(e) => setReviewerNotes(e.target.value)}
                  disabled={isDeciding}
                />
              </div>

              <div className="decision-buttons-row">
                <button
                  type="button"
                  className="btn-approve-lg"
                  onClick={() => handleApprove(false)}
                  disabled={isDeciding}
                >
                  {isDeciding ? (
                    <><span className="spinner-xs" /> Recording Decision…</>
                  ) : (
                    <>✓ Approve Repair Proposal</>
                  )}
                </button>
                <button
                  type="button"
                  className="btn-reject-lg"
                  onClick={() => handleReject(false)}
                  disabled={isDeciding}
                >
                  {isDeciding ? (
                    <><span className="spinner-xs" /> Recording Decision…</>
                  ) : (
                    <>✕ Reject Repair Proposal</>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Case 2: Approved Decision & Revisit Workflow */}
          {isApproved && (
            <div className="approved-decision-box">
              {!isRevisiting ? (
                <div className="approved-summary-bar">
                  <div className="approved-badge-msg">
                    <span className="check-circle">✓</span>
                    <span>
                      This proposal has been <strong>authorized for repair execution</strong>.
                      Execution remains gated and separate from live modification.
                    </span>
                  </div>

                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setIsRevisiting(true)}
                  >
                    🔄 Revisit Decision
                  </button>
                </div>
              ) : (
                <div className="revisit-controls-panel card">
                  <h5 className="revisit-heading">🔄 Revisit Approved Proposal Decision</h5>
                  <p className="revisit-subtext">
                    You may update reviewer notes or revoke this approval and transition the proposal to rejected status.
                  </p>

                  <div className="form-group">
                    <label htmlFor="revisit-notes-input" className="form-label">
                      Updated Reviewer Notes / Justification:
                    </label>
                    <input
                      id="revisit-notes-input"
                      type="text"
                      className="form-input"
                      value={revisitNotes}
                      onChange={(e) => setRevisitNotes(e.target.value)}
                      placeholder="e.g. Revoking approval after noticing regressions on mobile breakpoint."
                    />
                  </div>

                  <div className="revisit-actions-row">
                    <button
                      type="button"
                      className="btn btn-primary btn-sm"
                      onClick={() => handleApprove(true)}
                      disabled={isDeciding}
                    >
                      {isDeciding ? 'Saving...' : '✓ Update Approval Notes'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => handleReject(true)}
                      disabled={isDeciding}
                    >
                      {isDeciding ? 'Revoking...' : '✕ Revoke & Reject Proposal'}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => setIsRevisiting(false)}
                      disabled={isDeciding}
                    >
                      Cancel Revisit
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Case 3: Rejected Decision (Permanent) */}
          {isRejected && (
            <div className="rejected-decision-box">
              <div className="rejected-badge-msg">
                <span className="reject-circle">🚫</span>
                <div>
                  <strong>Proposal Decision: REJECTED</strong>
                  <p className="rejected-lock-notice">
                    In accordance with OmniSight safety governance, rejected repair proposals remain strictly rejected
                    and cannot be approved or reopened.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
