import React from 'react';
import { useScrollReveal } from '../hooks/useScrollReveal';
import { useCursorGlow } from '../hooks/useCursorGlow';
import './HomePage.css';
import './surfaces.css';

/**
 * HomePage — Meridian Command Center
 * Batch 3 layout + Batch 4 motion design:
 * - Scroll-triggered section reveals (IntersectionObserver)
 * - Staggered pipeline and mosaic entrance animations
 * - Animated SVG telemetry graphic
 * - Interactive hover depth effects
 * All data strictly from real backend props.
 */
export default function HomePage({
  runsList = [],
  isRunsLoading = false,
  runsError = '',
  onRefreshRuns = () => {},
  currentRun = null,
  onSelectView = () => {},
  onSelectRun = () => {},
}) {
  // Scroll reveal refs for each major section
  const [heroRef,     heroVisible]     = useScrollReveal({ threshold: 0 });
  const [activeRef,   activeVisible]   = useScrollReveal({ threshold: 0.1 });
  const [pipeRef,     pipeVisible]     = useScrollReveal({ threshold: 0.12 });
  const [capRef,      capVisible]      = useScrollReveal({ threshold: 0.08 });
  const [activityRef, activityVisible] = useScrollReveal({ threshold: 0.08 });

  // Cursor-responsive glow for the hero and featured capability card
  const heroGlow    = useCursorGlow();
  const featuredGlow = useCursorGlow();

  const getStatusBadgeClass = (status) => {
    const s = typeof status === 'string' ? status.trim().toLowerCase() : '';
    switch (s) {
      case 'completed':  return 'badge-success';
      case 'failed':
      case 'error':
      case 'cancelled':  return 'badge-danger';
      case 'capturing':
      case 'analyzing':
      case 'repair_pending':
      case 'repairing':
      case 'verifying':  return 'badge-warning';
      case 'queued':
      default:           return 'badge-neutral';
    }
  };

  const getStatusVariant = (status) => {
    const s = typeof status === 'string' ? status.trim().toLowerCase() : '';
    if (s === 'completed') return 'success';
    if (['failed', 'error', 'cancelled'].includes(s)) return 'danger';
    if (['capturing', 'analyzing', 'repair_pending', 'repairing', 'verifying'].includes(s)) return 'warning';
    return 'neutral';
  };

  const formatTimestamp = (isoString) => {
    if (!isoString) return '—';
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) return isoString;
      return date.toLocaleString(undefined, {
        month: 'short', day: '2-digit',
        hour: '2-digit', minute: '2-digit',
      });
    } catch { return isoString; }
  };

  const recentRuns = Array.isArray(runsList) ? runsList.slice(0, 6) : [];
  const latestRun = recentRuns[0] || null;
  const latestStatus = latestRun?.status?.toLowerCase() || null;

  const PIPELINE_STAGES = [
    { id: 'capture',  label: 'Capture',  icon: '📸', desc: 'Headless browser' },
    { id: 'analyze',  label: 'Analyze',  icon: '🧠', desc: 'Vision model' },
    { id: 'diagnose', label: 'Diagnose', icon: '🔬', desc: 'DOM traversal' },
    { id: 'repair',   label: 'Repair',   icon: '🛠️', desc: 'Self-healing' },
    { id: 'verify',   label: 'Verify',   icon: '✅', desc: 'Before / After' },
  ];

  const getStageState = (stageId) => {
    if (!latestStatus) return 'idle';
    const statusMap = {
      'queued':         { active: 'capture',  done: [] },
      'capturing':      { active: 'capture',  done: [] },
      'analyzing':      { active: 'analyze',  done: ['capture'] },
      'repair_pending': { active: 'diagnose', done: ['capture', 'analyze'] },
      'repairing':      { active: 'repair',   done: ['capture', 'analyze', 'diagnose'] },
      'verifying':      { active: 'verify',   done: ['capture', 'analyze', 'diagnose', 'repair'] },
      'completed':      { active: null,       done: ['capture', 'analyze', 'diagnose', 'repair', 'verify'] },
      'failed':         { active: null,       done: [] },
    };
    const mapping = statusMap[latestStatus] || { active: null, done: [] };
    if (mapping.done.includes(stageId)) return 'done';
    if (mapping.active === stageId) return 'active';
    return 'idle';
  };

  return (
    <div className="home-view-container">

      {/* ===================================================================
          1. CINEMATIC HERO
      =================================================================== */}
      <section
        ref={(node) => { heroRef.current = node; heroGlow.ref.current = node; }}
        className={`home-hero reveal cursor-glow${heroVisible ? ' is-visible' : ''}`}
        aria-label="Welcome Banner"
        onMouseMove={heroGlow.onMouseMove}
        onMouseLeave={heroGlow.onMouseLeave}
      >
        <div className="home-hero-left">
          <div className="home-hero-eyebrow">
            <span className="hero-eyebrow-badge">
              <span className="badge-glow-dot" aria-hidden="true" />
              OmniSight Platform
            </span>
            <span className="hero-eyebrow-pill">
              <span aria-hidden="true">🛡️</span>
              Enterprise UI Reliability
            </span>
          </div>

          <h1 className="home-hero-title">
            Autonomous UI<br />
            <span className="hero-title-accent">Quality &amp; Self&#8209;Healing</span>
          </h1>

          <p className="home-hero-desc">
            OmniSight automatically inspects web applications for visual regressions,
            broken DOM elements, and responsive layout overflows using multimodal
            vision models. Generate robust self-healing proposals and govern code
            changes with pull request safety gates.
          </p>

          <div className="home-hero-actions">
            <button
              type="button"
              className="btn btn-primary home-hero-btn-primary"
              onClick={() => onSelectView('inspection')}
            >
              <span aria-hidden="true">🔍</span>
              Launch Live Inspection
              <span className="hero-btn-arrow" aria-hidden="true">→</span>
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => onSelectView('history')}
            >
              Inspection History
              {runsList.length > 0 && (
                <span className="hero-count-badge">{runsList.length}</span>
              )}
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => onSelectView('proposals')}
            >
              <span aria-hidden="true">🛡️</span>
              Repair Proposals
            </button>
          </div>
        </div>

        {/* Right column: animated telemetry graphic */}
        <div className="home-hero-visual" aria-hidden="true">
          <HeroTelemetryGraphic runCount={runsList.length} latestStatus={latestStatus} />
        </div>
      </section>

      {/* ===================================================================
          2. ACTIVE SESSION BANNER
      =================================================================== */}
      {currentRun && (
        <section
          ref={activeRef}
          className={`home-active-session reveal${activeVisible ? ' is-visible' : ''}`}
          aria-label="Active Inspection Session"
        >
          <div className="active-session-indicator">
            <span className="active-pulse" aria-hidden="true" />
            <span className="active-session-label">Active Session</span>
          </div>
          <div className="active-session-body">
            <div className="active-session-info">
              <span className="active-session-run-id">
                Run <code>{currentRun.run_id ? String(currentRun.run_id) : '—'}</code>
              </span>
              <span className="active-session-url" title={currentRun.url || ''}>
                {currentRun.url || '—'}
              </span>
            </div>
            <div className="active-session-actions">
              <span className={`badge ${getStatusBadgeClass(currentRun.status)}`}>
                {typeof currentRun.status === 'string' && currentRun.status.trim()
                  ? currentRun.status.trim().toUpperCase()
                  : 'UNKNOWN'}
              </span>
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => onSelectRun(currentRun)}
              >
                Open in Live Studio →
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => { onSelectRun(currentRun); onSelectView('proposals'); }}
              >
                🛡️ Repair Proposals →
              </button>
            </div>
          </div>
        </section>
      )}

      {/* ===================================================================
          3. INSPECTION PIPELINE VISUALIZATION
      =================================================================== */}
      <section
        ref={pipeRef}
        className={`home-pipeline reveal${pipeVisible ? ' is-visible' : ''}`}
        aria-label="Inspection Pipeline"
      >
        <div className="pipeline-header">
          <div>
            <h2 className="pipeline-title">AI Inspection Pipeline</h2>
            <p className="pipeline-subtitle">
              {latestRun
                ? `Latest run ${latestRun.run_id ? String(latestRun.run_id) : ''} · ${latestStatus?.toUpperCase() || 'UNKNOWN'}`
                : 'End-to-end automated inspection, diagnosis and self-healing'}
            </p>
          </div>
        </div>

        {/* pipeline-stages gets stagger class so each stage animates in sequence */}
        <div className={`pipeline-stages${pipeVisible ? ' pipe-stagger-active' : ''}`} role="list">
          {PIPELINE_STAGES.map((stage, i) => {
            const state = getStageState(stage.id);
            return (
              <React.Fragment key={stage.id}>
                <div
                  className={`pipeline-stage pipeline-stage--${state}`}
                  style={{ '--stage-index': i }}
                  role="listitem"
                  aria-label={`${stage.label}: ${state}`}
                >
                  <div className="pipeline-stage-icon" aria-hidden="true">
                    {stage.icon}
                  </div>
                  <div className="pipeline-stage-info">
                    <span className="pipeline-stage-label">{stage.label}</span>
                    <span className="pipeline-stage-desc">{stage.desc}</span>
                  </div>
                  {state === 'active' && (
                    <span className="pipeline-stage-active-dot" aria-hidden="true" />
                  )}
                </div>
                {i < PIPELINE_STAGES.length - 1 && (
                  <div
                    className={`pipeline-connector pipeline-connector--${state === 'done' ? 'done' : 'idle'}`}
                    aria-hidden="true"
                  />
                )}
              </React.Fragment>
            );
          })}
        </div>
      </section>

      {/* ===================================================================
          4. CAPABILITY MOSAIC
      =================================================================== */}
      <section
        ref={capRef}
        className={`home-capabilities reveal${capVisible ? ' is-visible' : ''}`}
        aria-label="Platform Capabilities"
      >
        <div className="capabilities-header">
          <h2 className="section-heading">Platform Capabilities</h2>
          <p className="section-hint">An end-to-end multimodal inspection, analysis, and self-healing lifecycle</p>
        </div>

        <div className={`capabilities-mosaic${capVisible ? ' mosaic-stagger-active' : ''}`}>

          {/* FEATURED: Large card — Multimodal Inspection */}
          <div
            className="cap-card cap-card--featured cap-card--inspect cursor-glow"
            ref={featuredGlow.ref}
            onMouseMove={featuredGlow.onMouseMove}
            onMouseLeave={featuredGlow.onMouseLeave}
          >
            <div className="cap-card-bg-graphic" aria-hidden="true">
              <svg viewBox="0 0 320 200" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <rect x="20" y="20" width="200" height="140" rx="6" fill="none" stroke="rgba(0,201,167,0.2)" strokeWidth="1.5"/>
                <rect x="20" y="20" width="200" height="22" rx="6" fill="rgba(0,201,167,0.08)" />
                <circle cx="34" cy="31" r="3.5" fill="rgba(0,201,167,0.4)" />
                <circle cx="46" cy="31" r="3.5" fill="rgba(245,166,35,0.4)" />
                <circle cx="58" cy="31" r="3.5" fill="rgba(167,139,250,0.3)" />
                <line x1="20" y1="52" x2="220" y2="52" stroke="rgba(0,201,167,0.08)" strokeWidth="1" />
                <rect x="30" y="60" width="120" height="8" rx="2" fill="rgba(255,255,255,0.06)" />
                <rect x="30" y="74" width="80" height="6" rx="2" fill="rgba(255,255,255,0.04)" />
                <rect x="30" y="86" width="140" height="40" rx="4" fill="rgba(0,201,167,0.05)" stroke="rgba(0,201,167,0.1)" strokeWidth="1"/>
                <rect x="30" y="134" width="60" height="16" rx="3" fill="rgba(0,201,167,0.15)" />
                <rect x="240" y="40" width="60" height="100" rx="5" fill="none" stroke="rgba(0,201,167,0.15)" strokeWidth="1" strokeDasharray="3 2"/>
                <rect x="246" y="52" width="48" height="6" rx="2" fill="rgba(255,255,255,0.04)"/>
                <rect x="246" y="62" width="30" height="4" rx="2" fill="rgba(255,255,255,0.03)"/>
                {/* Animated scan beam */}
                <line className="card-scan-beam" x1="20" y1="90" x2="220" y2="90" stroke="rgba(0,201,167,0.5)" strokeWidth="1" strokeDasharray="4 3"/>
              </svg>
            </div>
            <div className="cap-card-content">
              <div className="cap-card-icon-row">
                <div className="cap-icon-box cap-icon--teal">🌐</div>
                <div className="cap-card-tech-tags">
                  <span className="feature-tag">Playwright Headless</span>
                  <span className="feature-tag">Multi-Viewport</span>
                </div>
              </div>
              <h3 className="cap-card-title">Multimodal Website Inspection</h3>
              <p className="cap-card-desc">
                Headless browser automation drives deep navigation across desktop, tablet, and mobile
                viewport presets, capturing pixel-perfect full-page screenshots and structural DOM snapshots.
              </p>
              <button
                type="button"
                className="cap-card-action btn btn-primary btn-sm"
                onClick={() => onSelectView('inspection')}
              >
                Launch Inspection →
              </button>
            </div>
          </div>

          {/* TALL: Visual Defect Detection */}
          <div className="cap-card cap-card--tall cap-card--detect">
            <div className="cap-card-icon-row">
              <div className="cap-icon-box cap-icon--amber">🎯</div>
            </div>
            <h3 className="cap-card-title">Visual Defect Detection</h3>
            <p className="cap-card-desc">
              Advanced multimodal vision models identify layout overflows, missing interactive elements,
              and broken image assets with pinpoint bounding-box coordinates and confidence scores.
            </p>
            <div className="cap-card-tech-tags">
              <span className="feature-tag">Gemini VLM</span>
              <span className="feature-tag">Bounding Boxes</span>
            </div>
            <div className="cap-detect-visual" aria-hidden="true">
              <div className="detect-box detect-box--overflow">overflow</div>
              <div className="detect-box detect-box--missing">missing</div>
              <div className="detect-box detect-box--broken">broken img</div>
            </div>
          </div>

          {/* SMALL: DOM Analysis */}
          <div className="cap-card cap-card--small cap-card--dom">
            <div className="cap-icon-box cap-icon--violet">📐</div>
            <h3 className="cap-card-title">DOM &amp; Layout Analysis</h3>
            <p className="cap-card-desc">
              Deterministic DOM traversal inspects element geometries, scroll dimensions, and client
              rectangles to corroborate visual discrepancies directly against the live page tree.
            </p>
            <div className="cap-card-tech-tags">
              <span className="feature-tag">DOM Traversal</span>
              <span className="feature-tag">Client Rects</span>
            </div>
          </div>

          {/* SMALL: Repair Proposals (clickable) */}
          <div
            className="cap-card cap-card--small cap-card--repair"
            role="button"
            tabIndex={0}
            onClick={() => onSelectView('proposals')}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelectView('proposals'); }}
            style={{ cursor: 'pointer' }}
            title="Open Repair Proposals"
          >
            <div className="cap-icon-box cap-icon--teal">💡</div>
            <h3 className="cap-card-title">Evidence-Based Repair Proposals</h3>
            <p className="cap-card-desc">
              Synthesize resilient locator recommendations with minimal unified diff patches for
              automated test suite repair.
            </p>
            <div className="cap-card-tech-tags">
              <span className="feature-tag">Self-Healing</span>
              <span className="feature-tag">Unified Diff</span>
              <span className="btn-link btn-link-sm" style={{ marginLeft: 'auto' }}>Open →</span>
            </div>
          </div>

          {/* WIDE: Sandbox + Verification */}
          <div className="cap-card cap-card--wide cap-card--sandbox">
            <div className="cap-wide-left">
              <div className="cap-icon-box cap-icon--green">🔒</div>
              <h3 className="cap-card-title">Controlled Sandbox Repair</h3>
              <p className="cap-card-desc">
                Proposed repairs execute strictly within an isolated local sandbox. The live production
                website is never modified automatically.
              </p>
              <div className="cap-card-tech-tags">
                <span className="feature-tag">Local Sandbox</span>
                <span className="feature-tag">Live Site Protected</span>
              </div>
              <div className="cap-sandbox-detail" aria-hidden="true">
                <span className="cap-sandbox-step">
                  <span className="cap-sandbox-step-dot cap-sandbox-step-dot--amber" />
                  Propose
                </span>
                <span className="cap-sandbox-step-arrow">›</span>
                <span className="cap-sandbox-step">
                  <span className="cap-sandbox-step-dot cap-sandbox-step-dot--teal" />
                  Approve
                </span>
                <span className="cap-sandbox-step-arrow">›</span>
                <span className="cap-sandbox-step">
                  <span className="cap-sandbox-step-dot cap-sandbox-step-dot--green" />
                  Apply
                </span>
              </div>
            </div>
            <div className="cap-wide-divider" aria-hidden="true" />
            <div className="cap-wide-right">
              <div className="cap-icon-box cap-icon--violet">⚖️</div>
              <h3 className="cap-card-title">Before / After Verification</h3>
              <p className="cap-card-desc">
                Interactive side-by-side split views contrast original defect evidence against repaired
                post-patch rendering under identical viewports.
              </p>
              <div className="cap-card-tech-tags">
                <span className="feature-tag">Split-View</span>
                <span className="feature-tag">Interactive Slider</span>
              </div>
              <div className="cap-verify-split" aria-hidden="true">
                <span className="cap-verify-before">Before</span>
                <span className="cap-verify-after">After</span>
              </div>
            </div>
          </div>

        </div>
      </section>

      {/* ===================================================================
          5. RECENT ACTIVITY
      =================================================================== */}
      <section
        ref={activityRef}
        className={`home-activity reveal${activityVisible ? ' is-visible' : ''}`}
        aria-label="Recent Inspection Activity"
      >
        <div className="home-activity-header">
          <div>
            <h2 className="section-heading">Recent Activity</h2>
            <p className="section-hint">Recent automated inspection runs and defect detection history</p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefreshRuns}
            disabled={isRunsLoading}
            title="Refresh recent activity"
          >
            {isRunsLoading ? 'Refreshing…' : '↻ Refresh'}
          </button>
        </div>

        {runsError && (
          <div className="alert-box alert-error home-activity-error" role="alert">
            <span>Failed to load recent activity: {runsError}</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={onRefreshRuns}>
              Retry
            </button>
          </div>
        )}

        {isRunsLoading && runsList.length === 0 ? (
          /* Loading skeleton */
          <div className="activity-skeleton" aria-label="Loading recent activity…" aria-busy="true">
            {[1, 2, 3].map((n) => (
              <div key={n} className="activity-skeleton-row">
                <div className="skeleton-bar" />
                <div className="skeleton-line skeleton-line--wide" />
                <div className="skeleton-line skeleton-line--mid" />
                <div className="skeleton-line skeleton-line--short" />
              </div>
            ))}
          </div>
        ) : runsList.length === 0 ? (
          <div className="home-activity-empty">
            <div className="activity-empty-icon" aria-hidden="true">📋</div>
            <div className="activity-empty-text">
              <p className="empty-state-title">No Recent Inspection Activity</p>
              <p className="empty-state-text">
                No inspection runs found. Open the Live Inspection Studio to initiate your first automated run.
              </p>
            </div>
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => onSelectView('inspection')}
            >
              Launch Live Inspection Studio →
            </button>
          </div>
        ) : (
          <div className={`activity-stream${activityVisible ? ' stream-stagger-active' : ''}`}>
            {recentRuns.map((run, idx) => {
              const variant = getStatusVariant(run.status);
              return (
                <div
                  key={run.run_id || idx}
                  className={`activity-row activity-row--${variant}`}
                  style={{ '--row-index': idx }}
                >
                  <div className="activity-row-status" aria-hidden="true">
                    <div className={`activity-status-bar activity-bar--${variant}`} />
                  </div>
                  <div className="activity-row-main">
                    <div className="activity-run-id">
                      <span className="run-id-pill">{run.run_id ? String(run.run_id) : '—'}</span>
                      <span className={`badge ${getStatusBadgeClass(run.status)}`}>
                        {typeof run.status === 'string' && run.status.trim()
                          ? run.status.trim().toUpperCase()
                          : 'UNKNOWN'}
                      </span>
                    </div>
                    <div className="activity-run-url" title={run.url || ''}>
                      {run.url || '—'}
                    </div>
                  </div>
                  <div className="activity-row-time">
                    <span className="timestamp-cell">{formatTimestamp(run.created_at)}</span>
                  </div>
                  <div className="activity-row-action">
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => onSelectRun(run)}
                      title={`Inspect run ${run.run_id || '—'}`}
                    >
                      Inspect →
                    </button>
                  </div>
                </div>
              );
            })}

            {runsList.length > 6 && (
              <div className="activity-view-all">
                <button
                  type="button"
                  className="btn btn-link"
                  onClick={() => onSelectView('history')}
                >
                  View all {runsList.length} inspection runs in History →
                </button>
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}

/* ---------------------------------------------------------------------------
   HeroTelemetryGraphic — Animated SVG command-center telemetry panel
   Class names on SVG elements enable CSS keyframe animations.
--------------------------------------------------------------------------- */
function HeroTelemetryGraphic({ runCount, latestStatus }) {
  return (
    <div className="hero-telemetry">
      <div className="telemetry-corner telemetry-corner--tl" aria-hidden="true" />
      <div className="telemetry-corner telemetry-corner--br" aria-hidden="true" />

      <svg
        className="telemetry-svg"
        viewBox="0 0 420 320"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <pattern id="tgrid" width="28" height="28" patternUnits="userSpaceOnUse">
            <path d="M 28 0 L 0 0 0 28" fill="none" stroke="rgba(0,201,167,0.06)" strokeWidth="0.5"/>
          </pattern>
          {/* Clip path for waveform draw-in */}
          <clipPath id="waveReveal">
            <rect className="tg-wave-clip" x="30" y="240" width="0" height="50" />
          </clipPath>
        </defs>

        {/* Background grid */}
        <rect width="420" height="320" fill="url(#tgrid)" />

        {/* Outer orbit ring — slow rotation */}
        <circle
          className="tg-ring tg-ring--outer"
          cx="210" cy="155" r="80"
          fill="none" stroke="rgba(0,201,167,0.12)" strokeWidth="1.5"
        />

        {/* Middle ring — dashed, counter-rotate */}
        <circle
          className="tg-ring tg-ring--mid"
          cx="210" cy="155" r="55"
          fill="none" stroke="rgba(0,201,167,0.18)" strokeWidth="1" strokeDasharray="4 6"
        />

        {/* Inner ring — pulse */}
        <circle
          className="tg-ring tg-ring--inner"
          cx="210" cy="155" r="30"
          fill="none" stroke="rgba(0,201,167,0.25)" strokeWidth="1"
        />

        {/* Centre target */}
        <circle cx="210" cy="155" r="8" fill="rgba(0,201,167,0.15)" stroke="rgba(0,201,167,0.5)" strokeWidth="1.5" />
        <circle className="tg-centre-dot" cx="210" cy="155" r="2.5" fill="rgba(0,201,167,0.9)" />

        {/* Crosshair lines */}
        <line className="tg-crosshair tg-crosshair--v1" x1="210" y1="60"  x2="210" y2="100" stroke="rgba(0,201,167,0.3)" strokeWidth="1" />
        <line className="tg-crosshair tg-crosshair--v2" x1="210" y1="210" x2="210" y2="250" stroke="rgba(0,201,167,0.3)" strokeWidth="1" />
        <line className="tg-crosshair tg-crosshair--h1" x1="110" y1="155" x2="150" y2="155" stroke="rgba(0,201,167,0.3)" strokeWidth="1" />
        <line className="tg-crosshair tg-crosshair--h2" x1="270" y1="155" x2="310" y2="155" stroke="rgba(0,201,167,0.3)" strokeWidth="1" />

        {/* Corner bracket markers */}
        <path className="tg-bracket" d="M 130 75 L 130 90 L 145 90" fill="none" stroke="rgba(0,201,167,0.4)" strokeWidth="1.5" />
        <path className="tg-bracket" d="M 290 75 L 290 90 L 275 90" fill="none" stroke="rgba(0,201,167,0.4)" strokeWidth="1.5" />
        <path className="tg-bracket" d="M 130 235 L 130 220 L 145 220" fill="none" stroke="rgba(0,201,167,0.4)" strokeWidth="1.5" />
        <path className="tg-bracket" d="M 290 235 L 290 220 L 275 220" fill="none" stroke="rgba(0,201,167,0.4)" strokeWidth="1.5" />

        {/* Detection bounding boxes — fade in with delay */}
        <g className="tg-bbox tg-bbox--1">
          <rect x="162" y="118" width="40" height="28" rx="1.5" fill="rgba(245,166,35,0.07)" stroke="rgba(245,166,35,0.45)" strokeWidth="1" strokeDasharray="2 2"/>
          <rect x="158" y="108" width="36" height="10" rx="2" fill="rgba(245,166,35,0.9)" />
          <text x="176" y="116" textAnchor="middle" fontSize="6.5" fill="#0D1614" fontWeight="700" fontFamily="monospace">94.2%</text>
        </g>
        <g className="tg-bbox tg-bbox--2">
          <rect x="220" y="145" width="30" height="22" rx="1.5" fill="rgba(167,139,250,0.07)" stroke="rgba(167,139,250,0.4)" strokeWidth="1" strokeDasharray="2 2"/>
          <rect x="216" y="135" width="32" height="10" rx="2" fill="rgba(167,139,250,0.9)" />
          <text x="232" y="143" textAnchor="middle" fontSize="6.5" fill="#0D1614" fontWeight="700" fontFamily="monospace">87.6%</text>
        </g>

        {/* Waveform — draws in left-to-right via clip */}
        <g clipPath="url(#waveReveal)" opacity="0.6">
          <polyline
            className="tg-waveform"
            points="30,275 50,265 70,278 90,260 110,272 130,255 150,268 170,258 190,270 210,250 230,268 250,258 270,272 290,260 310,275 330,262 350,270 370,255 390,268"
            fill="none"
            stroke="rgba(0,201,167,0.5)"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
        </g>
        {/* Waveform baseline */}
        <rect x="30" y="280" width="360" height="1" fill="rgba(0,201,167,0.08)" />

        {/* Stats box */}
        <g className="tg-stats-box">
          <rect x="330" y="82" width="70" height="52" rx="4" fill="rgba(13,22,20,0.7)" stroke="rgba(0,201,167,0.15)" strokeWidth="1"/>
          <text x="365" y="98"  textAnchor="middle" fontSize="7"  fill="rgba(0,201,167,0.6)"  fontFamily="monospace" letterSpacing="0.5">RUNS</text>
          <text x="365" y="116" textAnchor="middle" fontSize="20" fill="rgba(0,201,167,0.95)" fontWeight="700" fontFamily="monospace">
            {runCount != null ? String(runCount) : '0'}
          </text>
          <text x="365" y="127" textAnchor="middle" fontSize="6"  fill="rgba(0,201,167,0.4)"  fontFamily="monospace">total</text>
        </g>

        {/* Status indicator */}
        <circle
          className="tg-status-dot"
          cx="22" cy="78" r="4"
          fill={latestStatus === 'completed'
            ? 'rgba(0,201,167,0.9)'
            : latestStatus
              ? 'rgba(245,166,35,0.9)'
              : 'rgba(83,104,96,0.5)'}
        />
        <text x="32" y="81" fontSize="7" fill="rgba(255,255,255,0.4)" fontFamily="monospace">
          {latestStatus ? latestStatus.toUpperCase() : 'IDLE'}
        </text>
      </svg>

      <div className="telemetry-label telemetry-label--tl">Vision Analysis</div>
      <div className="telemetry-label telemetry-label--br">Defect Detection</div>
    </div>
  );
}
