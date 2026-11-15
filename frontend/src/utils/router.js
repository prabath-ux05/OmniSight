/**
 * OmniSight Client-Side Router & History Management
 *
 * Provides robust SPA routing, URL parsing, browser Back/Forward (popstate) synchronization,
 * direct deep-linking, and page context preservation without external dependencies.
 */

/**
 * Standard view identifiers supported across OmniSight
 */
export const ROUTES = {
  HOME: 'home',
  INSPECTION: 'inspection',
  RESULTS: 'results',
  HISTORY: 'history',
  PROPOSALS: 'proposals',
  REPAIR: 'repair',
  PROFILE: 'profile',
  ABOUT: 'about',
  SETTINGS: 'settings',
};

/**
 * Parse a URL path, search string, or hash into structured route parameters.
 * Supports both standard window.location objects and string URLs.
 *
 * @param {string|Location|Object} locationInput
 * @returns {{
 *   view: string,
 *   runId: string|null,
 *   proposalId: string|null,
 *   findingId: string|null,
 *   rawPath: string
 * }}
 */
export function parseRoute(locationInput) {
  let pathname = '/';
  let search = '';
  let hash = '';

  if (typeof locationInput === 'string') {
    try {
      // Support relative and absolute URL strings
      const base = 'http://localhost';
      const parsed = new URL(locationInput, base);
      pathname = parsed.pathname || '/';
      search = parsed.search || '';
      hash = parsed.hash || '';
    } catch {
      pathname = locationInput.split('?')[0].split('#')[0] || '/';
      search = locationInput.includes('?') ? '?' + locationInput.split('?')[1].split('#')[0] : '';
      hash = locationInput.includes('#') ? '#' + locationInput.split('#')[1] : '';
    }
  } else if (locationInput && typeof locationInput === 'object') {
    pathname = locationInput.pathname || '/';
    search = locationInput.search || '';
    hash = locationInput.hash || '';
  } else if (typeof window !== 'undefined' && window.location) {
    pathname = window.location.pathname || '/';
    search = window.location.search || '';
    hash = window.location.hash || '';
  }

  // Handle hash-based deep linking fallback (e.g. #/proposals/prop_123)
  if (hash && hash.startsWith('#/')) {
    const hashWithoutHash = hash.slice(1);
    const hashParts = hashWithoutHash.split('?');
    pathname = hashParts[0] || '/';
    if (hashParts[1] && !search) {
      search = '?' + hashParts[1];
    }
  }

  // Clean trailing slashes (except root '/')
  const cleanPath = pathname.length > 1 && pathname.endsWith('/') ? pathname.slice(0, -1) : pathname;
  const segments = cleanPath.split('/').filter(Boolean);

  // Parse query parameters
  const params = new URLSearchParams(search);
  let runId = params.get('runId') || params.get('run_id') || null;
  let proposalId = params.get('proposalId') || params.get('proposal_id') || null;
  let findingId = params.get('findingId') || params.get('finding_id') || null;
  let view = params.get('view') || null;

  // Segment-based path parsing:
  // 1. Root / Home
  if (segments.length === 0 || segments[0] === 'home') {
    view = view || ROUTES.HOME;
  }
  // 2. Inspection / Live Studio: /inspection or /live or /inspection/:runId
  else if (segments[0] === 'inspection' || segments[0] === 'live') {
    if (segments.length >= 2 && segments[1]) {
      runId = runId || decodeURIComponent(segments[1]);
      view = ROUTES.RESULTS;
    } else {
      view = runId ? ROUTES.RESULTS : ROUTES.INSPECTION;
    }
  }
  // 3. Results: /results or /results/:runId
  else if (segments[0] === 'results') {
    view = ROUTES.RESULTS;
    if (segments.length >= 2 && segments[1]) {
      runId = runId || decodeURIComponent(segments[1]);
    }
  }
  // 4. Runs: /runs/:runId or /runs/:runId/proposals or /runs/:runId/proposals/:proposalId
  else if (segments[0] === 'runs') {
    if (segments.length >= 2 && segments[1]) {
      runId = runId || decodeURIComponent(segments[1]);
    }
    if (segments.length >= 3 && segments[2] === 'proposals') {
      view = ROUTES.PROPOSALS;
      if (segments.length >= 4 && segments[3]) {
        proposalId = proposalId || decodeURIComponent(segments[3]);
      }
    } else if (segments.length >= 3 && segments[2] === 'repair') {
      view = ROUTES.REPAIR;
      if (segments.length >= 4 && segments[3]) {
        findingId = findingId || decodeURIComponent(segments[3]);
      }
    } else {
      view = ROUTES.RESULTS;
    }
  }
  // 5. History: /history
  else if (segments[0] === 'history') {
    view = ROUTES.HISTORY;
    if (segments.length >= 2 && segments[1]) {
      runId = runId || decodeURIComponent(segments[1]);
    }
  }
  // 6. Proposals: /proposals or /proposals/:proposalId
  else if (segments[0] === 'proposals' || segments[0] === 'proposal') {
    view = ROUTES.PROPOSALS;
    if (segments.length >= 2 && segments[1]) {
      proposalId = proposalId || decodeURIComponent(segments[1]);
    }
  }
  // 7. Repair: /repair or /repair/:runId or /repair/:runId/:findingId
  else if (segments[0] === 'repair' || segments[0] === 'workspace') {
    view = ROUTES.REPAIR;
    if (segments.length >= 2 && segments[1]) {
      runId = runId || decodeURIComponent(segments[1]);
    }
    if (segments.length >= 3 && segments[2]) {
      findingId = findingId || decodeURIComponent(segments[2]);
    }
  }
  // 8. Profile: /profile
  else if (segments[0] === 'profile') {
    view = ROUTES.PROFILE;
  }
  // 9. About: /about
  else if (segments[0] === 'about') {
    view = ROUTES.ABOUT;
  }
  // 10. Settings: /settings
  else if (segments[0] === 'settings') {
    view = ROUTES.SETTINGS;
  }
  // Unknown fallback -> Home
  else {
    view = view || ROUTES.HOME;
  }

  return {
    view: view || ROUTES.HOME,
    runId: runId ? String(runId).trim() : null,
    proposalId: proposalId ? String(proposalId).trim() : null,
    findingId: findingId ? String(findingId).trim() : null,
    rawPath: cleanPath,
  };
}

/**
 * Construct a canonical URL string based on view and parameters.
 *
 * @param {{
 *   view: string,
 *   runId?: string|null,
 *   proposalId?: string|null,
 *   findingId?: string|null
 * }} options
 * @returns {string} Canonical URL path
 */
export function formatRoute({ view, runId, proposalId, findingId } = {}) {
  const cleanView = view ? String(view).trim().toLowerCase() : ROUTES.HOME;
  const cleanRunId = runId ? encodeURIComponent(String(runId).trim()) : null;
  const cleanProposalId = proposalId ? encodeURIComponent(String(proposalId).trim()) : null;
  const cleanFindingId = findingId ? encodeURIComponent(String(findingId).trim()) : null;

  switch (cleanView) {
    case ROUTES.HOME:
      return '/';

    case ROUTES.INSPECTION:
      // Live Studio (when launching a new inspection or no runId)
      return '/inspection';

    case ROUTES.RESULTS:
      // Specific run inspection results
      return cleanRunId ? `/inspection/${cleanRunId}` : '/inspection';

    case ROUTES.HISTORY:
      return cleanRunId ? `/history?runId=${cleanRunId}` : '/history';

    case ROUTES.PROPOSALS:
      if (cleanRunId && cleanProposalId) {
        return `/runs/${cleanRunId}/proposals/${cleanProposalId}`;
      }
      if (cleanProposalId) {
        return cleanRunId ? `/proposals/${cleanProposalId}?runId=${cleanRunId}` : `/proposals/${cleanProposalId}`;
      }
      if (cleanRunId) {
        return `/runs/${cleanRunId}/proposals`;
      }
      return '/proposals';

    case ROUTES.REPAIR:
      if (cleanRunId && cleanFindingId) {
        return `/repair/${cleanRunId}/${cleanFindingId}`;
      }
      if (cleanRunId) {
        return `/repair/${cleanRunId}`;
      }
      return '/repair';

    case ROUTES.PROFILE:
      return '/profile';

    case ROUTES.ABOUT:
      return '/about';

    case ROUTES.SETTINGS:
      return '/settings';

    default:
      return '/';
  }
}

/**
 * Navigate to a destination route using HTML5 History API.
 * Prevents unnecessary or duplicate history entries when navigating to the same URL.
 *
 * @param {{
 *   view: string,
 *   runId?: string|null,
 *   proposalId?: string|null,
 *   findingId?: string|null,
 *   replace?: boolean
 * }} options
 * @returns {string} The navigated URL path
 */
export function navigateRoute({ view, runId, proposalId, findingId, replace = false } = {}) {
  const targetUrl = formatRoute({ view, runId, proposalId, findingId });

  if (typeof window === 'undefined') {
    return targetUrl;
  }

  const currentUrl = (window.location.pathname || '/') + (window.location.search || '');

  const statePayload = {
    view: view || ROUTES.HOME,
    runId: runId || null,
    proposalId: proposalId || null,
    findingId: findingId || null,
    timestamp: Date.now(),
  };

  // If already at the target URL, use replaceState to update state without adding duplicate history
  if (currentUrl === targetUrl) {
    if (window.history && typeof window.history.replaceState === 'function') {
      window.history.replaceState(statePayload, '', targetUrl);
    }
  } else if (replace) {
    if (window.history && typeof window.history.replaceState === 'function') {
      window.history.replaceState(statePayload, '', targetUrl);
    }
  } else {
    if (window.history && typeof window.history.pushState === 'function') {
      window.history.pushState(statePayload, '', targetUrl);
    }
  }

  // Notify active router listeners of the navigation event
  try {
    const navEvent = new CustomEvent('omnisight:navigate', {
      detail: { url: targetUrl, ...statePayload },
    });
    window.dispatchEvent(navEvent);
  } catch {
    // Graceful fallback for non-browser or test environments
  }

  return targetUrl;
}

/**
 * Subscribe to router navigation events (browser back/forward popstate + internal pushes).
 *
 * @param {Function} callback Callback receiving parsed route info
 * @returns {Function} Unsubscribe cleanup function
 */
export function subscribeToNavigation(callback) {
  if (typeof window === 'undefined') {
    return () => {};
  }

  const handlePopState = (event) => {
    const route = parseRoute(window.location);
    // Merge history state if available
    if (event && event.state) {
      if (event.state.runId && !route.runId) route.runId = event.state.runId;
      if (event.state.proposalId && !route.proposalId) route.proposalId = event.state.proposalId;
      if (event.state.findingId && !route.findingId) route.findingId = event.state.findingId;
    }
    callback(route);
  };

  const handleInternalNav = (event) => {
    if (event && event.detail) {
      const route = parseRoute(window.location);
      if (event.detail.runId) route.runId = event.detail.runId;
      if (event.detail.proposalId) route.proposalId = event.detail.proposalId;
      if (event.detail.findingId) route.findingId = event.detail.findingId;
      callback(route);
    } else {
      callback(parseRoute(window.location));
    }
  };

  window.addEventListener('popstate', handlePopState);
  window.addEventListener('omnisight:navigate', handleInternalNav);

  return () => {
    window.removeEventListener('popstate', handlePopState);
    window.removeEventListener('omnisight:navigate', handleInternalNav);
  };
}
