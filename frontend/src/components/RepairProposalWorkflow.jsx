import React, { useState } from 'react';

/**
 * RepairProposalWorkflow component.
 *
 * Implements the Human-in-the-Loop repair review & approval interface.
 * Connects with POST /api/v1/proposals/{proposal_id}/approve and /reject,
 * and POST /api/v1/runs/{run_id}/proposals.
 *
 * Enforces strict separation between Review Approval, Patch Execution, and Visual Verification.
 */
export default function RepairProposalWorkflow({
  run,
  findings = [],
  proposals = [],
  isLoading = false,
  onRefreshProposals,
  onApprove,
  onReject,
  onCreateProposal,
}) {
  // State for active proposal review decision notes
  const [decisionNotes, setDecisionNotes] = useState({});
  const [actionInProgress, setActionInProgress] = useState({}); // { [proposalId]: 'approving' | 'rejecting' }
  const [filterStatus, setFilterStatus] = useState('ALL');

  // State for new proposal creation drawer/form
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedFindingId, setSelectedFindingId] = useState('');
  const [proposedChangeText, setProposedChangeText] = useState('');
  const [prUrl, setPrUrl] = useState('');
  const [prNumber, setPrNumber] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState('');

  // ---------------------------------------------------------------------------
  // Helper: Status Badge Styling
  // ---------------------------------------------------------------------------
  const getApprovalBadgeClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'approved':
        return 'badge-success';
      case 'rejected':
        return 'badge-danger';
      case 'pending':
      default:
        return 'badge-warning';
    }
  };

  const getExecutionBadgeClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'applied':
        return 'badge-success';
      case 'applying':
        return 'badge-warning';
      case 'failed':
        return 'badge-danger';
      case 'unapplied':
      default:
        return 'badge-neutral';
    }
  };

  const getVerificationBadgeClass = (status) => {
    switch (status?.toLowerCase()) {
      case 'verified_success':
        return 'badge-success';
      case 'verified_failure':
        return 'badge-danger';
      case 'inconclusive':
        return 'badge-warning';
      case 'unverified':
      default:
        return 'badge-neutral';
    }
  };

  // ---------------------------------------------------------------------------
  // Action Handlers
  // ---------------------------------------------------------------------------
  const handleApproveClick = async (proposalId) => {
    if (actionInProgress[proposalId]) return;
    const notes = decisionNotes[proposalId] || '';
    setActionInProgress((prev) => ({ ...prev, [proposalId]: 'approving' }));
    try {
      await onApprove(proposalId, notes);
      setDecisionNotes((prev) => ({ ...prev, [proposalId]: '' }));
    } finally {
      setActionInProgress((prev) => ({ ...prev, [proposalId]: null }));
    }
  };

  const handleRejectClick = async (proposalId) => {
    if (actionInProgress[proposalId]) return;
    const notes = decisionNotes[proposalId] || '';
    setActionInProgress((prev) => ({ ...prev, [proposalId]: 'rejecting' }));
    try {
      await onReject(proposalId, notes);
      setDecisionNotes((prev) => ({ ...prev, [proposalId]: '' }));
    } finally {
      setActionInProgress((prev) => ({ ...prev, [proposalId]: null }));
    }
  };

  const handleCreateSubmit = async (e) => {
    e.preventDefault();
    if (!proposedChangeText.trim()) {
      setCreateError('Proposed change content or patch description is required.');
      return;
    }
    setCreateError('');
    setIsCreating(true);

    const payload = {
      finding_id: selectedFindingId || null,
      proposed_change: proposedChangeText.trim(),
      github_pr_url: prUrl.trim() || null,
      github_pr_number: prNumber ? parseInt(prNumber, 10) : null,
    };

    try {
      const ok = await onCreateProposal(run.run_id, payload);
      if (ok) {
        setProposedChangeText('');
        setSelectedFindingId('');
        setPrUrl('');
        setPrNumber('');
        setShowCreateForm(false);
      }
    } finally {
      setIsCreating(false);
    }
  };

  // Format timestamp helper
  const formatTime = (isoString) => {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      return isNaN(date.getTime()) ? isoString : date.toLocaleString();
    } catch {
      return isoString;
    }
  };

  // Filter proposals
  const filteredProposals = proposals.filter((p) => {
    if (filterStatus === 'ALL') return true;
    return p.approval_status?.toUpperCase() === filterStatus;
  });

  if (!run) {
    return (
      <section className="card proposals-workflow-section">
        <div className="card-header">
          <h2 className="card-title">Self-Healing Repair Proposals</h2>
        </div>
        <div className="empty-state">
          <div className="empty-state-icon">🛡️</div>
          <p className="empty-state-title">No Active Inspection Run Selected</p>
          <p className="empty-state-text">
            Please initiate an inspection run or select one from the Run History to view and review repair proposals.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section className="card proposals-workflow-section">
      {/* Header and Control Bar */}
      <div className="card-header-with-actions">
        <div>
          <h2 className="card-title">Repair Approval Workflow</h2>
          <p className="card-description">
            Human-in-the-Loop review for run <code className="finding-id-highlight">{run.run_id}</code>
            {run.url && <span> ({run.url})</span>}.
          </p>
        </div>

        <div className="proposal-header-buttons">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefreshProposals}
            disabled={isLoading}
            title="Refresh proposals for this run"
          >
            {isLoading ? 'Refreshing...' : '↻ Refresh Proposals'}
          </button>
          <button
            type="button"
            className={`btn btn-sm ${showCreateForm ? 'btn-secondary' : 'btn-primary'}`}
            onClick={() => setShowCreateForm((prev) => !prev)}
          >
            {showCreateForm ? 'Cancel Proposal Creation' : '+ Draft Repair Proposal'}
          </button>
        </div>
      </div>

      {/* Governance Banner */}
      <div className="governance-banner">
        <span className="governance-icon">⚖️</span>
        <div className="governance-text">
          <strong>Human-in-the-Loop Governance:</strong> Approving a proposal records human authorization.
          Execution (patch application) and Visual Verification remain distinct stages and are not claimed as verified upon approval.
        </div>
      </div>

      {/* Proposal Creation Drawer/Form */}
      {showCreateForm && (
        <form onSubmit={handleCreateSubmit} className="proposal-create-form card">
          <h3 className="form-section-title">Draft New Self-Healing Repair Proposal</h3>
          <p className="form-section-description">
            Attach a proposed code, CSS patch, or selector fix to an existing finding.
          </p>

          {createError && (
            <div className="alert-box alert-error" style={{ marginBottom: '1rem' }}>
              <span>{createError}</span>
            </div>
          )}

          <div className="form-group">
            <label htmlFor="proposal-finding-select" className="form-label">Associated Finding:</label>
            <select
              id="proposal-finding-select"
              className="form-input"
              value={selectedFindingId}
              onChange={(e) => setSelectedFindingId(e.target.value)}
            >
              <option value="">-- No specific finding (Global Run Patch) --</option>
              {findings.map((f) => (
                <option key={f.finding_id} value={f.finding_id}>
                  {f.finding_id} &mdash; [{f.category || 'Defect'}] {f.description?.substring(0, 50)}...
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label htmlFor="proposal-change-textarea" className="form-label">Proposed Change / Patch Diff *:</label>
            <textarea
              id="proposal-change-textarea"
              className="form-input form-textarea"
              rows={4}
              placeholder="e.g.: .hero-banner { max-width: 100vw; overflow-x: hidden; } /* Prevents horizontal scroll on 375px mobile breakpoint */"
              value={proposedChangeText}
              onChange={(e) => setProposedChangeText(e.target.value)}
              required
            />
          </div>

          <div className="form-row-2">
            <div className="form-group">
              <label htmlFor="proposal-pr-url" className="form-label">GitHub Pull Request URL (optional):</label>
              <input
                id="proposal-pr-url"
                type="url"
                className="form-input"
                placeholder="https://github.com/prabath-ux05/OmniSight/pull/12"
                value={prUrl}
                onChange={(e) => setPrUrl(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label htmlFor="proposal-pr-number" className="form-label">GitHub PR # (optional):</label>
              <input
                id="proposal-pr-number"
                type="number"
                className="form-input"
                placeholder="12"
                value={prNumber}
                onChange={(e) => setPrNumber(e.target.value)}
              />
            </div>
          </div>

          <div className="form-actions">
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isCreating}
            >
              {isCreating ? 'Creating Proposal...' : 'Submit Proposal'}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowCreateForm(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Filter Tabs */}
      <div className="proposals-filter-bar">
        <span className="filter-label">Filter by Review Status:</span>
        <div className="filter-pills">
          {['ALL', 'PENDING', 'APPROVED', 'REJECTED'].map((st) => (
            <button
              key={st}
              type="button"
              className={`filter-pill ${filterStatus === st ? 'filter-pill-active' : ''}`}
              onClick={() => setFilterStatus(st)}
            >
              {st} ({st === 'ALL' ? proposals.length : proposals.filter((p) => p.approval_status?.toUpperCase() === st).length})
            </button>
          ))}
        </div>
      </div>

      {/* Proposals List or Empty State */}
      {filteredProposals.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">💡</div>
          <p className="empty-state-title">No Repair Proposals Found</p>
          <p className="empty-state-text">
            {proposals.length === 0
              ? 'No repair proposals have been generated yet for this inspection run. Click "+ Draft Repair Proposal" above to create one.'
              : `No proposals with status '${filterStatus}'. Try selecting 'ALL'.`}
          </p>
        </div>
      ) : (
        <div className="proposals-list">
          {filteredProposals.map((proposal) => {
            const isPending = proposal.approval_status === 'pending';
            const isApproved = proposal.approval_status === 'approved';
            const isRejected = proposal.approval_status === 'rejected';
            const inProgressAction = actionInProgress[proposal.proposal_id];

            return (
              <div
                key={proposal.proposal_id}
                className={`proposal-card ${
                  isApproved ? 'proposal-approved' : isRejected ? 'proposal-rejected' : 'proposal-pending'
                }`}
              >
                {/* Proposal Card Header */}
                <div className="proposal-card-header">
                  <div className="proposal-title-group">
                    <span className="proposal-id-tag">Proposal: <code>{proposal.proposal_id}</code></span>
                    {proposal.finding_id && (
                      <span className="proposal-finding-tag">
                        Target Finding: <code>{proposal.finding_id}</code>
                      </span>
                    )}
                  </div>

                  {/* Tri-stage Badges */}
                  <div className="proposal-badge-row">
                    <div className="badge-wrapper" title="Human Review / Governance Status">
                      <span className="badge-caption">Review:</span>
                      <span className={`badge ${getApprovalBadgeClass(proposal.approval_status)}`}>
                        {proposal.approval_status?.toUpperCase()}
                      </span>
                    </div>

                    <div className="badge-wrapper" title="Patch Application Execution Status">
                      <span className="badge-caption">Execution:</span>
                      <span className={`badge ${getExecutionBadgeClass(proposal.execution_status)}`}>
                        {proposal.execution_status?.toUpperCase()}
                      </span>
                    </div>

                    <div className="badge-wrapper" title="Post-Repair Re-inspection Verification Status">
                      <span className="badge-caption">Verification:</span>
                      <span className={`badge ${getVerificationBadgeClass(proposal.verification_status)}`}>
                        {proposal.verification_status?.toUpperCase()}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Proposed Change / Diff */}
                <div className="proposal-body">
                  <h4 className="proposal-body-title">Proposed Patch / Remediation</h4>
                  <pre className="patch-diff-box">
                    <code>{proposal.proposed_change}</code>
                  </pre>
                </div>

                {/* Metadata & Timestamps */}
                <div className="proposal-meta-row">
                  <div className="proposal-meta-item">
                    <span className="meta-label">Created:</span>
                    <span className="meta-value">{formatTime(proposal.created_at)}</span>
                  </div>
                  {proposal.updated_at && (
                    <div className="proposal-meta-item">
                      <span className="meta-label">Last Decision:</span>
                      <span className="meta-value">{formatTime(proposal.updated_at)}</span>
                    </div>
                  )}
                  {proposal.github_pr_url && (
                    <div className="proposal-meta-item">
                      <span className="meta-label">Pull Request:</span>
                      <a
                        href={proposal.github_pr_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-link btn-link-sm"
                      >
                        PR #{proposal.github_pr_number || 'Link'} ↗
                      </a>
                    </div>
                  )}
                </div>

                {/* Review Action Controls */}
                <div className="proposal-review-section">
                  {isPending ? (
                    <div className="review-action-container">
                      <div className="review-notes-input-wrapper">
                        <label htmlFor={`review-notes-${proposal.proposal_id}`} className="review-notes-label">
                          Reviewer Notes / Justification (optional):
                        </label>
                        <input
                          id={`review-notes-${proposal.proposal_id}`}
                          type="text"
                          className="form-input form-input-sm"
                          placeholder="e.g. Verified styling against design system and approved for merge."
                          value={decisionNotes[proposal.proposal_id] || ''}
                          onChange={(e) =>
                            setDecisionNotes((prev) => ({
                              ...prev,
                              [proposal.proposal_id]: e.target.value,
                            }))
                          }
                          disabled={Boolean(inProgressAction)}
                        />
                      </div>

                      <div className="review-buttons-group">
                        <button
                          type="button"
                          className="btn btn-success btn-sm"
                          onClick={() => handleApproveClick(proposal.proposal_id)}
                          disabled={Boolean(inProgressAction)}
                          title="Authorize repair patch execution"
                        >
                          {inProgressAction === 'approving' ? 'Approving...' : '✓ Approve Proposal'}
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          onClick={() => handleRejectClick(proposal.proposal_id)}
                          disabled={Boolean(inProgressAction)}
                          title="Reject repair proposal"
                        >
                          {inProgressAction === 'rejecting' ? 'Rejecting...' : '✕ Reject Proposal'}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="review-decision-recorded">
                      <span className="decision-icon">
                        {isApproved ? '✅' : '🚫'}
                      </span>
                      <span className="decision-text">
                        <strong>Decision Recorded:</strong> Proposal was {proposal.approval_status.toUpperCase()} on {formatTime(proposal.updated_at)}.
                      </span>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
