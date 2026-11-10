import React, { useEffect, useRef } from 'react';

/**
 * 6-Step Guided Onboarding Tour Definition
 */
export const TUTORIAL_STEPS = [
  {
    stepId: 'home',
    viewId: 'home',
    badge: 'Step 1 of 6: Getting Started',
    icon: '🏠',
    title: 'Home & Inspection Dispatch',
    description:
      'Welcome to OmniSight! Launch automated multimodal UI inspections by entering any web URL. OmniSight orchestrates a headless browser session to capture visual snapshots and detect defects with zero manual scripting required.',
    tips: [
      'Enter target web URL or use quick demo presets',
      'Guest mode is fully supported with no login barrier',
      'Click "Start Full Inspection" to trigger the autonomous agent pipeline',
    ],
  },
  {
    stepId: 'inspection',
    viewId: 'inspection',
    badge: 'Step 2 of 6: Live Studio',
    icon: '🔍',
    title: 'Inspection Studio & Real-Time Telemetry',
    description:
      'Monitor active inspection runs through capturing, analyzing, and reporting stages. As anomalies are identified, they appear in the Defect Findings list categorized by severity (Critical, High, Medium, Low) and failure type.',
    tips: [
      'Real-time polling synchronizes background execution progress',
      'Filter findings by defect category or search by description',
      'Select any defect finding to inspect multimodal evidence',
    ],
  },
  {
    stepId: 'evidence',
    viewId: 'inspection',
    badge: 'Step 3 of 6: Multimodal Evidence',
    icon: '🖼️',
    title: 'Evidence & Defect Localization',
    description:
      'OmniSight analyzes both rendered pixels and document nodes. Review full-page viewport screenshots alongside serialized DOM HTML trees and broken element selectors to isolate UI regressions immediately.',
    tips: [
      'Side-by-side visual screenshot artifact and captured DOM tree',
      'DOM selector copy action for rapid debugging',
      'Direct link to open the finding in the Self-Healing Repair Workflow',
    ],
  },
  {
    stepId: 'history',
    viewId: 'history',
    badge: 'Step 4 of 6: Audit Log',
    icon: '📋',
    title: 'Run History & Audit Database',
    description:
      'Every inspection run is persistently stored in PostgreSQL (port 5433). Browse past runs, filter by status or date range, copy run IDs, and inspect historical defect breakdowns in read-only mode without re-triggering pipelines.',
    tips: [
      'Filter by status (Completed, Failed, In-Progress) and date intervals',
      'Click any row to open the in-place Historical Run Inspector',
      'Strict read-only safety: opening historical runs never triggers execution',
    ],
  },
  {
    stepId: 'repair',
    viewId: 'repair',
    badge: 'Step 5 of 6: Self-Healing & Governance',
    icon: '🛡️',
    title: 'Self-Healing Locator Repair & Approval',
    description:
      'Synthesize resilient replacement locators using data attributes, semantic IDs, and accessible roles. Converse with the deterministic repair assistant, generate safe minimal test code diffs, and submit pull requests with mandatory human approval.',
    tips: [
      'Chat with the deterministic repair assistant for root-cause analysis',
      'Inspect before-and-after evidence with strict live verification checks',
      'Human-in-the-loop gate: PRs require explicit user confirmation before creation',
    ],
  },
  {
    stepId: 'settings',
    viewId: 'settings',
    badge: 'Step 6 of 6: Preferences & Diagnostics',
    icon: '⚙️',
    title: 'Settings, Themes & Tour Replay',
    description:
      'Configure appearance themes (Dark, Light, or System), check FastAPI service connectivity, inspect environment diagnostics, or replay this guided tour at any time.',
    tips: [
      'Toggle Dark, Light, or System theme preferences',
      'Verify FastAPI service health and environment diagnostics',
      'Replay this guided onboarding tutorial whenever needed',
    ],
  },
];

/**
 * GuidedTutorial renders the lightweight, accessible onboarding walkthrough overlay.
 */
export default function GuidedTutorial({
  isOpen = false,
  currentStepIndex = 0,
  onNext = () => {},
  onPrev = () => {},
  onSkip = () => {},
  onFinish = () => {},
  onJumpToStep = () => {},
}) {
  const cardRef = useRef(null);
  const nextBtnRef = useRef(null);

  const step = TUTORIAL_STEPS[currentStepIndex] || TUTORIAL_STEPS[0];
  const isFirstStep = currentStepIndex === 0;
  const isLastStep = currentStepIndex === TUTORIAL_STEPS.length - 1;

  // Keyboard navigation accessibility
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onSkip();
      } else if (e.key === 'ArrowRight') {
        e.preventDefault();
        if (isLastStep) onFinish();
        else onNext();
      } else if (e.key === 'ArrowLeft') {
        e.preventDefault();
        if (!isFirstStep) onPrev();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isFirstStep, isLastStep, onNext, onPrev, onSkip, onFinish]);

  // Focus management: focus the primary next/finish button when tour opens or step changes
  useEffect(() => {
    if (isOpen && nextBtnRef.current) {
      nextBtnRef.current.focus();
    }
  }, [isOpen, currentStepIndex]);

  if (!isOpen) return null;

  return (
    <div
      className="tour-overlay-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-dialog-title"
      aria-describedby="tour-dialog-desc"
    >
      <div className="tour-dialog-card" ref={cardRef}>
        {/* Tour Header with Step Progress */}
        <div className="tour-card-header">
          <div className="tour-header-meta">
            <span className="tour-step-badge">{step.badge}</span>
            <span className="tour-keyboard-hint">Use ← → or Esc</span>
          </div>

          <button
            type="button"
            className="tour-close-btn"
            onClick={onSkip}
            aria-label="Close and skip tour"
            title="Skip onboarding tour (Esc)"
          >
            ✕
          </button>
        </div>

        {/* Tour Content Body */}
        <div className="tour-card-body">
          <div className="tour-title-row">
            <span className="tour-step-icon">{step.icon}</span>
            <h3 id="tour-dialog-title" className="tour-step-title">
              {step.title}
            </h3>
          </div>

          <p id="tour-dialog-desc" className="tour-step-description">
            {step.description}
          </p>

          {step.tips && step.tips.length > 0 && (
            <div className="tour-tips-box">
              <span className="tour-tips-label">Key Highlights:</span>
              <ul className="tour-tips-list">
                {step.tips.map((tip, idx) => (
                  <li key={idx} className="tour-tip-item">
                    • {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Tour Footer Controls */}
        <div className="tour-card-footer">
          {/* Progress Indicator Dots */}
          <div className="tour-dots-row" aria-label="Tour step progress">
            {TUTORIAL_STEPS.map((s, idx) => (
              <button
                key={s.stepId}
                type="button"
                className={`tour-dot ${idx === currentStepIndex ? 'active' : ''}`}
                onClick={() => onJumpToStep(idx)}
                aria-label={`Jump to step ${idx + 1}: ${s.title}`}
                title={s.title}
              />
            ))}
          </div>

          {/* Action Buttons */}
          <div className="tour-actions-group">
            <button
              type="button"
              className="btn btn-secondary btn-sm tour-btn-skip"
              onClick={onSkip}
              title="Dismiss onboarding tour"
            >
              Skip Tour
            </button>

            {!isFirstStep && (
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={onPrev}
                title="Go to previous step (←)"
              >
                ← Back
              </button>
            )}

            <button
              type="button"
              ref={nextBtnRef}
              className="btn btn-primary btn-sm tour-btn-next"
              onClick={isLastStep ? onFinish : onNext}
              title={isLastStep ? 'Complete tour' : 'Proceed to next step (→)'}
            >
              {isLastStep ? 'Finish Tour ✓' : 'Next Step →'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
