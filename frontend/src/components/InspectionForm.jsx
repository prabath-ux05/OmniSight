import React, { useState } from 'react';
import { DEMO_STATES, constructDemoUrl, DEFAULT_DEMO_BASE_URL } from '../services/api';

const VIEWPORT_OPTIONS = [
  { id: 'desktop', label: '🖥️ Desktop', desc: '1280x800 Chromium Desktop' },
  { id: 'tablet', label: '📱 Tablet', desc: '768x1024 iPad Touch Emulation' },
  { id: 'mobile', label: '📲 Mobile', desc: '375x667 iPhone Touch Emulation' },
];

export default function InspectionForm({ onSubmit, isLoading }) {
  const [url, setUrl] = useState(() => constructDemoUrl('', 'clean'));
  const [selectedDemoState, setSelectedDemoState] = useState('clean');
  const [selectedViewports, setSelectedViewports] = useState(['desktop']);
  const [validationError, setValidationError] = useState('');

  const toggleViewport = (vpId) => {
    setSelectedViewports((prev) => {
      if (prev.includes(vpId)) {
        if (prev.length <= 1) return prev; // At least one viewport must stay active
        return prev.filter((id) => id !== vpId);
      }
      return [...prev, vpId];
    });
  };

  const handleSelectDemoState = (stateId) => {
    setSelectedDemoState(stateId);
    const newUrl = constructDemoUrl(url || DEFAULT_DEMO_BASE_URL, stateId);
    setUrl(newUrl);
    setValidationError('');
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = url.trim();
    if (!trimmed) {
      setValidationError('Please enter a target website URL.');
      return;
    }
    if (!trimmed.startsWith('http://') && !trimmed.startsWith('https://')) {
      setValidationError('URL must start with http:// or https://');
      return;
    }
    if (!selectedViewports || selectedViewports.length === 0) {
      setValidationError('Please select at least one viewport to inspect.');
      return;
    }
    setValidationError('');
    onSubmit(trimmed, selectedViewports);
  };

  const handlePreset = (presetUrl) => {
    setUrl(presetUrl);
    setSelectedDemoState(null);
    setValidationError('');
  };

  return (
    <section className="card inspection-form-section">
      <div className="card-header">
        <h2 className="card-title">Initiate Website Inspection</h2>
        <p className="card-description">
          Select target demo inspection state and viewports, or enter a custom URL to dispatch an automated inspection through the OmniSight pipeline.
        </p>
      </div>

      <div className="demo-state-selector-group">
        <div className="demo-state-header">
          <span className="demo-state-label">Demo Target State:</span>
          <span className="demo-state-hint">Deterministic Playwright defect harness</span>
        </div>
        <div className="demo-state-pills">
          {DEMO_STATES.map((ds) => {
            const isActive = selectedDemoState === ds.id;
            return (
              <button
                key={ds.id}
                type="button"
                className={`btn btn-sm ${isActive ? 'btn-demo-active' : 'btn-secondary'}`}
                onClick={() => handleSelectDemoState(ds.id)}
                disabled={isLoading}
                title={ds.description}
              >
                {ds.label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="viewport-selector-group">
        <div className="viewport-header">
          <span className="viewport-label">Target Viewports:</span>
          <span className="viewport-hint">Playwright device &amp; touch emulation (multi-select)</span>
        </div>
        <div className="viewport-pills">
          {VIEWPORT_OPTIONS.map((vp) => {
            const isSelected = selectedViewports.includes(vp.id);
            return (
              <button
                key={vp.id}
                type="button"
                className={`btn btn-sm ${isSelected ? 'btn-viewport-active' : 'btn-secondary'}`}
                onClick={() => toggleViewport(vp.id)}
                disabled={isLoading}
                title={vp.desc}
                aria-pressed={isSelected}
              >
                {vp.label} {isSelected && '✓'}
              </button>
            );
          })}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="form-layout">
        <div className="input-group">
          <label htmlFor="target-url-input" className="input-label">
            Target Inspection URL
          </label>
          <div className="input-row">
            <input
              id="target-url-input"
              type="text"
              className={`text-input ${validationError ? 'input-invalid' : ''}`}
              placeholder="http://127.0.0.1:8080/index.html?defect=overflow"
              value={url}
              onChange={(e) => {
                const val = e.target.value;
                setUrl(val);
                // Check if user typed a known defect param
                const matched = DEMO_STATES.find((ds) => {
                  if (ds.id === 'clean' && (val.includes('state=clean') || val.includes('baseline=true'))) return true;
                  if (ds.id === 'overflow' && val.includes('defect=overflow')) return true;
                  if (ds.id === 'missing' && (val.includes('defect=missing') || val.includes('defect=missing_element'))) return true;
                  if (ds.id === 'image' && (val.includes('defect=image') || val.includes('defect=broken_image'))) return true;
                  if (ds.id === 'all' && (val.includes('defects=all') || val.includes('state=corrupted'))) return true;
                  return false;
                });
                setSelectedDemoState(matched ? matched.id : null);
                if (validationError) setValidationError('');
              }}
              disabled={isLoading}
              maxLength={2048}
            />
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isLoading || !url.trim()}
            >
              {isLoading ? (
                <>
                  <span className="spinner-sm"></span>
                  <span>Initiating...</span>
                </>
              ) : (
                'Start Inspection'
              )}
            </button>
          </div>
          {validationError && (
            <p className="field-error-text" role="alert">{validationError}</p>
          )}
        </div>
        <div className="preset-row">
          <span className="preset-label">Other samples:</span>
          <button
            type="button"
            className="btn-link"
            onClick={() => handlePreset('http://127.0.0.1:8000/')}
            disabled={isLoading}
          >
            Local API (http://127.0.0.1:8000/)
          </button>
          <span className="preset-separator">&bull;</span>
          <button
            type="button"
            className="btn-link"
            onClick={() => handlePreset('https://example.com')}
            disabled={isLoading}
          >
            https://example.com
          </button>
        </div>
      </form>
    </section>
  );
}
