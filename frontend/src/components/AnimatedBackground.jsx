import React from 'react';
import './AnimatedBackground.css';

const NODES = [1, 2, 3, 4, 5, 6, 7, 8].map((i) => ({ id: i }));
const RINGS = [1, 2, 3].map((i) => ({ id: i }));
const SCAN_LINES = [
  { style: { animationDelay: '0s', animationDuration: '9s' } },
  { style: { animationDelay: '3.5s', animationDuration: '12s' } },
  { style: { animationDelay: '7s', animationDuration: '10s' } },
];

export default function AnimatedBackground({ view = 'home' }) {
  const variant = (() => {
    if (view === 'inspection' || view === 'results') return 'scan';
    if (view === 'proposals' || view === 'repair') return 'repair';
    if (view === 'history') return 'archive';
    if (['about', 'settings', 'profile'].includes(view)) return 'calm';
    return 'home';
  })();

  return (
    <div
      className={`omnisight-bg omnisight-bg--${variant}`}
      aria-hidden="true"
      role="presentation"
    >
      {/* Nebula / ambient glow layers */}
      <div className="bg-nebula bg-nebula-primary" />
      <div className="bg-nebula bg-nebula-secondary" />
      <div className="bg-nebula bg-nebula-accent" />

      {/* Subtle perspective grid */}
      <div className="bg-grid" />

      {/* Floating particle nodes */}
      {NODES.map((n) => (
        <div key={n.id} className={`anim-node anim-node-${n.id}`} />
      ))}

      {/* Pulsing concentric rings */}
      {RINGS.map((r) => (
        <div key={r.id} className={`anim-ring anim-ring-${r.id}`} />
      ))}

      {/* Horizontal scan-line sweeps */}
      {SCAN_LINES.map((s, i) => (
        <div key={i} className="bg-scan-line" style={s.style} />
      ))}

      {/* SVG: hex frames + circuit traces + dashed arcs */}
      <svg
        className="bg-svg-layer"
        viewBox="0 0 1440 900"
        preserveAspectRatio="xMidYMid slice"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Hexagonal frames */}
        <g className="svg-hex-group" opacity="0.06">
          <polygon
            points="120,30 155,50 155,90 120,110 85,90 85,50"
            fill="none"
            stroke="#00C9A7"
            strokeWidth="1"
          />
          <polygon
            points="210,80 245,100 245,140 210,160 175,140 175,100"
            fill="none"
            stroke="#00C9A7"
            strokeWidth="0.75"
          />
          <polygon
            points="1280,120 1315,140 1315,180 1280,200 1245,180 1245,140"
            fill="none"
            stroke="#00C9A7"
            strokeWidth="1"
          />
          <polygon
            points="1360,60 1395,80 1395,120 1360,140 1325,120 1325,80"
            fill="none"
            stroke="#F5A623"
            strokeWidth="0.75"
          />
          <polygon
            points="700,750 735,770 735,810 700,830 665,810 665,770"
            fill="none"
            stroke="#A78BFA"
            strokeWidth="0.75"
          />
        </g>

        {/* Circuit trace paths */}
        <g
          className="svg-circuit-group"
          opacity="0.05"
          stroke="#00C9A7"
          strokeWidth="1"
          fill="none"
        >
          <path d="M 60 200 L 140 200 L 140 160 L 220 160" />
          <path d="M 1380 300 L 1300 300 L 1300 340 L 1220 340" />
          <path d="M 60 650 L 120 650 L 120 600 L 200 600 L 200 580" />
          <circle cx="140" cy="200" r="3" fill="#00C9A7" />
          <circle cx="1300" cy="300" r="3" fill="#00C9A7" />
          <circle cx="120" cy="650" r="3" fill="#00C9A7" />
          <circle cx="200" cy="600" r="3" fill="#F5A623" />
        </g>

        {/* Large dashed orbit rings */}
        <g opacity="0.03">
          <circle
            cx="1200"
            cy="150"
            r="380"
            fill="none"
            stroke="#00C9A7"
            strokeWidth="1.5"
            strokeDasharray="6 18"
          />
          <circle
            cx="240"
            cy="750"
            r="280"
            fill="none"
            stroke="#A78BFA"
            strokeWidth="1"
            strokeDasharray="4 20"
          />
        </g>
      </svg>

      {/* Noise grain overlay for depth */}
      <div className="bg-grain" />
    </div>
  );
}
