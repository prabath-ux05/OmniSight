/**
 * useCursorGlow — Tracks mouse position within an element and sets
 * CSS custom properties --glow-x / --glow-y for cursor-responsive
 * radial lighting effects.
 *
 * Usage:
 *   const glowProps = useCursorGlow();
 *   <div className="cursor-glow" {...glowProps} />
 *
 * The CSS on `.cursor-glow::before` reads --glow-x / --glow-y to position
 * a subtle radial highlight that follows the cursor.
 */
import { useRef, useCallback } from 'react';

const REDUCED_MOTION_QUERY = '(prefers-reduced-motion: reduce)';

export function useCursorGlow() {
  const ref = useRef(null);

  const handleMouseMove = useCallback((e) => {
    const el = ref.current;
    if (!el) return;
    if (window.matchMedia(REDUCED_MOTION_QUERY).matches) return;
    const rect = el.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    el.style.setProperty('--glow-x', `${x.toFixed(2)}%`);
    el.style.setProperty('--glow-y', `${y.toFixed(2)}%`);
  }, []);

  const handleMouseLeave = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    // Reset to top-centre so the glow fades off-screen gracefully
    el.style.setProperty('--glow-x', '50%');
    el.style.setProperty('--glow-y', '-20%');
  }, []);

  return {
    ref,
    onMouseMove: handleMouseMove,
    onMouseLeave: handleMouseLeave,
  };
}
