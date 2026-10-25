import React, { useState } from 'react';

export default function InspectionForm({ onSubmit, isLoading }) {
  const [url, setUrl] = useState('');
  const [validationError, setValidationError] = useState('');

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
    setValidationError('');
    onSubmit(trimmed);
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
          Enter a web application URL to dispatch an automated inspection run through the OmniSight orchestration pipeline.
        </p>
      </div>
      <form onSubmit={handleSubmit} className="form-layout">
        <div className="input-group">
          <label htmlFor="target-url-input" className="input-label">
            Target Website URL
          </label>
          <div className="input-row">
            <input
              id="target-url-input"
              type="text"
              className={`text-input ${validationError ? 'input-invalid' : ''}`}
              placeholder="https://example.com or http://127.0.0.1:8000/"
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
          <span className="preset-label">Quick samples:</span>
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
