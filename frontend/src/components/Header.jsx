import React from 'react';

export const NAV_ITEMS = [
  { id: 'home', label: 'Home', icon: '🏠', desc: 'System overview & quick actions' },
  { id: 'inspection', label: 'Inspection', icon: '🔍', desc: 'Live browser capture & defect detection' },
  { id: 'history', label: 'History', icon: '📋', desc: 'Audit log of past inspection runs' },
  { id: 'repair', label: 'Repair Workflow', icon: '🛡️', desc: 'Self-healing review & PR governance' },
];

export const DRAWER_NAV_ITEMS = [
  { id: 'home', label: 'Home' },
  { id: 'profile', label: 'Profile' },
  { id: 'about', label: 'About' },
  { id: 'settings', label: 'Settings' },
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
  onLoginSignUp,
  isMenuOpen = false,
  onToggleMenu = () => {},
  onCloseMenu = () => {},
}) {
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

  const handleAuthClick = onLoginSignUp || onSignIn;

  const handleDrawerNav = (itemId) => {
    onSelectView(itemId);
    onCloseMenu();
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

        {/* 3. Main Dashboard Header: ONLY Home, Inspection, History, Repair Workflow */}
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

        {/* 4. Far-Right Header Action: Exactly One Login / Sign Up Button or Profile Avatar */}
        <div className="header-actions">
          {user ? (
            <button
              type="button"
              className="user-profile-avatar-btn"
              onClick={() => onSelectView('profile')}
              title={`Signed in as ${user.firstName || user.name || 'User'} - Click to view Profile`}
              aria-label={`User profile: ${user.firstName || user.name || 'User'}`}
            >
              {user.avatar || user.avatarUrl || user.picture ? (
                <img
                  src={user.avatar || user.avatarUrl || user.picture}
                  alt={user.name || user.firstName || 'User'}
                  className="user-profile-avatar-img"
                />
              ) : (
                <div className="user-profile-avatar">
                  {userInitial}
                </div>
              )}
            </button>
          ) : (
            <button
              type="button"
              className="btn btn-primary btn-sm btn-auth-login"
              onClick={handleAuthClick}
              title="Login or Sign Up for an account"
              aria-label="Login or Sign Up"
            >
              Login / Sign Up
            </button>
          )}
        </div>
      </header>

      {/* 5. Slide-Over Navigation Drawer (Mobile, Tablet, and Hamburger Mode) */}
      {isMenuOpen && (
        <div className="drawer-backdrop" onClick={onCloseMenu} aria-hidden="true">
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
                onClick={onCloseMenu}
                aria-label="Close navigation menu"
              >
                ✕
              </button>
            </div>

            {/* Hamburger drawer: ONLY Home, Profile, About, Settings (in that exact order, text-only) */}
            <nav className="drawer-nav-list" aria-label="Mobile Navigation">
              {DRAWER_NAV_ITEMS.map((item) => {
                const active = isNavActive(item.id);
                return (
                  <button
                    key={item.id}
                    type="button"
                    data-tour-nav={item.id}
                    className={`drawer-nav-item ${active ? 'active' : ''}`}
                    onClick={() => handleDrawerNav(item.id)}
                  >
                    <span className="drawer-nav-label">{item.label}</span>
                  </button>
                );
              })}
            </nav>

            {/* Reserved bottom section for authenticated user profile */}
            {user && (
              <div className="drawer-profile-section">
                <button
                  type="button"
                  className="drawer-profile-btn"
                  onClick={() => handleDrawerNav('profile')}
                  title="View Profile"
                  aria-label="View Profile"
                >
                  {user.avatar || user.avatarUrl || user.picture ? (
                    <img
                      src={user.avatar || user.avatarUrl || user.picture}
                      alt={user.name || user.firstName || 'User profile'}
                      className="drawer-profile-avatar-img"
                    />
                  ) : (
                    <div className="user-profile-avatar drawer-profile-avatar">
                      {userInitial}
                    </div>
                  )}
                  <div className="drawer-profile-info">
                    <span className="drawer-profile-name">
                      {user.name || user.firstName || 'User'}
                    </span>
                    {user.email && (
                      <span className="drawer-profile-email">{user.email}</span>
                    )}
                  </div>
                </button>
              </div>
            )}
          </aside>
        </div>
      )}
    </>
  );
}
