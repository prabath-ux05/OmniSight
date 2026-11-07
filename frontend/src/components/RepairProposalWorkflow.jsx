import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchGitHubConfig,
  fetchRunProposals,
  generateProposalPatch,
  submitProposalPR,
} from '../services/api';

/**
 * FindingRepairWorkflow
 * 
 * Specialized single-finding workflow used within EvidenceSection.
 * Allows inspecting the self-healed locator candidate, creating a reviewable proposal,
 * generating a minimal unified diff against source code, requiring explicit human
 * approval, and submitting a pull request (live or simulated dry-run).
 */
export function FindingRepairWorkflow({ finding, runId, repair }) {
  // GitHub configuration state
  const [githubConfig, setGithubConfig] = useState(null);
  const [isConfigLoading, setIsConfigLoading] = useState(false);

  // Proposal state
  const [proposal, setProposal] = useState(null);
  const [isProposing, setIsProposing] = useState(false);
  const [proposalError, setProposalError] = useState('');

  // Patch generation state
  const [targetFile, setTargetFile] = useState('tests/e2e/test_checkout.py');
  const [isPatching, setIsPatching] = useState(false);
  const [patchResult, setPatchResult] = useState(null);
  const [patchError, setPatchError] = useState('');

  // Approval and PR state
  const [userApproved, setUserApproved] = useState(false);
  const [isSimulated, setIsSimulated] = useState(true);
  const [isSubmittingPR, setIsSubmittingPR] = useState(false);
  const [prResult, setPrResult] = useState(null);
  const [prError, setPrError] = useState('');

  // Load GitHub integration config
  const loadConfig = useCallback(async () => {
    setIsConfigLoading(true);
    const res = await fetchGitHubConfig();
    if (res.ok && res.data) {
      setGithubConfig(res.data);
      if (res.data.is_configured) {
        setIsSimulated(false);
      } else {
        setIsSimulated(true);
      }
    }
    setIsConfigLoading(false);
  }, []);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  // When finding or repair changes, reset or generate proposal
  useEffect(() => {
    setProposal(null);
    setPatchResult(null);
    setPatchError('');
    setPrResult(null);
    setPrError('');
    setUserApproved(false);
  }, [finding?.finding_id, repair?.repaired]);

  // Handle Proposal Creation
  const handleCreateProposal = async () => {
    if (!runId || !finding?.finding_id) return;
    setIsProposing(true);
    setProposalError('');
    setPatchError('');
    setPrError('');

    const res = await fetchRunProposals(runId, {
      finding_id: finding.finding_id,
      target_file: targetFile.trim() || undefined,
    });

    if (res.ok && res.data) {
      const list = Array.isArray(res.data) ? res.data : [res.data];
      const matched = list.find((p) => p.finding_id === finding.finding_id) || list[0];
      if (matched) {
        setProposal(matched);
      } else {
        setProposalError('No repair proposal could be generated for this finding.');
      }
    } else {
      setProposalError(res.error || 'Failed to create repair proposal.');
    }
    setIsProposing(false);
  };

  // Handle Minimal Patch Generation
  const handleGeneratePatch = async () => {
    if (!runId || !proposal?.proposal_id || !targetFile.trim()) {
      setPatchError('A target file path is required to generate a safe patch.');
      return;
    }
    setIsPatching(true);
    setPatchError('');
    setPatchResult(null);

    const res = await generateProposalPatch(runId, proposal.proposal_id, targetFile.trim());
    if (res.ok && res.data) {
      if (res.data.success) {
        setPatchResult(res.data);
        setProposal((prev) => (prev ? { ...prev, status: 'locally_validated', patch_diff: res.data.diff, target_file: res.data.target_file } : prev));
      } else {
        setPatchError(res.data.error || 'Patch generation was rejected or failed.');
      }
    } else {
      setPatchError(res.error || 'Failed to generate patch.');
    }
    setIsPatching(false);
  };

  // Handle PR Submission with Approval Gate
  const handleSubmitPR = async () => {
    if (!userApproved) {
      setPrError('Submission blocked: You must check the explicit approval checkbox before submitting.');
      return;
    }
    if (!runId || !proposal?.proposal_id) return;

    setIsSubmittingPR(true);
    setPrError('');

    const res = await submitProposalPR(runId, proposal.proposal_id, {
      userApproved: true,
      targetFile: targetFile.trim() || undefined,
      simulate: isSimulated,
    });

    if (res.ok && res.data) {
      const isOk = res.data.success ?? (res.data.status === 'created' || res.data.status === 'simulated');
      if (isOk) {
        setPrResult(res.data);
        setProposal((prev) => (prev ? {
          ...prev,
          status: 'remotely_submitted',
          branch_name: res.data.branch_name,
          pr_url: res.data.pr_url,
          pr_number: res.data.pr_number,
        } : prev));
      } else {
        setPrError(res.data.error || 'Pull request creation failed.');
      }
    } else {
      setPrError(res.error || 'Pull request submission failed.');
    }
    setIsSubmittingPR(false);
  };

  if (!repair || !repair.best_locator) {
    return null;
  }

  const status = proposal?.status || 'proposed';

  const getStatusBadge = () => {
    switch (status) {
      case 'remotely_submitted':
        return <span className="badge badge-status-submitted">🚀 Remotely Submitted</span>;
      case 'locally_validated':
        return <span className="badge badge-status-validated">✓ Locally Validated</span>;
      case 'rejected':
        return <span className="badge badge-status-rejected">✕ Rejected</span>;
      case 'proposed':
      default:
        return <span className="badge badge-status-proposed">📝 Proposed</span>;
    }
  };

  return (
    <div className="proposal-workflow-card">
      <div className="proposal-header">
        <div className="proposal-title-group">
          <span className="proposal-icon">🔄</span>
          <div>
            <h4 className="proposal-title">Safe Repair Proposal &amp; GitHub Pull Request</h4>
            <p className="proposal-subtitle">
              Convert verified locator candidate into a structured reviewable proposal, generate a non-destructive unified diff, and prepare a GitHub PR with explicit approval.
            </p>
          </div>
        </div>
        <div className="proposal-status-container">
          {getStatusBadge()}
        </div>
      </div>

      {/* GitHub Integration Config Status Badge */}
      <div className="github-status-strip">
        <span className="github-status-label">GitHub Integration:</span>
        {isConfigLoading ? (
          <span className="github-status-value">Checking configuration...</span>
        ) : githubConfig?.is_configured ? (
          <span className="github-status-value github-configured">
            ✓ Configured ({githubConfig.repo_owner}/{githubConfig.repo_name} &bull; base: <code>{githubConfig.base_branch}</code> &bull; token: <code>{githubConfig.masked_token}</code>)
          </span>
        ) : (
          <span className="github-status-value github-unconfigured">
            ⚠️ Credentials not set in environment &mdash; Simulation mode available (safe offline dry-run)
          </span>
        )}
      </div>

      {/* Step 1: Create Reviewable Proposal */}
      {!proposal ? (
        <div className="proposal-step-box">
          <div className="proposal-step-header">
            <strong>Step 1: Generate Reviewable Repair Proposal</strong>
          </div>
          <p className="proposal-step-text">
            Transforms locator candidate <code>{repair.best_locator}</code> and DOM validation evidence into a formal audit record.
          </p>
          {proposalError && (
            <div className="alert alert-error proposal-alert">
              <span>{proposalError}</span>
            </div>
          )}
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleCreateProposal}
            disabled={isProposing}
          >
            {isProposing ? 'Generating Proposal...' : 'Create Reviewable Proposal'}
          </button>
        </div>
      ) : (
        <div className="proposal-details-box">
          {/* Proposal Summary Details */}
          <div className="proposal-meta-grid">
            <div className="meta-row">
              <span className="meta-key">Proposal ID:</span>
              <code className="meta-val">{proposal.proposal_id}</code>
            </div>
            <div className="meta-row">
              <span className="meta-key">Original Selector:</span>
              <code className="meta-val meta-val-strike">{proposal.original_selector}</code>
            </div>
            <div className="meta-row">
              <span className="meta-key">Proposed Locator:</span>
              <code className="meta-val meta-val-highlight">{proposal.proposed_locator}</code>
            </div>
            <div className="meta-row">
              <span className="meta-key">Confidence &amp; Validation:</span>
              <span className="meta-val">
                {Math.round((proposal.confidence || 0) * 100)}% &bull; Snapshot Matches: {proposal.validation_evidence?.matches ?? 1}
                {proposal.validation_evidence?.live_verified ? ' &bull; Live Fresh-Page Verified ✓' : ''}
              </span>
            </div>
            <div className="meta-row">
              <span className="meta-key">Rationale:</span>
              <span className="meta-val">{proposal.rationale}</span>
            </div>
          </div>

          {/* Step 2: Safe Patch Generation */}
          <div className="proposal-patch-section">
            <h5 className="patch-section-title">Step 2: Generate Safe Minimal Diff</h5>
            <p className="patch-section-desc">
              Specify the test or application file containing the broken locator. Path traversal is rejected and OmniSight internal files are strictly protected. Diffs are generated purely in memory (read-only).
            </p>

            <div className="patch-input-group">
              <label htmlFor="target-file-input" className="patch-input-label">
                Target File (Workspace Relative):
              </label>
              <div className="patch-input-row">
                <input
                  id="target-file-input"
                  type="text"
                  className="input patch-file-input"
                  value={targetFile}
                  onChange={(e) => setTargetFile(e.target.value)}
                  placeholder="e.g. tests/e2e/test_checkout.py"
                  disabled={isPatching || status === 'remotely_submitted'}
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleGeneratePatch}
                  disabled={isPatching || !targetFile.trim() || status === 'remotely_submitted'}
                >
                  {isPatching ? 'Generating Diff...' : 'Generate Minimal Diff'}
                </button>
              </div>
            </div>

            {patchError && (
              <div className="alert alert-error proposal-alert">
                <strong>Patch Error:</strong> {patchError}
              </div>
            )}

            {patchResult && patchResult.diff && (
              <div className="diff-preview-box">
                <div className="diff-header">
                  <span className="diff-title">Unified Diff Preview (Minimal Patch):</span>
                  <span className="diff-filename">{patchResult.target_file}</span>
                </div>
                <pre className="diff-text">
                  {patchResult.diff.split('\n').map((line, idx) => {
                    let lineClass = 'diff-line-normal';
                    if (line.startsWith('+') && !line.startsWith('+++')) lineClass = 'diff-line-add';
                    else if (line.startsWith('-') && !line.startsWith('---')) lineClass = 'diff-line-del';
                    else if (line.startsWith('@@')) lineClass = 'diff-line-hunk';
                    else if (line.startsWith('---') || line.startsWith('+++')) lineClass = 'diff-line-file';
                    return (
                      <div key={idx} className={`diff-line ${lineClass}`}>
                        {line}
                      </div>
                    );
                  })}
                </pre>
              </div>
            )}
          </div>

          {/* Step 3: Human Approval Gate & Pull Request Submission */}
          <div className="proposal-pr-section">
            <h5 className="pr-section-title">Step 3: Explicit Human Approval &amp; Pull Request</h5>

            {status !== 'remotely_submitted' ? (
              <>
                <div className="approval-gate-box">
                  <div className="approval-checkbox-row">
                    <input
                      id="approval-checkbox"
                      type="checkbox"
                      className="approval-checkbox"
                      checked={userApproved}
                      onChange={(e) => setUserApproved(e.target.checked)}
                      disabled={isSubmittingPR}
                    />
                    <label htmlFor="approval-checkbox" className="approval-checkbox-label">
                      <strong>Explicit Approval:</strong> I have reviewed the proposed locator candidate and diff preview, and explicitly authorize creating a repair branch and submitting a GitHub Pull Request.
                    </label>
                  </div>

                  <div className="simulation-toggle-row">
                    <label className="simulation-label">
                      <input
                        type="checkbox"
                        checked={isSimulated}
                        onChange={(e) => setIsSimulated(e.target.checked)}
                        disabled={isSubmittingPR}
                      />
                      <span>Simulate Pull Request (Dry-run without writing to remote repository)</span>
                    </label>
                  </div>
                </div>

                {prError && (
                  <div className="alert alert-error proposal-alert">
                    <strong>Submission Error:</strong> {prError}
                  </div>
                )}

                <div className="pr-action-row">
                  <button
                    type="button"
                    className="btn btn-primary btn-sm btn-submit-pr"
                    onClick={handleSubmitPR}
                    disabled={!userApproved || isSubmittingPR}
                    title={!userApproved ? 'You must explicitly check the approval box first.' : 'Submit Pull Request to GitHub'}
                  >
                    {isSubmittingPR
                      ? 'Submitting to GitHub...'
                      : isSimulated
                      ? '✓ Approve & Submit (Simulated PR)'
                      : '✓ Approve & Create GitHub Pull Request'}
                  </button>
                  {!userApproved && (
                    <span className="approval-notice">
                      ⚠️ Approval required before any branch or PR is created.
                    </span>
                  )}
                </div>
              </>
            ) : (
              <div className="pr-success-box">
                <div className="pr-success-header">
                  <span className="pr-success-icon">{prResult?.simulated || prResult?.status === 'simulated' ? '🔬' : '🎉'}</span>
                  <div>
                    <h6 className="pr-success-title">
                      {prResult?.simulated || prResult?.status === 'simulated'
                        ? 'Simulated Pull Request (Dry-Run Only — No Remote Changes Made)'
                        : 'GitHub Pull Request Successfully Created!'}
                    </h6>
                    <p className="pr-success-branch">
                      Branch: <code>{prResult?.branch_name || proposal.branch_name}</code>
                    </p>
                  </div>
                </div>

                <div className="pr-success-links">
                  {prResult?.pr_url && prResult?.pr_number && (
                    <a
                      href={prResult.pr_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary btn-sm pr-external-link"
                    >
                      View GitHub Pull Request #{prResult.pr_number} ↗
                    </a>
                  )}
                  {(prResult?.simulated || prResult?.status === 'simulated') && (
                    <span className="badge badge-simulated">Dry-Run Simulation Active &bull; No Remote Repository Modified</span>
                  )}
                </div>

                <p className="pr-success-msg">{prResult?.message}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * RunProposalsDashboard
 *
 * Full-featured Human-in-the-Loop review and approval dashboard for all repair proposals
 * associated with an inspection run.
 * Connects with POST /api/v1/proposals/{proposal_id}/approve, /reject, and
 * POST /api/v1/runs/{run_id}/proposals.
 * Enforces strict separation between Review Approval, Patch Execution, and Visual Verification.
 */
export function RunProposalsDashboard({
  run,
  findings = [],
  proposals = [],
  isLoading = false,
  onRefreshProposals,
  onApprove,
  onReject,
  onCreateProposal,
}) {
  const [decisionNotes, setDecisionNotes] = useState({});
  const [actionInProgress, setActionInProgress] = useState({});
  const [filterStatus, setFilterStatus] = useState('ALL');

  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedFindingId, setSelectedFindingId] = useState('');
  const [proposedChangeText, setProposedChangeText] = useState('');
  const [prUrl, setPrUrl] = useState('');
  const [prNumber, setPrNumber] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState('');

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

  const formatTime = (isoString) => {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      return isNaN(date.getTime()) ? isoString : date.toLocaleString();
    } catch {
      return isoString;
    }
  };

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

      <div className="governance-banner">
        <span className="governance-icon">⚖️</span>
        <div className="governance-text">
          <strong>Human-in-the-Loop Governance:</strong> Approving a proposal records human authorization.
          Execution (patch application) and Visual Verification remain distinct stages and are not claimed as verified upon approval.
        </div>
      </div>

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
                <div className="proposal-card-header">
                  <div className="proposal-title-group">
                    <span className="proposal-id-tag">Proposal: <code>{proposal.proposal_id}</code></span>
                    {proposal.finding_id && (
                      <span className="proposal-finding-tag">
                        Target Finding: <code>{proposal.finding_id}</code>
                      </span>
                    )}
                  </div>

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

                <div className="proposal-body">
                  <h4 className="proposal-body-title">Proposed Patch / Remediation</h4>
                  <pre className="patch-diff-box">
                    <code>{proposal.proposed_change}</code>
                  </pre>
                </div>

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

/**
 * Default Export: RepairProposalWorkflow
 * Dispatches to FindingRepairWorkflow if called with finding and repair (inside EvidenceSection),
 * otherwise renders the RunProposalsDashboard for the full run review & approval tab.
 */
export default function RepairProposalWorkflow(props) {
  if (props.finding && props.repair) {
    return <FindingRepairWorkflow {...props} />;
  }
  return <RunProposalsDashboard {...props} />;
}
