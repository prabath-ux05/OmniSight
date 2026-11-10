import React from 'react';

export const NAV_ITEMS = [
  { id: 'home', label: 'Home', icon: '🏠', desc: 'System overview & quick actions' },
  { id: 'inspection', label: 'Inspection', icon: '🔍', desc: 'Live browser capture & defect detection' },
  { id: 'history', label: 'History', icon: '📋', desc: 'Audit log of past inspection runs' },
  { id: 'repair', label: 'Repair Workflow', icon: '🛡️', desc: 'Self-healing review & PR governance' },
  { id: 'about', label: 'About', icon: 'ℹ️', desc: 'Architecture & project details' },
  { id: 'settings', label: 'Settings', icon: '⚙️', desc: 'Theme & environment diagnostics' },
];

export default function Header({
  health,
  onRefreshHealth,
  isHealthLoading,
  currentView = 'inspection',
  onSelectView = () => {},
  theme = 'system',
  onToggleTheme = () => {},
  user = null,
  onSignIn = () => {},
  onSignUp = () => {},
  isMenuOpen = false,
  onToggleMenu = () => {},
}) {
  const getHealthBadge = () => {
    if (isHealthLoading) {
      return <span className="badge badge-neutral">Checking backend...</span>;
    }
    if (health?.status === 'ok') {
      return (
        <span className="badge badge-success" title={`Version: ${health.version || '0.1.0'}`}>
          <span className="status-dot status-dot-online"></span>
          Backend API Online
        </span>
      );
    }
    return (
      <span className="badge badge-danger">
        <span className="status-dot status-dot-offline"></span>
        Backend Offline
      </span>
    );
  };

  // Derive user initial if real authenticated session exists
  const userInitial = user?.firstName
    ? user.firstName.charAt(0).toUpperCase()
    : user?.name
    ? user.name.charAt(0).toUpperCase()
    : null;

  const isNavActive = (itemId) => {
    if (currentView === itemId) return true;
    if (itemId === 'inspection' && currentView === 'live') return true;
    if (itemId === 'repair' && currentView === 'proposals') return true;
    return false;
  };

  const getThemeIcon = () => {
    if (theme === 'dark') return '🌙';
    if (theme === 'light') return '☀️';
    return '💻';
  };

  return (
    <>
      <header className="dashboard-header">
        <div className="header-left-cluster">
          {/* 1. Three-bar Hamburger Navigation Button */}
          <button
            type="button"
            className={`hamburger-btn ${isMenuOpen ? 'is-active' : ''}`}
            onClick={onToggleMenu}
            aria-label="Toggle navigation menu"
            aria-expanded={isMenuOpen}
            title="Navigation Menu"
          >
            <span className="hamburger-line"></span>
            <span className="hamburger-line"></span>
            <span className="hamburger-line"></span>
          </button>

          {/* 2. OmniSight Branding */}
          <div
            className="header-brand clickable-brand"
            onClick={() => onSelectView('home')}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') onSelectView('home');
            }}
            title="Go to Home"
          >
            <div className="logo-icon">
              <svg
                width="26"
                height="26"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                <circle cx="12" cy="12" r="3" />
              </svg>
            </div>
            <div>
              <h1 className="header-title">OmniSight</h1>
              <p className="header-subtitle">Multimodal UI Self-Healing &amp; RPA Agent</p>
            </div>
          </div>
        </div>

        {/* 3. Desktop Navigation Entries */}
        <nav className="desktop-nav-menu" aria-label="Primary Navigation">
          {NAV_ITEMS.map((item) => {
            const active = isNavActive(item.id);
            return (
              <button
                key={item.id}
                type="button"
                data-tour-nav={item.id}
                className={`desktop-nav-item ${active ? 'active' : ''}`}
                onClick={() => onSelectView(item.id)}
                title={item.desc}
              >
                <span className="nav-item-icon" aria-hidden="true">{item.icon}</span>
                <span className="nav-item-label">{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* 4. Header Actions: Health, Theme, Auth / Avatar */}
        <div className="header-actions">
          {/* Health badge */}
          {getHealthBadge()}

          {/* Health ping button */}
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefreshHealth}
            disabled={isHealthLoading}
            title="Refresh backend health"
          >
            {isHealthLoading ? 'Pinging...' : 'Check Health'}
          </button>

          {/* Theme Switcher Toggle */}
          <button
            type="button"
            className="btn btn-secondary btn-sm theme-toggle-btn"
            onClick={onToggleTheme}
            title={`Current theme: ${theme}. Click to toggle dark / light / system.`}
            aria-label={`Toggle theme (currently ${theme})`}
          >
            <span aria-hidden="true">{getThemeIcon()}</span>
            <span className="theme-toggle-label">{theme.charAt(0).toUpperCase() + theme.slice(1)}</span>
          </button>

          {/* Real user avatar if session exists; otherwise clear Guest Mode badge & Sign In (Auth Not Configured) */}
          {userInitial ? (
            <div
              className="user-profile-avatar"
              title={`Signed in as ${user.firstName || user.name || 'User'}`}
              aria-label={`User profile: ${user.firstName || user.name || 'User'}`}
            >
              {userInitial}
            </div>
          ) : (
            <div className="header-auth-group">
              <span className="header-guest-badge" title="Guest Mode active: all features available without sign-in">
                <span className="guest-dot" aria-hidden="true"></span>
                Guest Access
              </span>
              <button
                type="button"
                className="btn btn-secondary btn-sm btn-auth-signin"
                onClick={onSignIn}
                title="Authentication is not configured in this deployment. Full guest access is active."
                aria-label="Sign In (Authentication not configured)"
              >
                Sign In
              </button>
            </div>
          )}
        </div>
      </header>

      {/* 5. Slide-Over Navigation Drawer (Mobile, Tablet, and Hamburger Mode) */}
      {isMenuOpen && (
        <div className="drawer-backdrop" onClick={onToggleMenu} aria-hidden="true">
          <aside
            className="nav-drawer"
            onClick={(e) => e.stopPropagation()}
            aria-label="Sidebar Navigation Menu"
          >
            <div className="drawer-header">
              <div className="drawer-brand">
                <div className="logo-icon logo-icon-sm">
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                </div>
                <div>
                  <div className="drawer-title">OmniSight</div>
                  <div className="drawer-subtitle">Navigation</div>
                </div>
              </div>
              <button
                type="button"
                className="drawer-close-btn"
                onClick={onToggleMenu}
                aria-label="Close navigation menu"
              >
                ✕
              </button>
            </div>

            <nav className="drawer-nav-list" aria-label="Mobile Navigation">
              {NAV_ITEMS.map((item) => {
                const active = isNavActive(item.id);
                return (
                  <button
                    key={item.id}
                    type="button"
                    data-tour-nav={item.id}
                    className={`drawer-nav-item ${active ? 'active' : ''}`}
                    onClick={() => {
                      onSelectView(item.id);
                      onToggleMenu();
                    }}
                  >
                    <span className="drawer-nav-icon" aria-hidden="true">{item.icon}</span>
                    <div className="drawer-nav-text">
                      <div className="drawer-nav-label">{item.label}</div>
                      <div className="drawer-nav-desc">{item.desc}</div>
                    </div>
                    {active && <span className="active-pill" aria-hidden="true">Active</span>}
                  </button>
                );
              })}
            </nav>

            <div className="drawer-footer">
              <div className="drawer-footer-row">
                <span className="drawer-footer-label">Theme:</span>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm drawer-theme-btn"
                  onClick={onToggleTheme}
                >
                  <span aria-hidden="true">{getThemeIcon()}</span>
                  <span>{theme.charAt(0).toUpperCase() + theme.slice(1)}</span>
                </button>
              </div>

              <div className="drawer-footer-row">
                <span className="drawer-footer-label">Session:</span>
                <span className="header-guest-badge">
                  <span className="guest-dot" aria-hidden="true"></span>
                  Guest Access
                </span>
              </div>

              {!userInitial && (
                <div className="drawer-auth-row">
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm full-width"
                    onClick={() => {
                      onSignIn();
                      onToggleMenu();
                    }}
                    title="Authentication is not configured in this deployment. Full guest access is active."
                  >
                    Sign In (Auth Not Configured)
                  </button>
                </div>
              )}
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
