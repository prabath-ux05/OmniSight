/**
 * OmniSight Test Target — Controlled Defect Engine
 * 
 * Manages deterministic UI defect injection and baseline restoration.
 * Designed for automated Playwright / Selenium browser agents and Vision Models.
 */

(function () {
  'use strict';

  // Baseline initial constants
  const BASELINE_SUBTEXT = '42 browser sessions navigating target endpoints concurrently.';
  const OVERFLOW_SUBTEXT = 'CRITICAL_ALERT_BUFFER_OVERFLOW: 42_CONCURRENT_RPA_WORKERS_EXPERIENCING_UNBOUNDED_TELEMETRY_PIPELINE_DESYNCHRONIZATION_EVENT_HASH_98fa4bc10028a4c88e990021bbcf009217894a488fbe01994e_UNCONSTRAINED_HORIZONTAL_BLOWOUT_TRIGGERED_NO_TRUNCATION_TEST_BURST_PAYLOAD_PAYLOAD_PAYLOAD_BURST_BURST_ACTIVE_BURST_END';

  const CLEAN_IMAGE_SRC = 'assets/images/system-topology.svg';
  const BROKEN_IMAGE_SRC = 'assets/images/non-existent-broken-diagram.png';

  // Internal state
  const state = {
    overflow: false,
    missingElement: false,
    brokenImage: false
  };

  // Cached DOM element references
  let elements = {};

  function initElements() {
    elements = {
      body: document.getElementById('omnisight-portal-body') || document.body,
      // Defect Dock Elements
      dock: document.getElementById('defect-control-dock'),
      dockContent: document.getElementById('defect-dock-content'),
      dockCollapseBtn: document.getElementById('btn-toggle-defect-panel'),
      dockCollapseIcon: document.getElementById('dock-collapse-icon'),
      statusSummary: document.getElementById('defect-status-summary'),
      toggleOverflow: document.getElementById('toggle-defect-overflow'),
      toggleMissing: document.getElementById('toggle-defect-missing-element'),
      toggleBrokenImage: document.getElementById('toggle-defect-broken-image'),
      cardOverflowToggle: document.getElementById('defect-card-overflow'),
      cardMissingToggle: document.getElementById('defect-card-missing-element'),
      cardBrokenImageToggle: document.getElementById('defect-card-broken-image'),
      btnReset: document.getElementById('btn-reset-defects'),
      btnInjectAll: document.getElementById('btn-inject-all-defects'),

      // Defect 1 Targets (Overflow)
      cardActiveJobs: document.getElementById('card-active-jobs'),
      metricSubtext: document.getElementById('metric-active-jobs-subtext'),

      // Defect 2 Targets (Missing Visible Element)
      btnTriggerSelfHeal: document.getElementById('btn-trigger-self-heal'),
      tableStatus102: document.getElementById('status-badge-102'),
      tableHeal102: document.getElementById('heal-badge-102'),

      // Defect 3 Targets (Broken Image)
      topologyImage: document.getElementById('service-topology-image'),
      imageFallback: document.getElementById('image-fallback-placeholder'),
      topologyCaption: document.getElementById('topology-status-caption'),
      tableStatus104: document.getElementById('status-badge-104'),
      tableHeal104: document.getElementById('heal-badge-104')
    };
  }

  /**
   * Apply Defect 1: Layout Overflow
   */
  function applyDefectOverflow(active) {
    state.overflow = Boolean(active);
    elements.body.setAttribute('data-defect-overflow', state.overflow ? 'true' : 'false');
    
    if (elements.toggleOverflow) {
      elements.toggleOverflow.checked = state.overflow;
    }
    if (elements.cardOverflowToggle) {
      elements.cardOverflowToggle.classList.toggle('is-active', state.overflow);
    }

    if (elements.metricSubtext) {
      elements.metricSubtext.textContent = state.overflow ? OVERFLOW_SUBTEXT : BASELINE_SUBTEXT;
    }
  }

  /**
   * Apply Defect 2: Missing Visible Element (#btn-trigger-self-heal)
   */
  function applyDefectMissingElement(active) {
    state.missingElement = Boolean(active);
    elements.body.setAttribute('data-defect-missing', state.missingElement ? 'true' : 'false');

    if (elements.toggleMissing) {
      elements.toggleMissing.checked = state.missingElement;
    }
    if (elements.cardMissingToggle) {
      elements.cardMissingToggle.classList.toggle('is-active', state.missingElement);
    }

    // Update corresponding telemetry table row
    if (elements.tableStatus102 && elements.tableHeal102) {
      if (state.missingElement) {
        elements.tableStatus102.textContent = 'Locator Missing (404)';
        elements.tableStatus102.className = 'status-badge status-danger';
        elements.tableHeal102.textContent = 'Awaiting Self-Healing Patch';
        elements.tableHeal102.className = 'heal-badge heal-active';
      } else {
        elements.tableStatus102.textContent = 'Passing';
        elements.tableStatus102.className = 'status-badge status-success';
        elements.tableHeal102.textContent = 'Standard Locator';
        elements.tableHeal102.className = 'heal-badge heal-idle';
      }
    }
  }

  /**
   * Apply Defect 3: Broken Image Asset (#service-topology-image)
   */
  function applyDefectBrokenImage(active) {
    state.brokenImage = Boolean(active);
    elements.body.setAttribute('data-defect-broken-image', state.brokenImage ? 'true' : 'false');

    if (elements.toggleBrokenImage) {
      elements.toggleBrokenImage.checked = state.brokenImage;
    }
    if (elements.cardBrokenImageToggle) {
      elements.cardBrokenImageToggle.classList.toggle('is-active', state.brokenImage);
    }

    if (elements.topologyImage) {
      if (state.brokenImage) {
        elements.topologyImage.src = BROKEN_IMAGE_SRC;
        elements.topologyImage.style.display = 'none';
        if (elements.imageFallback) {
          elements.imageFallback.style.display = 'flex';
        }
        if (elements.topologyCaption) {
          elements.topologyCaption.textContent = '⚠️ Broken Visual Asset: 404 Not Found';
        }
        if (elements.tableStatus104 && elements.tableHeal104) {
          elements.tableStatus104.textContent = 'Visual Asset 404';
          elements.tableStatus104.className = 'status-badge status-danger';
          elements.tableHeal104.textContent = 'Vision Fallback Engaged';
          elements.tableHeal104.className = 'heal-badge heal-active';
        }
      } else {
        elements.topologyImage.src = CLEAN_IMAGE_SRC;
        elements.topologyImage.style.display = 'block';
        if (elements.imageFallback) {
          elements.imageFallback.style.display = 'none';
        }
        if (elements.topologyCaption) {
          elements.topologyCaption.textContent = 'Visual Asset Verified: system-topology.svg';
        }
        if (elements.tableStatus104 && elements.tableHeal104) {
          elements.tableStatus104.textContent = 'Passing';
          elements.tableStatus104.className = 'status-badge status-success';
          elements.tableHeal104.textContent = 'Visual OK';
          elements.tableHeal104.className = 'heal-badge heal-idle';
        }
      }
    }
  }

  /**
   * Refresh Status Summary Badge in Control Dock
   */
  function updateSummaryBadge() {
    const activeCount = [state.overflow, state.missingElement, state.brokenImage].filter(Boolean).length;
    
    if (elements.statusSummary) {
      if (activeCount === 0) {
        elements.statusSummary.textContent = 'Baseline (Clean)';
        elements.statusSummary.className = 'status-pill status-clean';
      } else {
        const labels = [];
        if (state.overflow) labels.push('Overflow');
        if (state.missingElement) labels.push('Missing CTA');
        if (state.brokenImage) labels.push('Broken Image');
        elements.statusSummary.textContent = `Defects Active (${activeCount}): ${labels.join(', ')}`;
        elements.statusSummary.className = 'status-pill status-defective';
      }
    }

    // Dispatch global event for agent automation listeners
    const event = new CustomEvent('omnisight:defect-change', {
      detail: {
        state: { ...state },
        activeCount
      }
    });
    window.dispatchEvent(event);
  }

  /**
   * Reset all defects to clean baseline
   */
  function resetAllDefects() {
    applyDefectOverflow(false);
    applyDefectMissingElement(false);
    applyDefectBrokenImage(false);
    updateSummaryBadge();

    if (window.showToast) {
      window.showToast('Reset to Baseline: Clean State Active', 'clean');
    }
  }

  /**
   * Inject all defects simultaneously
   */
  function injectAllDefects() {
    applyDefectOverflow(true);
    applyDefectMissingElement(true);
    applyDefectBrokenImage(true);
    updateSummaryBadge();

    if (window.showToast) {
      window.showToast('Injected all 3 reproducible defects!', 'defect');
    }
  }

  /**
   * Read and parse URL parameters
   */
  function parseUrlParameters() {
    const params = new URLSearchParams(window.location.search);

    // Baseline clean override
    if (params.get('state') === 'clean' || params.get('baseline') === 'true') {
      resetAllDefects();
      return;
    }

    // Inject all override
    if (params.get('defects') === 'all' || params.get('state') === 'corrupted') {
      injectAllDefects();
      return;
    }

    // Specific defect checks
    const defectParam = (params.get('defect') || '').toLowerCase();
    const defectsList = (params.get('defects') || '').toLowerCase().split(',');

    const hasOverflow = defectParam === 'overflow' ||
      defectsList.includes('overflow') ||
      params.get('defect_overflow') === 'true' ||
      params.get('defect_overflow') === '1';

    const hasMissing = defectParam === 'missing' ||
      defectParam === 'missing_element' ||
      defectsList.includes('missing') ||
      defectsList.includes('missing_element') ||
      params.get('defect_missing') === 'true' ||
      params.get('defect_missing') === '1';

    const hasBrokenImage = defectParam === 'image' ||
      defectParam === 'broken_image' ||
      defectsList.includes('image') ||
      defectsList.includes('broken_image') ||
      params.get('defect_broken_image') === 'true' ||
      params.get('defect_broken_image') === '1';

    applyDefectOverflow(hasOverflow);
    applyDefectMissingElement(hasMissing);
    applyDefectBrokenImage(hasBrokenImage);
    updateSummaryBadge();
  }

  /**
   * Attach UI event listeners
   */
  function setupListeners() {
    // Dock collapse toggle
    if (elements.dockCollapseBtn) {
      elements.dockCollapseBtn.addEventListener('click', function () {
        const isCollapsed = elements.dockContent.style.display === 'none';
        elements.dockContent.style.display = isCollapsed ? 'flex' : 'none';
        elements.dockCollapseIcon.textContent = isCollapsed ? '▲' : '▼';
        elements.dockCollapseBtn.setAttribute('aria-expanded', isCollapsed ? 'true' : 'false');
      });
    }

    // Defect checkbox toggles
    if (elements.toggleOverflow) {
      elements.toggleOverflow.addEventListener('change', function (e) {
        applyDefectOverflow(e.target.checked);
        updateSummaryBadge();
        if (window.showToast) {
          window.showToast(e.target.checked ? 'Defect Enabled: Layout Overflow' : 'Defect Cleared: Layout Overflow', e.target.checked ? 'defect' : 'clean');
        }
      });
    }

    if (elements.toggleMissing) {
      elements.toggleMissing.addEventListener('change', function (e) {
        applyDefectMissingElement(e.target.checked);
        updateSummaryBadge();
        if (window.showToast) {
          window.showToast(e.target.checked ? 'Defect Enabled: Missing Element (#btn-trigger-self-heal)' : 'Defect Cleared: Element Restored', e.target.checked ? 'defect' : 'clean');
        }
      });
    }

    if (elements.toggleBrokenImage) {
      elements.toggleBrokenImage.addEventListener('change', function (e) {
        applyDefectBrokenImage(e.target.checked);
        updateSummaryBadge();
        if (window.showToast) {
          window.showToast(e.target.checked ? 'Defect Enabled: Broken Image (404)' : 'Defect Cleared: Image Restored', e.target.checked ? 'defect' : 'clean');
        }
      });
    }

    // Action buttons
    if (elements.btnReset) {
      elements.btnReset.addEventListener('click', resetAllDefects);
    }

    if (elements.btnInjectAll) {
      elements.btnInjectAll.addEventListener('click', injectAllDefects);
    }
  }

  // Initialize on DOMContentLoaded
  document.addEventListener('DOMContentLoaded', function () {
    initElements();
    setupListeners();
    parseUrlParameters();
  });

  // Expose API for Browser Agent and automated test scripts
  window.OmniSightDefects = {
    getState: function () {
      return { ...state };
    },
    setOverflow: function (val) {
      applyDefectOverflow(val);
      updateSummaryBadge();
    },
    setMissingElement: function (val) {
      applyDefectMissingElement(val);
      updateSummaryBadge();
    },
    setBrokenImage: function (val) {
      applyDefectBrokenImage(val);
      updateSummaryBadge();
    },
    resetAll: resetAllDefects,
    injectAll: injectAllDefects
  };

})();
