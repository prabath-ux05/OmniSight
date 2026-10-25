import React, { useState } from 'react';
import { getArtifactUrl } from '../services/api';

export default function EvidenceSection({ finding, runId }) {
  const [imageError, setImageError] = useState(false);
  const [isImageLoading, setIsImageLoading] = useState(true);

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

  // Calculate real HTTP-accessible artifact URLs via backend /api/v1/artifacts
  // Do NOT treat local filesystem path (e.g. artifacts/run_xxx/before.png) as a browser URL
  const screenshotFilename = evidence.screenshot_path ? 'before.png' : null;
  const domFilename = evidence.dom_snapshot_path ? 'dom.html' : null;

  const accessibleScreenshotUrl = (runId && screenshotFilename)
    ? getArtifactUrl(runId, screenshotFilename)
    : null;

  const accessibleDomUrl = (runId && domFilename)
    ? getArtifactUrl(runId, domFilename)
    : null;

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
                  'Multimodal Vision Model'
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
    </section>
  );
}
