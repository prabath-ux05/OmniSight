import React, { useState, useRef, useEffect } from 'react';

/**
 * Defect category styling configuration.
 * Distinctive, high-contrast colors with non-obscuring subtle fills.
 */
const CATEGORY_STYLES = {
  layout_overflow: {
    color: '#f59e0b', // Amber
    fill: 'rgba(245, 158, 11, 0.14)',
    label: 'Layout Overflow',
    icon: '↔',
  },
  missing_visible_element: {
    color: '#ef4444', // Red
    fill: 'rgba(239, 68, 68, 0.14)',
    label: 'Missing Element',
    icon: '✕',
  },
  broken_image: {
    color: '#a855f7', // Purple
    fill: 'rgba(168, 85, 247, 0.14)',
    label: 'Broken Image',
    icon: '🖼',
  },
  default: {
    color: '#3b82f6', // Blue
    fill: 'rgba(59, 130, 246, 0.14)',
    label: 'UI Defect',
    icon: '⚠️',
  },
};

/**
 * Severity border configuration.
 */
function getSeverityStroke(severity) {
  const s = (severity || 'medium').toLowerCase();
  switch (s) {
    case 'critical':
      return { strokeWidth: 3.5, strokeDasharray: 'none', label: 'Critical' };
    case 'high':
      return { strokeWidth: 3, strokeDasharray: 'none', label: 'High' };
    case 'medium':
      return { strokeWidth: 2.2, strokeDasharray: 'none', label: 'Medium' };
    case 'low':
    default:
      return { strokeWidth: 2, strokeDasharray: '6 4', label: 'Low' };
  }
}

/**
 * DefectHighlightOverlay
 *
 * Renders an immutable screenshot with an accurate, responsive SVG bounding-box overlay.
 * Uses image natural dimensions in viewBox so that all coordinates map with 100% precision
 * across desktop, tablet, and mobile responsive scaling.
 */
export default function DefectHighlightOverlay({
  imageSrc,
  alt = 'Inspection Evidence Screenshot',
  findings = [],
  selectedFindingId = null,
  onSelectFinding = null,
  viewport = 'desktop',
  stage = 'before',
  showLegend = true,
}) {
  const imgRef = useRef(null);
  const [naturalDim, setNaturalDim] = useState({ width: 0, height: 0 });
  const [hoveredFindingId, setHoveredFindingId] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [hasError, setHasError] = useState(false);

  // Normalize findings list
  const findingList = Array.isArray(findings) ? findings : (findings ? [findings] : []);

  // Filter findings matching the active viewport if viewport is specified on finding
  const relevantFindings = findingList.filter((f) => {
    if (!f) return false;
    if (!f.viewport) return true;
    return f.viewport.toLowerCase() === (viewport || 'desktop').toLowerCase();
  });

  // Extract findings with valid bounding box coordinates
  const mappedFindings = relevantFindings.filter((f) => {
    const box = f?.bounding_box;
    return (
      box &&
      typeof box.x === 'number' &&
      typeof box.y === 'number' &&
      typeof box.width === 'number' &&
      typeof box.height === 'number' &&
      box.width > 0 &&
      box.height > 0
    );
  });

  // Findings without reliable coordinates
  const unmappedFindings = relevantFindings.filter((f) => !mappedFindings.includes(f));

  // Update natural dimensions on image load
  const handleImageLoad = (e) => {
    const img = e.target;
    setNaturalDim({
      width: img.naturalWidth || 1280,
      height: img.naturalHeight || 800,
    });
    setIsLoaded(true);
    setHasError(false);
  };

  const handleImageError = () => {
    setIsLoaded(false);
    setHasError(true);
  };

  const selectedFinding = relevantFindings.find((f) => f.finding_id === selectedFindingId);

  return (
    <div className="defect-highlight-wrapper">
      {/* Unmapped Coordinates Notification Banner (Strict Rule: Do not invent bounding boxes) */}
      {selectedFinding && !selectedFinding.bounding_box && (
        <div className="unmapped-coordinates-banner" role="status">
          <span className="unmapped-icon" aria-hidden="true">📍</span>
          <div className="unmapped-text">
            <strong>Location Unmapped:</strong> Defect coordinates could not be precisely identified on the screenshot for finding{' '}
            <code className="finding-id-highlight">{selectedFinding.finding_id}</code>.
            {selectedFinding.selector && (
              <> Target selector: <code>{selectedFinding.selector}</code>.</>
            )}
            {' '}Original screenshot evidence is preserved immutably below.
          </div>
        </div>
      )}

      {/* Main Screenshot Container with Interactive SVG Overlay */}
      <div className="defect-screenshot-stage">
        {!isLoaded && !hasError && imageSrc && (
          <div className="screenshot-loading-spinner">
            <span className="spinner-sm" aria-hidden="true"></span>
            <span>Loading evidence screenshot…</span>
          </div>
        )}

        {imageSrc && !hasError ? (
          <div className="defect-image-container">
            <img
              ref={imgRef}
              src={imageSrc}
              alt={alt}
              className={`defect-base-screenshot ${!isLoaded ? 'hidden-while-loading' : ''}`}
              onLoad={handleImageLoad}
              onError={handleImageError}
              draggable={false}
            />

            {/* Accurate SVG Vector Overlay (Zero Drift on Resize) */}
            {isLoaded && naturalDim.width > 0 && (
              <svg
                className="defect-svg-overlay"
                viewBox={`0 0 ${naturalDim.width} ${naturalDim.height}`}
                preserveAspectRatio="xMidYMid meet"
                aria-label="Defect Bounding Box Highlights"
              >
                <defs>
                  <filter id="focus-glow" x="-20%" y="-20%" width="140%" height="140%">
                    <feDropShadow dx="0" dy="0" stdDeviation="4" floodColor="#38bdf8" floodOpacity="0.8" />
                  </filter>
                </defs>

                {mappedFindings.map((finding, idx) => {
                  const box = finding.bounding_box;
                  const isSelected = selectedFindingId === finding.finding_id;
                  const isHovered = hoveredFindingId === finding.finding_id;
                  const catStyle = CATEGORY_STYLES[finding.category] || CATEGORY_STYLES.default;
                  const sevStyle = getSeverityStroke(finding.severity);
                  const markerNumber = idx + 1;

                  // Highlighting colors
                  const strokeColor = isSelected ? '#38bdf8' : (isHovered ? '#ffffff' : catStyle.color);
                  const fillColor = isSelected ? 'rgba(56, 189, 248, 0.22)' : catStyle.fill;
                  const strokeWidth = isSelected ? sevStyle.strokeWidth * 1.5 : sevStyle.strokeWidth;

                  // Badge position (clamped inside boundaries)
                  const badgeX = Math.max(4, Math.min(naturalDim.width - 90, box.x));
                  const badgeY = Math.max(22, box.y - 6);

                  return (
                    <g
                      key={finding.finding_id || idx}
                      className={`defect-box-group ${isSelected ? 'is-selected' : ''} ${isHovered ? 'is-hovered' : ''}`}
                      onClick={() => onSelectFinding && onSelectFinding(finding.finding_id)}
                      onMouseEnter={() => setHoveredFindingId(finding.finding_id)}
                      onMouseLeave={() => setHoveredFindingId(null)}
                      style={{ cursor: onSelectFinding ? 'pointer' : 'default', pointerEvents: 'auto' }}
                      role="button"
                      tabIndex={0}
                      aria-label={`Finding #${markerNumber}: ${finding.description}`}
                    >
                      <title>
                        {`[#${markerNumber}] Finding: ${finding.finding_id}\n` +
                          `Category: ${catStyle.label}\n` +
                          `Severity: ${finding.severity ? finding.severity.toUpperCase() : 'MEDIUM'}\n` +
                          `Confidence: ${finding.confidence !== undefined ? Math.round(finding.confidence * 100) + '%' : '100%'}\n` +
                          `Selector: ${finding.selector || 'Global layout scope'}\n` +
                          `Coordinates: x:${Math.round(box.x)}, y:${Math.round(box.y)}, w:${Math.round(box.width)}, h:${Math.round(box.height)}`}
                      </title>

                      {/* Highlighted Bounding Box */}
                      <rect
                        x={box.x}
                        y={box.y}
                        width={box.width}
                        height={box.height}
                        fill={fillColor}
                        stroke={strokeColor}
                        strokeWidth={strokeWidth}
                        strokeDasharray={sevStyle.strokeDasharray}
                        rx="4"
                        ry="4"
                        filter={isSelected ? 'url(#focus-glow)' : 'none'}
                        className="defect-rect"
                      />

                      {/* Numbered Pill Marker Badge */}
                      <g className="defect-marker-badge" transform={`translate(${badgeX}, ${badgeY})`}>
                        {/* Background pill */}
                        <rect
                          x="0"
                          y="-18"
                          width={isSelected ? 110 : 38}
                          height="22"
                          rx="4"
                          fill={isSelected ? '#0284c7' : '#0f172a'}
                          stroke={strokeColor}
                          strokeWidth="1.5"
                          opacity="0.95"
                        />
                        {/* Marker text */}
                        <text
                          x={isSelected ? 6 : 8}
                          y="-4"
                          fill="#ffffff"
                          fontSize="11"
                          fontWeight="700"
                          fontFamily="ui-sans-serif, system-ui, sans-serif"
                        >
                          {isSelected ? `#${markerNumber} ${finding.finding_id.slice(-6)}` : `#${markerNumber}`}
                        </text>
                      </g>
                    </g>
                  );
                })}
              </svg>
            )}
          </div>
        ) : (
          <div className="screenshot-fallback-box">
            <span className="fallback-icon" aria-hidden="true">🖼️</span>
            <h4 className="fallback-title">Screenshot Evidence Not Yet Available</h4>
            <p className="fallback-description">
              No screenshot artifact is present on disk for viewport <code>{viewport}</code>.
            </p>
          </div>
        )}
      </div>

      {/* Defect Overlay Details & Legend Bar */}
      {showLegend && isLoaded && mappedFindings.length > 0 && (
        <div className="defect-overlay-legend">
          <div className="legend-items">
            <span className="legend-title">Detected Regions:</span>
            {mappedFindings.map((f, idx) => {
              const catStyle = CATEGORY_STYLES[f.category] || CATEGORY_STYLES.default;
              const isSelected = selectedFindingId === f.finding_id;
              const box = f.bounding_box;

              return (
                <button
                  key={f.finding_id || idx}
                  type="button"
                  className={`legend-pill ${isSelected ? 'active' : ''}`}
                  onClick={() => onSelectFinding && onSelectFinding(f.finding_id)}
                  title={`Focus finding ${f.finding_id}`}
                >
                  <span className="legend-marker-tag" style={{ backgroundColor: catStyle.color }}>
                    #{idx + 1}
                  </span>
                  <span className="legend-finding-id">{f.finding_id}</span>
                  <span className="legend-box-dims">
                    [{Math.round(box.width)}×{Math.round(box.height)}px]
                  </span>
                </button>
              );
            })}
          </div>

          <div className="legend-viewport-indicator">
            <span className="vp-tag font-mono">
              Viewport: {viewport.toUpperCase()} ({naturalDim.width}×{naturalDim.height})
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
