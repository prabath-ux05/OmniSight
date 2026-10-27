import React, { useState } from 'react';
import { getArtifactUrl } from '../services/api';
import RepairProposalWorkflow from './RepairProposalWorkflow';

export default function EvidenceSection({
  finding,
  runId,
  repair,
  isRepairing,
  repairError,
  onSuggestRepair,
}) {
  const [imageError, setImageError] = useState(false);
  const [isImageLoading, setIsImageLoading] = useState(true);
  const [copied, setCopied] = useState(false);

  if (!finding) {
    return (
      <section className="card evidence-section">
        <div className="card-header">
          <h2 className="card-title">Inspection Evidence &amp; Visual Artifacts</h2>
        </div>
        <div className="empty-state">
          <p className="empty-state-text">
            Select a finding from the Defect Findings list to inspect its captured screenshot and DOM snapshot evidence.
          </p>
        </div>
      </section>
    );
  }

  const evidence = finding.evidence || {};
  const isMock = finding.source === 'mock' || (finding.description && finding.description.includes('[MOCK]'));
  const isEligible = finding.category === 'missing_visible_element';

  // Calculate real HTTP-accessible artifact URLs via backend /api/v1/artifacts
  // Extract basename whether path uses forward slash or backslash (Windows)
  const extractFilename = (p, fallback) => {
    if (!p) return null;
    const clean = p.replace(/\\/g, '/');
    const name = clean.substring(clean.lastIndexOf('/') + 1);
    return name || fallback;
  };

  const screenshotFilename = extractFilename(evidence.screenshot_path, 'before.png');
  const domFilename = extractFilename(evidence.dom_snapshot_path, 'dom.html');

  const accessibleScreenshotUrl = (runId && screenshotFilename)
    ? getArtifactUrl(runId, screenshotFilename)
    : null;

  const accessibleDomUrl = (runId && domFilename)
    ? getArtifactUrl(runId, domFilename)
    : null;

  const handleCopy = (text) => {
    if (!text) return;
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(text).catch(() => {});
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStrategyLabel = (strategy) => {
    switch (strategy) {
      case 'data_attribute':
        return 'Data Attribute (data-testid / data-cy)';
      case 'stable_id':
        return 'Stable Semantic ID';
      case 'accessible_role_name':
        return 'Accessible Role / Name';
      case 'unique_text':
        return 'Unique Text Content';
      case 'semantic_css':
        return 'Semantic Tag + Class';
      case 'hierarchical':
        return 'Hierarchical Scope';
      default:
        return strategy || 'Heuristic';
    }
  };

  return (
    <section className="card evidence-section">
      <div className="card-header">
        <div>
          <h2 className="card-title">Evidence &amp; Artifact Details</h2>
          <p className="card-description">
            Associated visual evidence for finding <code className="finding-id-highlight">{finding.finding_id}</code>.
          </p>
        </div>
      </div>

      <div className="evidence-grid">
        {/* Screenshot Column */}
        <div className="evidence-column">
          <div className="evidence-header-row">
            <h3 className="evidence-subtitle">Visual Screenshot Artifact</h3>
            {accessibleScreenshotUrl && !imageError && (
              <a
                href={accessibleScreenshotUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-link btn-link-sm"
              >
                Open Full Size ↗
              </a>
            )}
          </div>

          <div className="evidence-preview-box">
            {accessibleScreenshotUrl && !imageError ? (
              <div className="screenshot-container">
                {isImageLoading && (
                  <div className="screenshot-loading-spinner">
                    <span className="spinner-sm"></span>
                    <span>Loading screenshot artifact...</span>
                  </div>
                )}
                <img
                  src={accessibleScreenshotUrl}
                  alt={`Screenshot artifact for run ${runId}`}
                  className={`screenshot-img ${isImageLoading ? 'screenshot-img-hidden' : ''}`}
                  onLoad={() => setIsImageLoading(false)}
                  onError={() => {
                    setIsImageLoading(false);
                    setImageError(true);
                  }}
                />
              </div>
            ) : (
              <div className="screenshot-fallback-box">
                <div className="fallback-icon">🖼️</div>
                <h4 className="fallback-title">Screenshot File Not Yet On Disk</h4>
                <p className="fallback-description">
                  {evidence.screenshot_path ? (
                    <>
                      Expected at: <code>{evidence.screenshot_path}</code>
                      <br />
                      The Browser Agent has not yet written this screenshot file to disk, or the file was cleared.
                    </>
                  ) : (
                    'No screenshot artifact path was recorded for this finding.'
                  )}
                </p>
                <span className="fallback-hint">
                  Run the integrated Browser Agent pipeline to capture live viewport screenshots.
                </span>
              </div>
            )}
          </div>
        </div>

        {/* DOM & Metadata Column */}
        <div className="evidence-column">
          <h3 className="evidence-subtitle">DOM Snapshot &amp; Element Context</h3>
          <div className="evidence-meta-card">
            <div className="meta-row">
              <span className="meta-key">DOM Snapshot:</span>
              <div className="meta-val-with-action">
                <code className="meta-val">{evidence.dom_snapshot_path || 'None recorded'}</code>
                {accessibleDomUrl && (
                  <a
                    href={accessibleDomUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn btn-secondary btn-xs"
                    title="View captured DOM HTML in a new tab"
                  >
                    View HTML ↗
                  </a>
                )}
              </div>
            </div>

            <div className="meta-row">
              <span className="meta-key">CSS / DOM Selector:</span>
              <code className="meta-val">{finding.selector || 'Global layout scope'}</code>
            </div>

            <div className="meta-row">
              <span className="meta-key">Defect Category:</span>
              <span className="meta-val">{finding.category || 'N/A'}</span>
            </div>

            <div className="meta-row">
              <span className="meta-key">Confidence Score:</span>
              <span className="meta-val">
                {typeof finding.confidence === 'number'
                  ? `${Math.round(finding.confidence * 100)}%`
                  : 'Not provided'}
              </span>
            </div>

            <div className="meta-row">
              <span className="meta-key">Source Engine:</span>
              <span className="meta-val">
                {isMock ? (
                  <span className="badge badge-source-mock">[MOCK] Test Fixture</span>
                ) : (
                  <span>{finding.source ? `Engine: ${finding.source}` : 'DOM / Vision Detector'}</span>
                )}
              </span>
            </div>
          </div>

          <div className="artifact-storage-note">
            <span className="note-title">Artifact Serving Architecture:</span>
            <p className="note-body">
              Local filesystem paths are securely served over HTTP at <code>/api/v1/artifacts/{'{run_id}'}/{'{filename}'}</code>. Path traversal is strictly protected, ensuring only verified run artifacts are accessible.
            </p>
          </div>
        </div>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Self-Healing Locator Engine Section */}
      {/* ------------------------------------------------------------------ */}
      <div className="repair-panel">
        <div className="repair-panel-header">
          <div>
            <h3 className="repair-panel-title">
              <span className="repair-title-icon">⚡</span> Self-Healing Locator Repair Engine
            </h3>
            <p className="repair-panel-subtitle">
              Generates resilient alternative locators (data attributes, semantic IDs, accessible roles, unique text) and verifies uniqueness against captured DOM.
            </p>
          </div>

          {onSuggestRepair && (
            <div className="repair-action-btn-group">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => onSuggestRepair(false)}
                disabled={isRepairing}
              >
                {isRepairing ? (
                  <>
                    <span className="spinner-xs"></span> Analyzing...
                  </>
                ) : repair ? (
                  'Re-suggest (Snapshot)'
                ) : (
                  'Suggest Repair'
                )}
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onSuggestRepair(true)}
                disabled={isRepairing}
                title="Synthesize candidates from snapshot and verify against live fresh page"
              >
                ⚡ Verify on Live Page
              </button>
            </div>
          )}
        </div>


        {/* Loading State */}
        {isRepairing && (
          <div className="repair-loading-box">
            <span className="spinner-md"></span>
            <div className="repair-loading-text">
              <strong>Analyzing Captured DOM Snapshot...</strong>
              <span>Generating candidate selectors, ranking deterministic heuristics, and verifying match uniqueness against DOM.</span>
            </div>
          </div>
        )}

        {/* Error Alert */}
        {!isRepairing && repairError && (
          <div className="alert alert-error repair-error-alert" role="alert">
            <div className="alert-content">
              <strong>Repair Error:</strong> {repairError}
            </div>
            {onSuggestRepair && (
              <button
                type="button"
                className="btn btn-secondary btn-xs"
                onClick={onSuggestRepair}
              >
                Retry
              </button>
            )}
          </div>
        )}

        {/* Non-eligible Category Notice */}
        {!isRepairing && !repair && !isEligible && (
          <div className="repair-info-box">
            <span className="repair-info-icon">ℹ️</span>
            <div>
              <p className="repair-info-title">Self-Healing Locator Repair Scope</p>
              <p className="repair-info-desc">
                Autonomous locator repair is active for <code>missing_visible_element</code> findings. For <code>{finding.category || 'layout'}</code> findings, visual layout or resource remediation is recommended.
              </p>
            </div>
          </div>
        )}

        {/* Idle Eligible State (Before user clicks Suggest Repair) */}
        {!isRepairing && !repair && isEligible && !repairError && (
          <div className="repair-prompt-box">
            <div className="repair-prompt-content">
              <h4 className="repair-prompt-title">Broken or Missing Element Locator Detected</h4>
              <p className="repair-prompt-desc">
                Original selector: <code>{finding.selector || 'Not specified'}</code>. Click <strong>Suggest Repair</strong> to let OmniSight's deterministic engine inspect <code>{evidence.dom_snapshot_path || 'the captured DOM'}</code>, discover target elements, generate alternative locators, and validate them.
              </p>
            </div>
            {onSuggestRepair && (
              <div className="repair-action-btn-group">
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => onSuggestRepair(false)}
                >
                  Suggest Repair
                </button>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => onSuggestRepair(true)}
                  title="Synthesize candidates from snapshot and verify against live fresh page"
                >
                  ⚡ Suggest &amp; Verify Live
                </button>
              </div>
            )}
          </div>
        )}

        {/* Repair Results State */}
        {!isRepairing && repair && (
          <div className="repair-result-card">
            {/* Status & Best Candidate Summary */}
            <div className="repair-result-header">
              <div className="repair-status-badge-group">
                {repair.repaired ? (
                  <span className="badge badge-repair-success-large">
                    ✓ VERIFIED REPAIR CANDIDATE FOUND
                  </span>
                ) : (
                  <span className="badge badge-repair-failed-large">
                    ⚠️ NO VALID CANDIDATE FOUND
                  </span>
                )}
                {repair.strategy && (
                  <span className="badge badge-strategy">
                    Strategy: {getStrategyLabel(repair.strategy)}
                  </span>
                )}
                {typeof repair.score === 'number' && (
                  <span className="badge badge-score">
                    Score: {Math.round(repair.score * 100)}%
                  </span>
                )}
                {repair.validation && (
                  <span
                    className={`badge ${repair.validation.is_valid ? 'badge-validation-pass' : 'badge-validation-fail'}`}
                    title="Verified uniquely in captured DOM snapshot"
                  >
                    Snapshot DOM: {repair.validation.matches ?? 0} {repair.validation.is_valid ? '(Unique ✓)' : '(Non-unique ✗)'}
                  </span>
                )}
                {repair.live_verification?.attempted && (
                  <span
                    className={`badge ${repair.live_verification.is_verified ? 'badge-validation-pass' : 'badge-validation-fail'}`}
                    title={repair.live_verification.validation_message}
                  >
                    Live Page: {repair.live_verification.matches ?? 0} {repair.live_verification.is_verified ? '(Live Verified ✓)' : '(Unresolved ✗)'}
                  </span>
                )}
              </div>
            </div>

            {/* Best Locator Box */}
            <div className="repair-best-box">
              <div className="repair-best-header">
                <span className="repair-best-label">Recommended Locator:</span>
                {repair.best_locator && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-xs btn-copy"
                    onClick={() => handleCopy(repair.best_locator)}
                    title="Copy recommended locator to clipboard"
                  >
                    {copied ? '✓ Copied!' : 'Copy Locator'}
                  </button>
                )}
              </div>
              <code className="repair-best-code">
                {repair.best_locator || 'None — No candidate resolved uniquely in DOM'}
              </code>
            </div>

            {/* Fresh Live-Page Verification Details (Requirement 2) */}
            {repair.live_verification?.attempted && (
              <div
                className={`repair-live-box ${repair.live_verification.is_verified ? 'repair-live-success' : 'repair-live-warning'}`}
              >
                <div className="repair-live-header">
                  <span className="repair-live-title">
                    {repair.live_verification.is_verified
                      ? '✓ Live Fresh-Page Verification: Passed'
                      : '⚠️ Live Fresh-Page Verification: Failed'}
                  </span>
                  <span className="repair-live-matches">
                    Live matches: {repair.live_verification.matches}
                  </span>
                </div>
                <p className="repair-live-message">{repair.live_verification.validation_message}</p>
                {repair.live_verification.target_url && (
                  <div className="repair-live-url">
                    <span className="meta-key">Target URL:</span>
                    <code>{repair.live_verification.target_url}</code>
                  </div>
                )}
              </div>
            )}


            {/* Explanation / Reason */}
            <div className="repair-explanation-box">
              <span className="explanation-label">Engine Analysis &amp; Explanation:</span>
              <p className="explanation-text">{repair.reason || 'No explanation provided.'}</p>
            </div>

            {/* Ranked Candidates List */}
            {Array.isArray(repair.candidates) && repair.candidates.length > 0 && (
              <div className="repair-candidates-section">
                <h4 className="repair-candidates-title">
                  Ranked Locator Candidates ({repair.candidates.length})
                </h4>
                <div className="repair-candidates-list">
                  {repair.candidates.map((cand, idx) => {
                    const isBest = cand.selector === repair.best_locator;
                    const isValid = cand.validation?.is_valid;
                    return (
                      <div
                        key={idx}
                        className={`repair-candidate-item ${isBest ? 'repair-candidate-best' : ''}`}
                      >
                        <div className="candidate-rank">#{idx + 1}</div>
                        <div className="candidate-details">
                          <div className="candidate-selector-row">
                            <code className="candidate-selector">{cand.selector}</code>
                            {isBest && <span className="candidate-best-tag">Recommended</span>}
                          </div>
                          <div className="candidate-meta-row">
                            <span className="candidate-strategy">{getStrategyLabel(cand.strategy)}</span>
                            <span className="candidate-score">Score: {Math.round(cand.score * 100)}%</span>
                            <span
                              className={`candidate-validation ${isValid ? 'validation-valid' : 'validation-invalid'}`}
                            >
                              DOM Matches: {cand.validation?.matches ?? 0} {isValid ? '✓' : '✗'}
                            </span>
                          </div>
                        </div>
                        <button
                          type="button"
                          className="btn btn-secondary btn-xs"
                          onClick={() => handleCopy(cand.selector)}
                          title="Copy candidate selector"
                        >
                          Copy
                        </button>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Safe Repair Proposal & GitHub PR Workflow (Batch Milestone) */}
            <RepairProposalWorkflow
              finding={finding}
              runId={runId}
              repair={repair}
            />

            {/* Safety & Architecture Notice (Requirement 6) */}
            <div className="repair-disclaimer-box">
              <span className="disclaimer-badge">Engine Notice</span>
              <p className="disclaimer-text">
                Candidate locators are suggested and validated strictly against the captured DOM snapshot (<code>{evidence.dom_snapshot_path || 'snapshot'}</code>). Locators are not automatically applied to application source code.
              </p>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
