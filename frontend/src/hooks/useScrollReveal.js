import { useEffect, useRef, useState } from 'react';

/**
 * useScrollReveal — IntersectionObserver-based scroll reveal hook.
 *
 * Returns [ref, isVisible].
 * - Elements already in the viewport on mount are immediately marked visible.
 * - Respects `prefers-reduced-motion` (instantly marks visible, skips observer).
 * - Once visible, stays visible (observer is disconnected on first trigger).
 *
 * @param {object}  options
 * @param {number}  options.threshold  Intersection ratio to trigger (default 0.1)
 * @param {string}  options.rootMargin Margin around viewport (default '0px 0px -48px 0px')
 */
export function useScrollReveal({ threshold = 0.1, rootMargin = '0px 0px -48px 0px' } = {}) {
  const ref = useRef(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Immediately visible for reduced-motion users — no animation needed
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      setIsVisible(true);
      return;
    }

    // Synchronous check: element already in viewport on mount
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight && rect.bottom > 0) {
      setIsVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
          observer.unobserve(el); // Stay revealed — no toggling back
        }
      },
      { threshold, rootMargin }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return [ref, isVisible];
}
