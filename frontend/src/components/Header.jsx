import React from 'react';

export default function Header({ health, onRefreshHealth, isHealthLoading }) {
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

  return (
    <header className="dashboard-header">
      <div className="header-brand">
        <div className="logo-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
            <circle cx="12" cy="12" r="3" />
          </svg>
        </div>
        <div>
          <h1 className="header-title">OmniSight</h1>
          <p className="header-subtitle">Multimodal UI Self-Healing &amp; RPA Agent Dashboard</p>
        </div>
      </div>
      <div className="header-actions">
        {getHealthBadge()}
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={onRefreshHealth}
          disabled={isHealthLoading}
          title="Refresh backend health"
        >
          {isHealthLoading ? 'Pinging...' : 'Check Health'}
        </button>
      </div>
    </header>
  );
}
