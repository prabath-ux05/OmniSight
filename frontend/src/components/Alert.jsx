import React from 'react';

export default function Alert({ type = 'info', message, onDismiss }) {
  if (!message) return null;

  const typeClass = {
    error: 'alert-error',
    warning: 'alert-warning',
    success: 'alert-success',
    info: 'alert-info',
  }[type] || 'alert-info';

  return (
    <div className={`alert ${typeClass}`} role="alert">
      <div className="alert-content">
        <span className="alert-message">{message}</span>
      </div>
      {onDismiss && (
        <button type="button" className="alert-close" onClick={onDismiss} aria-label="Close alert">
          &times;
        </button>
      )}
    </div>
  );
}
