import React, { useState } from 'react';
import { constructDemoUrl } from '../services/api';

const VIEWPORT_OPTIONS = [
  { id: 'desktop', label: '🖥️ Desktop', desc: '1280x800 Chromium Desktop' },
  { id: 'tablet', label: '📱 Tablet', desc: '768x1024 iPad Touch Emulation' },
  { id: 'mobile', label: '📲 Mobile', desc: '375x667 iPhone Touch Emulation' },
];

export default function InspectionForm({ onSubmit, isLoading }) {
  const [url, setUrl] = useState(() => constructDemoUrl('', 'clean'));
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
    setValidationError('');
  };

  return (
    <section className="card inspection-form-section">
      <div className="card-header">
        <h2 className="card-title">Initiate Website Inspection</h2>
        <p className="card-description">
          Select target viewports and enter a website URL to dispatch an automated inspection through the OmniSight pipeline.
        </p>
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
              placeholder="https://example.com or http://127.0.0.1:8080/index.html"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
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
