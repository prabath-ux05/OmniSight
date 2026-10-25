import React from 'react';

export default function EvidenceSection({ finding, runId }) {
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
        <div className="evidence-column">
          <h3 className="evidence-subtitle">Visual Screenshot Artifact</h3>
          <div className="evidence-preview-box">
            {evidence.screenshot_path ? (
              <div className="screenshot-placeholder">
                <div className="screenshot-icon">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                    <rect width="18" height="18" x="3" y="3" rx="2" ry="2" />
                    <circle cx="9" cy="9" r="2" />
                    <path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21" />
                  </svg>
                </div>
                <p className="screenshot-filename">{evidence.screenshot_path}</p>
                <span className="screenshot-meta">Browser Agent Captured Viewport Frame</span>
              </div>
            ) : (
              <div className="evidence-empty-box">
                <p>No screenshot artifact recorded for this finding.</p>
              </div>
            )}
          </div>
        </div>

        <div className="evidence-column">
          <h3 className="evidence-subtitle">DOM Snapshot &amp; Element Context</h3>
          <div className="evidence-meta-card">
            <div className="meta-row">
              <span className="meta-key">DOM Snapshot:</span>
              <code className="meta-val">{evidence.dom_snapshot_path || 'None recorded'}</code>
            </div>

            <div className="meta-row">
              <span className="meta-key">CSS / DOM Selector:</span>
              <code className="meta-val">{finding.selector || 'Global / Not specified'}</code>
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
            <span className="note-title">Artifact Storage Location:</span>
            <p className="note-body">
              Evidence artifacts are saved locally in <code>artifacts/{runId || '<run_id>'}/</code> by the Browser Agent for automated inspection and self-healing verification.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
