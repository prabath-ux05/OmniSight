import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  fetchPreviewStatus,
  getPreviewStreamUrl,
  getViewportScreenshotUrl,
} from '../services/api';

/**
 * LiveScanningPreview
 *
 * Real-time Live Website Scanning Preview component.
 * Displays actual Playwright browser viewport frames, synchronized top-to-bottom
 * scrolling telemetry, horizontal scanning laser line, and real page defect highlights.
 */
export default function LiveScanningPreview({
  run,
  selectedFindingId,
  onSelectFinding,
}) {
  const [previewState, setPreviewState] = useState(null);
  const [activeViewport, setActiveViewport] = useState('desktop');
  const [connectionMode, setConnectionMode] = useState('idle'); // 'idle' | 'sse' | 'polling' | 'completed' | 'error'
  const [streamError, setStreamError] = useState(null);
  const [hoveredDefectId, setHoveredDefectId] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  const eventSourceRef = useRef(null);
  const pollTimerRef = useRef(null);
  const isMountedRef = useRef(true);

  // Synchronize active viewport from run viewports or current preview state
  useEffect(() => {
    if (run?.viewports && run.viewports.length > 0) {
      if (!run.viewports.includes(activeViewport)) {
        setActiveViewport(run.viewports[0]);
      }
    }
  }, [run?.viewports, activeViewport]);

  const runId = run?.run_id;
  const rawRunStatus = run?.status ? String(run.status).toLowerCase().trim() : '';
  const isTerminal = ['completed', 'failed', 'cancelled'].includes(rawRunStatus);
  const isActive = Boolean(runId && !isTerminal && rawRunStatus);

  // Cleanup helper for SSE and polling timers
  const cleanupConnection = useCallback(() => {
    if (eventSourceRef.current) {
      try {
        eventSourceRef.current.close();
      } catch {
        // Safe ignore
      }
      eventSourceRef.current = null;
    }
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }, []);

  // Fetch initial/fallback snapshot
  const loadPreviewSnapshot = useCallback(async (targetRunId) => {
    if (!targetRunId) return;
    const res = await fetchPreviewStatus(targetRunId);
    if (!isMountedRef.current) return;

    if (res.ok && res.data) {
      setPreviewState(res.data);
      if (res.data.viewport) {
        setActiveViewport(res.data.viewport);
      }
      setStreamError(null);
    } else {
      setStreamError(res.error || 'Preview status unavailable.');
    }
  }, []);

  // Fallback recursive polling if SSE is unsupported or fails
  const startPollingFallback = useCallback((targetRunId) => {
    cleanupConnection();
    setConnectionMode('polling');

    const poll = async () => {
      if (!isMountedRef.current) return;
      const res = await fetchPreviewStatus(targetRunId);
      if (!isMountedRef.current) return;

      if (res.ok && res.data) {
        setPreviewState(res.data);
        const stage = String(res.data.stage || '').toLowerCase();
        if (['completed', 'failed', 'cancelled'].includes(stage)) {
          setConnectionMode('completed');
          return;
        }
      }
      pollTimerRef.current = setTimeout(poll, 1200);
    };

    pollTimerRef.current = setTimeout(poll, 500);
  }, [cleanupConnection]);

  // Connect to live SSE stream or load final snapshot
  useEffect(() => {
    isMountedRef.current = true;
    cleanupConnection();

    if (!runId) {
      setPreviewState(null);
      setConnectionMode('idle');
      setStreamError(null);
      return;
    }

    // Load initial snapshot immediately
    loadPreviewSnapshot(runId);

    if (isTerminal) {
      setConnectionMode('completed');
      return;
    }

    // Open Server-Sent Events stream for real-time live preview
    if (typeof EventSource !== 'undefined') {
      try {
        const streamUrl = getPreviewStreamUrl(runId);
        const es = new EventSource(streamUrl);
        eventSourceRef.current = es;
        setConnectionMode('sse');

        es.onmessage = (event) => {
          if (!isMountedRef.current) return;
          try {
            const data = JSON.parse(event.data);
            setPreviewState(data);
            if (data.viewport) {
              setActiveViewport(data.viewport);
            }
            const stage = String(data.stage || '').toLowerCase();
            if (['completed', 'failed', 'cancelled'].includes(stage)) {
              cleanupConnection();
              setConnectionMode('completed');
            }
          } catch {
            // Ignore parse errors on keep-alives
          }
        };

        es.onerror = () => {
          if (!isMountedRef.current) return;
          // Gracefully fall back to polling on SSE connection failure
          cleanupConnection();
          startPollingFallback(runId);
        };
      } catch {
        startPollingFallback(runId);
      }
    } else {
      startPollingFallback(runId);
    }

    return () => {
      isMountedRef.current = false;
      cleanupConnection();
    };
  }, [runId, isTerminal, cleanupConnection, loadPreviewSnapshot, startPollingFallback]);

  // Effective dimensions and telemetry
  const effectiveStage = previewState?.stage || (isActive ? 'scrolling' : rawRunStatus || 'idle');
  const progressPct = previewState?.progress !== undefined
    ? previewState.progress
    : (rawRunStatus === 'completed' ? 100 : (isActive ? 45 : 0));

  const scrollY = previewState?.scroll_y || 0;
  const maxScrollY = previewState?.max_scroll_y || 0;
  const scrollRatio = previewState?.scroll_ratio !== undefined
    ? previewState.scroll_ratio
    : (maxScrollY > 0 ? scrollY / maxScrollY : 0);

  const vpWidth = previewState?.viewport_width || (activeViewport === 'desktop' ? 1280 : (activeViewport === 'tablet' ? 768 : 375));
  const vpHeight = previewState?.viewport_height || (activeViewport === 'desktop' ? 800 : (activeViewport === 'tablet' ? 1024 : 667));

  // Determine effective preview image
  const liveBase64Frame = previewState?.frame_base64;
  const fallbackArtifactUrl = runId ? getViewportScreenshotUrl(runId, activeViewport) : null;
  const previewImageSrc = liveBase64Frame || fallbackArtifactUrl;

  // Viewport preset dimensions
  const availableViewports = run?.viewports && run.viewports.length > 0
    ? run.viewports
    : ['desktop'];

  // Defect markers for current viewport
  const rawDefects = previewState?.defects || [];
  const currentViewportDefects = rawDefects.filter((d) => {
    const dvp = String(d.viewport || 'desktop').toLowerCase();
    return dvp === activeViewport.toLowerCase();
  });

  // Calculate scanning laser vertical position (% of visible viewport height)
  // When scrolling actively, laser moves across the viewport frame
  const scanLaserPosPct = Math.min(95, Math.max(5, (scrollRatio * 85) + 10));

  return (
    <section className="card live-scanning-preview-card" aria-label="Real-time Live Scanning Preview">
      {/* Header with Title, Telemetry, and Collapse Controls */}
      <div className="preview-card-header">
        <div className="preview-header-left">
          <div className="preview-title-row">
            <span className="preview-live-dot" aria-hidden="true">
              <span className={`pulse-indicator ${isActive ? 'pulse-active' : (isTerminal ? 'pulse-completed' : 'pulse-idle')}`}></span>
            </span>
            <h2 className="preview-title">Live Website Scanning &amp; Visual Studio</h2>
            {isActive && (
              <span className="badge badge-scanning-live" title="Real-time frame streaming from Chromium">
                ● LIVE BROWSER STREAM
              </span>
            )}
            {rawRunStatus === 'completed' && (
              <span className="badge badge-completed-run" title="Inspection completed and audited">
                ✓ INSPECTION AUDITED
              </span>
            )}
            {rawRunStatus === 'failed' && (
              <span className="badge badge-terminal-run" title="Inspection failed">
                ✕ EXECUTION FAILED
              </span>
            )}
          </div>
          <p className="preview-subtitle">
            Synchronized Playwright browser session rendering actual page frames, real top-to-bottom scroll telemetry, and in-situ defect coordinates.
          </p>
        </div>

        <div className="preview-header-right">
          {/* Viewport Switcher Tabs */}
          <div className="preview-viewport-switcher" role="tablist" aria-label="Inspection Viewports">
            {availableViewports.map((vp) => (
              <button
                key={vp}
                type="button"
                role="tab"
                aria-selected={activeViewport === vp}
                className={`viewport-pill-btn ${activeViewport === vp ? 'active' : ''}`}
                onClick={() => setActiveViewport(vp)}
                title={`Switch to ${vp.toUpperCase()} preview`}
              >
                {vp === 'desktop' && '💻 Desktop (1280×800)'}
                {vp === 'tablet' && '📱 Tablet (768×1024)'}
                {vp === 'mobile' && '📱 Mobile (375×667)'}
              </button>
            ))}
          </div>

          <button
            type="button"
            className="btn btn-secondary btn-xs collapse-toggle-btn"
            onClick={() => setIsCollapsed(!isCollapsed)}
            title={isCollapsed ? 'Expand Live Preview' : 'Minimize Live Preview'}
            aria-expanded={!isCollapsed}
          >
            {isCollapsed ? '▼ Expand Preview' : '▲ Collapse'}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          {/* Real-time Progress Bar */}
          <div className="live-progress-container" aria-label="Scanning Progress Bar">
            <div className="live-progress-bar-track">
              <div
                className={`live-progress-bar-fill ${isActive ? 'fill-active' : ''}`}
                style={{ width: `${progressPct}%` }}
                role="progressbar"
                aria-valuenow={progressPct}
                aria-valuemin="0"
                aria-valuemax="100"
              >
                <div className="progress-shimmer"></div>
              </div>
            </div>
            <div className="live-progress-labels">
              <span className="progress-stage-label">
                <strong>Stage:</strong> {previewState?.message || (isActive ? `Scanning ${activeViewport} page...` : 'Ready')}
              </span>
              <span className="progress-percent-label">{progressPct}%</span>
            </div>
          </div>

          {/* Browser Mockup Device Shell */}
          <div className={`browser-device-mockup device-${activeViewport}`}>
            {/* Browser Chrome Header Bar */}
            <div className="device-chrome-bar">
              <div className="chrome-controls">
                <span className="chrome-dot dot-red"></span>
                <span className="chrome-dot dot-yellow"></span>
                <span className="chrome-dot dot-green"></span>
              </div>

              <div className="chrome-address-box">
                <span className="chrome-ssl-lock" title="Secure HTTP / HTTPS Connection">🔒</span>
                <span className="chrome-url-text" title={run?.url || 'No URL Loaded'}>
                  {run?.url || 'https://omnisight-agent.local/inspection'}
                </span>
                <span className="chrome-viewport-badge">
                  {vpWidth} × {vpHeight}
                </span>
              </div>

              <div className="chrome-status-pill">
                <span className="status-mode-text">
                  {connectionMode === 'sse' && '📡 Stream: Active (SSE)'}
                  {connectionMode === 'polling' && '⏱ Polling (1.2s)'}
                  {connectionMode === 'completed' && '✓ Audited Frame'}
                  {connectionMode === 'idle' && 'Idle'}
                </span>
              </div>
            </div>

            {/* Viewport Screen Content */}
            <div className="device-screen-container">
              {previewImageSrc ? (
                <div className="preview-canvas-wrapper">
                  {/* Real Browser Image Frame */}
                  <img
                    src={previewImageSrc}
                    alt={`Live preview of ${run?.url || 'inspection target'} on ${activeViewport}`}
                    className="preview-browser-frame-img"
                  />

                  {/* Animated Synchronized Scanning Laser Line */}
                  {isActive && (
                    <div
                      className="scan-laser-line-wrapper"
                      style={{ top: `${scanLaserPosPct}%` }}
                      aria-hidden="true"
                    >
                      <div className="scan-laser-beam"></div>
                      <div className="scan-laser-glow"></div>
                      <div className="scan-laser-tag">
                        ⌖ SCANNING {activeViewport.toUpperCase()}: {scrollY}px
                      </div>
                    </div>
                  )}

                  {/* Defect Bounding Box Overlays */}
                  {currentViewportDefects.map((defect, idx) => {
                    const isSelected = selectedFindingId && defect.id === selectedFindingId;
                    const isHovered = hoveredDefectId === defect.id;

                    // Calculate positioning: if exact coordinates provided, render at real box
                    let boxStyle = {};
                    if (defect.box && defect.box.width > 0 && defect.box.height > 0) {
                      const leftPct = Math.max(0, Math.min(95, (defect.box.x / vpWidth) * 100));
                      // Position relative to current scroll view or page height
                      const topPct = Math.max(0, Math.min(95, (defect.box.y / (maxScrollY + vpHeight)) * 100));
                      const widthPct = Math.max(4, Math.min(95, (defect.box.width / vpWidth) * 100));
                      const heightPct = Math.max(4, Math.min(80, (defect.box.height / vpHeight) * 100));

                      boxStyle = {
                        left: `${leftPct}%`,
                        top: `${topPct}%`,
                        width: `${widthPct}%`,
                        height: `${heightPct}%`,
                        display: 'block',
                      };
                    } else {
                      // Fallback spread across page for identified findings without explicit bounding rect
                      const fallbackTop = 20 + ((idx * 25) % 65);
                      const fallbackLeft = 10 + ((idx * 30) % 70);
                      boxStyle = {
                        left: `${fallbackLeft}%`,
                        top: `${fallbackTop}%`,
                        width: '28%',
                        minHeight: '60px',
                        display: 'block',
                      };
                    }

                    const sevClass = `defect-marker-${defect.severity || 'medium'}`;

                    return (
                      <div
                        key={defect.id || idx}
                        className={`defect-bounding-box ${sevClass} ${isSelected ? 'selected' : ''} ${isHovered ? 'hovered' : ''}`}
                        style={boxStyle}
                        onClick={() => onSelectFinding && onSelectFinding(defect.id)}
                        onMouseEnter={() => setHoveredDefectId(defect.id)}
                        onMouseLeave={() => setHoveredDefectId(null)}
                        role="button"
                        tabIndex={0}
                        title={`Click to inspect finding: ${defect.description}`}
                        aria-label={`Defect: ${defect.category} (${defect.severity})`}
                      >
                        <div className="defect-corner-marker top-left"></div>
                        <div className="defect-corner-marker top-right"></div>
                        <div className="defect-corner-marker bottom-left"></div>
                        <div className="defect-corner-marker bottom-right"></div>

                        <div className="defect-pin-badge">
                          <span className="pin-icon">⚠️</span>
                          <span className="pin-category">{defect.category?.replace(/_/g, ' ')}</span>
                          {defect.selector && <code className="pin-selector">{defect.selector}</code>}
                        </div>

                        {(isHovered || isSelected) && (
                          <div className="defect-hover-card">
                            <strong className="hover-title">{defect.category?.replace(/_/g, ' ').toUpperCase()}</strong>
                            <p className="hover-desc">{defect.description}</p>
                            <span className="hover-action">Click to inspect in Findings list →</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="preview-empty-screen">
                  {rawRunStatus === 'failed' ? (
                    <div className="preview-screen-error">
                      <div className="error-screen-icon">✕</div>
                      <h3>Browser Navigation Failed</h3>
                      <p>{run?.error || previewState?.error || 'Unable to connect to target URL with Chromium.'}</p>
                    </div>
                  ) : isActive ? (
                    <div className="preview-screen-connecting">
                      <div className="connecting-spinner"></div>
                      <h3>Connecting to Target Website...</h3>
                      <p>Chromium Browser Agent launching for <strong>{run?.url || 'target'}</strong></p>
                    </div>
                  ) : (
                    <div className="preview-screen-standby">
                      <div className="standby-logo">🌐</div>
                      <h3>Visual Inspection Preview Ready</h3>
                      <p>Enter a target URL above and click <strong>Start Inspection</strong> to launch a real-time browser session with live scrolling and defect detection.</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Bottom Telemetry Bar */}
            <div className="device-telemetry-bar">
              <div className="telemetry-pill">
                <span className="telemetry-label">Status:</span>
                <span className="telemetry-val text-capitalize">{effectiveStage}</span>
              </div>

              <div className="telemetry-pill">
                <span className="telemetry-label">Scroll:</span>
                <span className="telemetry-val">{scrollY}px / {maxScrollY}px ({Math.round(scrollRatio * 100)}%)</span>
              </div>

              <div className="telemetry-pill">
                <span className="telemetry-label">Viewport:</span>
                <span className="telemetry-val">{activeViewport.toUpperCase()} ({vpWidth}×{vpHeight})</span>
              </div>

              <div className="telemetry-pill">
                <span className="telemetry-label">Defects Visible:</span>
                <span className={`telemetry-val ${currentViewportDefects.length > 0 ? 'text-warning font-bold' : ''}`}>
                  {currentViewportDefects.length} detected
                </span>
              </div>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
