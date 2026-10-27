import React, { useState, useEffect, useCallback } from 'react';
import {
  fetchGitHubConfig,
  fetchRunProposals,
  generateProposalPatch,
  submitProposalPR,
} from '../services/api';

export default function RepairProposalWorkflow({ finding, runId, repair }) {
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
      // If real credentials exist, user can opt for live or simulated
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
        // Update proposal status locally to locally_validated
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
