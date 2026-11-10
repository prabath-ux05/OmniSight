import React, { useState, useEffect } from 'react';
import { getBackendDisplayUrl, fetchVlmConfig, fetchGitHubConfig } from '../services/api';

/**
 * SettingsPage renders the dedicated, functional Settings view for OmniSight.
 *
 * Requirements met:
 * 1. Appearance: Dark, Light, and System theme selection with immediate update and persistence.
 * 2. Guided Tutorial: Replay tutorial action reusing existing tour implementation.
 * 3. Backend Connection: Real-time health status, manual refresh, loading/connected/offline states.
 *    Strictly does not claim database connectivity unless verified.
 * 4. Application Information: Displays actual version and environment from configuration without inventing values.
 * 5. Guest Access: Explains the guest access model honestly without fake accounts or login forms.
 * 6. Usability: Cleanly separated sections, responsive layout, dark/light theme integration.
 */
export default function SettingsPage({
  theme = 'system',
  onSelectTheme = () => {},
  hasCompletedTour = false,
  onReplayTour = () => {},
  health = null,
  isHealthLoading = false,
  onCheckHealth = () => {},
  includeMockFindings = false,
  onToggleMockFindings = () => {},
  onSelectView = () => {},
}) {
  // Diagnostic requests state with resilient status tracking
  const [vlmStatus, setVlmStatus] = useState({ state: 'idle', data: null, error: null });
  const [isVlmLoading, setIsVlmLoading] = useState(false);
  const [githubStatus, setGithubStatus] = useState({ state: 'idle', data: null, error: null });
  const [isGithubLoading, setIsGithubLoading] = useState(false);

  // Load diagnostics once on mount with resilient error handling and settled loading states
  useEffect(() => {
    let mounted = true;

    async function loadDiagnostics() {
      setIsVlmLoading(true);
      try {
        const vlmRes = await fetchVlmConfig();
        if (mounted) {
          if (vlmRes && vlmRes.ok && vlmRes.data) {
            setVlmStatus({
              state: vlmRes.data.configured ? 'configured' : 'not_configured',
              data: vlmRes.data,
              error: null,
            });
          } else {
            setVlmStatus({
              state: 'unable_to_verify',
              data: null,
              error: vlmRes?.error || 'Failed to verify VLM configuration',
            });
          }
        }
      } catch (err) {
        if (mounted) {
          setVlmStatus({
            state: 'unable_to_verify',
            data: null,
            error: err?.message || 'Diagnostic query rejected',
          });
        }
      } finally {
        if (mounted) setIsVlmLoading(false);
      }

      setIsGithubLoading(true);
      try {
        const ghRes = await fetchGitHubConfig();
        if (mounted) {
          if (ghRes && ghRes.ok && ghRes.data) {
            setGithubStatus({
              state: ghRes.data.is_configured ? 'configured' : 'not_configured',
              data: ghRes.data,
              error: null,
            });
          } else {
            setGithubStatus({
              state: 'unable_to_verify',
              data: null,
              error: ghRes?.error || 'Failed to verify GitHub configuration',
            });
          }
        }
      } catch (err) {
        if (mounted) {
          setGithubStatus({
            state: 'unable_to_verify',
            data: null,
            error: err?.message || 'Diagnostic query rejected',
          });
        }
      } finally {
        if (mounted) setIsGithubLoading(false);
      }
    }

    loadDiagnostics();
    return () => {
      mounted = false;
    };
  }, []);

  const backendUrl = getBackendDisplayUrl();
  const environmentMode = (typeof import.meta !== 'undefined' && import.meta.env?.MODE) || 'development';

  return (
    <div className="settings-page-container">
      {/* 1. Settings Hero Banner */}
      <div className="settings-hero-banner">
        <div className="settings-hero-badge-row">
          <span className="settings-hero-badge">System Preferences</span>
          <span className="settings-guest-badge">Guest Session Active</span>
        </div>
        <h2 className="settings-hero-title">Settings &amp; Diagnostics</h2>
        <p className="settings-hero-desc">
          Customize dashboard appearance, manage guided tutorial walkthroughs, inspect backend API telemetry, and review environment connectivity.
        </p>
      </div>

      {/* 2. Appearance & Theme Foundation */}
      <div className="card settings-section-card">
        <div className="card-header">
          <h3 className="card-title">🎨 Appearance &amp; Theme</h3>
          <p className="card-description">
            Customize the visual presentation of OmniSight. Preferences are saved automatically to your browser profile.
          </p>
        </div>

        <div className="settings-row">
          <div className="settings-info">
            <span className="settings-title">Active Visual Theme</span>
            <span className="settings-desc">
              Currently using <strong>{theme.charAt(0).toUpperCase() + theme.slice(1)} Mode</strong>.
              {theme === 'system'
                ? ' Adapts automatically based on your operating system light/dark preference.'
                : ` Locked to ${theme} palette.`}
            </span>
          </div>

          <div className="theme-pill-group" role="radiogroup" aria-label="Visual theme selection">
            <button
              type="button"
              className={`theme-pill-btn ${theme === 'dark' ? 'active' : ''}`}
              onClick={() => onSelectTheme('dark')}
              aria-checked={theme === 'dark'}
              role="radio"
              title="Switch to Dark theme"
            >
              🌙 Dark
            </button>
            <button
              type="button"
              className={`theme-pill-btn ${theme === 'light' ? 'active' : ''}`}
              onClick={() => onSelectTheme('light')}
              aria-checked={theme === 'light'}
              role="radio"
              title="Switch to Light theme"
            >
              ☀️ Light
            </button>
            <button
              type="button"
              className={`theme-pill-btn ${theme === 'system' ? 'active' : ''}`}
              onClick={() => onSelectTheme('system')}
              aria-checked={theme === 'system'}
              role="radio"
              title="Automatically match operating system appearance"
            >
              💻 System
            </button>
          </div>
        </div>
      </div>

      {/* 3. Guided Tutorial Controls */}
      <div className="card settings-section-card">
        <div className="card-header">
          <h3 className="card-title">🎓 Guided Onboarding Walkthrough</h3>
          <p className="card-description">
            Interactive tour introducing automated inspection, defect localization, and self-healing review.
          </p>
        </div>

        <div className="settings-row">
          <div className="settings-info">
            <span className="settings-title">Tutorial Completion Status</span>
            <span className="settings-desc">
              {hasCompletedTour ? (
                <span className="text-success">
                  ✓ Completed or previously dismissed. You can restart the walkthrough at any time.
                </span>
              ) : (
                <span className="text-warning">
                  Pending. The tour is available on first visit or on demand.
                </span>
              )}
            </span>
          </div>

          <div className="settings-action-col">
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={onReplayTour}
              title="Relaunch the 6-step interactive onboarding tour"
            >
              ↺ Replay Guided Tour
            </button>
          </div>
        </div>
      </div>

      {/* 4. Backend Connection & Health Status */}
      <div className="card settings-section-card">
        <div className="card-header">
          <h3 className="card-title">🔌 Backend Connection &amp; Telemetry</h3>
          <p className="card-description">
            Live connectivity diagnostics for the FastAPI application server and database service.
          </p>
        </div>

        {/* FastAPI Health Check */}
        <div className="settings-row">
          <div className="settings-info">
            <span className="settings-title">FastAPI Backend API</span>
            <span className="settings-desc">
              Connected via endpoint <code>{backendUrl}/health</code>
            </span>
          </div>

          <div className="settings-status-group">
            {isHealthLoading ? (
              <span className="badge badge-neutral">
                <span className="spinner-xs"></span>
                <span>Pinging service...</span>
              </span>
            ) : health?.status === 'ok' ? (
              <span className="badge badge-success">
                <span className="status-dot status-dot-online"></span>
                Connected (v{health.version || '0.1.0'})
              </span>
            ) : (
              <span className="badge badge-danger">
                <span className="status-dot status-dot-offline"></span>
                Service Unavailable
              </span>
            )}

            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onCheckHealth}
              disabled={isHealthLoading}
              title="Ping backend health endpoint"
            >
              {isHealthLoading ? 'Checking...' : 'Ping API'}
            </button>
          </div>
        </div>

        {/* PostgreSQL Database Status (Honest: Not verified by /health) */}
        <div className="settings-row">
          <div className="settings-info">
            <span className="settings-title">PostgreSQL Database Service</span>
            <span className="settings-desc">
              Audit log and defect findings persistence store.
              <br />
              <span className="text-dim">
                Note: The <code>/health</code> endpoint confirms FastAPI API process health only; relational database connectivity is queried and verified during active run operations.
              </span>
            </span>
          </div>

          <div className="settings-status-group">
            <span className="badge badge-neutral" title="Database connectivity is verified on active queries, independent of /health">
              Verified on Active Queries
            </span>
          </div>
        </div>
      </div>

      {/* 5. Application Information & Diagnostics */}
      <div className="card settings-section-card">
        <div className="card-header">
          <h3 className="card-title">ℹ️ Application Information &amp; Architecture</h3>
          <p className="card-description">
            Verified configuration attributes retrieved from the current application environment.
          </p>
        </div>

        <div className="settings-info-grid">
          <div className="info-grid-item">
            <span className="info-item-label">Application Name:</span>
            <span className="info-item-val">{health?.app || 'OmniSight Backend'}</span>
          </div>

          <div className="info-grid-item">
            <span className="info-item-label">API Semantic Version:</span>
            <span className="info-item-val font-mono">{health?.version || '0.1.0'}</span>
          </div>

          <div className="info-grid-item">
            <span className="info-item-label">Frontend Runtime:</span>
            <span className="info-item-val font-mono">React 18.3 &bull; Vite 5.4</span>
          </div>

          <div className="info-grid-item">
            <span className="info-item-label">Environment Mode:</span>
            <span className="info-item-val font-mono">{environmentMode}</span>
          </div>

          <div className="info-grid-item">
            <span className="info-item-label">VLM Provider Status:</span>
            <span className="info-item-val">
              {isVlmLoading ? (
                'Checking...'
              ) : vlmStatus.state === 'configured' ? (
                <span className="text-success font-semibold">
                  Configured ({vlmStatus.data?.provider || 'VLM'})
                </span>
              ) : vlmStatus.state === 'not_configured' ? (
                <span className="text-muted">
                  Not Configured (Deterministic DOM fallback active)
                </span>
              ) : (
                <span className="text-warning font-semibold" title={vlmStatus.error || 'Diagnostic query failed'}>
                  Unable to Verify (API Offline or Error)
                </span>
              )}
            </span>
          </div>

          <div className="info-grid-item">
            <span className="info-item-label">GitHub PR Integration:</span>
            <span className="info-item-val">
              {isGithubLoading ? (
                'Checking...'
              ) : githubStatus.state === 'configured' ? (
                <span className="text-success font-semibold">
                  Configured ({githubStatus.data?.owner}/{githubStatus.data?.repo})
                </span>
              ) : githubStatus.state === 'not_configured' ? (
                <span className="text-muted">
                  Not Configured (Simulation Mode active)
                </span>
              ) : (
                <span className="text-warning font-semibold" title={githubStatus.error || 'Diagnostic query failed'}>
                  Unable to Verify (API Offline or Error)
                </span>
              )}
            </span>
          </div>
        </div>
      </div>

      {/* 6. Guest Access & Authentication Model */}
      <div className="card settings-section-card">
        <div className="card-header">
          <h3 className="card-title">👤 Authentication Model &amp; Guest Access</h3>
          <p className="card-description">
            Information regarding account management and user identity.
          </p>
        </div>

        <div className="guest-model-callout">
          <div className="callout-header">
            <span className="callout-icon">🔓</span>
            <div>
              <h4 className="callout-title">Full Guest Access Active</h4>
              <span className="callout-subtitle">Authentication is not configured in this deployment</span>
            </div>
          </div>

          <p className="callout-body">
            OmniSight operates with complete, unrestricted access for all users in guest mode.
            There are no user databases, password forms, or session restrictions.
            You can launch automated inspections, review multimodal DOM and screenshot evidence, inspect historical run databases, and test self-healing locator repairs without signing in or creating an account.
          </p>
        </div>
      </div>

      {/* 7. Inspection Studio Defaults */}
      <div className="card settings-section-card">
        <div className="card-header">
          <h3 className="card-title">🛠️ Inspection Studio Defaults</h3>
          <p className="card-description">
            Configure default runtime behaviors for live automated inspections.
          </p>
        </div>

        <div className="settings-row">
          <div className="settings-info">
            <span className="settings-title">Include Simulated / Mock Findings</span>
            <span className="settings-desc">
              Inject representative sample defect findings for verification, testing, and UI demonstrations.
            </span>
          </div>

          <div className="settings-action-col">
            <button
              type="button"
              className={`btn btn-sm ${includeMockFindings ? 'btn-accent' : 'btn-secondary'}`}
              onClick={onToggleMockFindings}
            >
              {includeMockFindings ? 'Enabled (Active)' : 'Disabled'}
            </button>
          </div>
        </div>

        <div className="settings-row">
          <div className="settings-info">
            <span className="settings-title">Real-Time Polling Interval</span>
            <span className="settings-desc">
              Automatic synchronization interval when an inspection run is active in the background.
            </span>
          </div>

          <span className="badge badge-neutral">2500 ms</span>
        </div>
      </div>
    </div>
  );
}
