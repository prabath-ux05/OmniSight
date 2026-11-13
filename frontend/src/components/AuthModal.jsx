import React, { useState, useEffect } from 'react';
import { loginUser, registerUser } from '../services/api';

/**
 * Authentication Modal supporting User Registration and Login.
 *
 * Provides:
 * - Tab switching between Sign In and Register
 * - Form validation (email format, 8+ char password, confirmation matching)
 * - Password visibility toggling
 * - Inline error alerts and loading spinners
 * - Seamless session initialization with cookies
 */
export default function AuthModal({
  isOpen = false,
  initialMode = 'login',
  onClose = () => {},
  onAuthSuccess = () => {},
}) {
  const [mode, setMode] = useState(initialMode); // 'login' | 'register'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  // Sync mode whenever initialMode changes
  useEffect(() => {
    setMode(initialMode);
    setErrorMessage('');
  }, [initialMode, isOpen]);

  // Handle ESC key to close modal
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const resetForm = () => {
    setEmail('');
    setPassword('');
    setConfirmPassword('');
    setFullName('');
    setErrorMessage('');
    setShowPassword(false);
  };

  const handleSwitchMode = (newMode) => {
    setMode(newMode);
    setErrorMessage('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMessage('');

    const cleanEmail = email.trim();
    if (!cleanEmail || !cleanEmail.includes('@') || !cleanEmail.includes('.')) {
      setErrorMessage('Please provide a valid email address.');
      return;
    }

    if (!password || password.length < 8) {
      setErrorMessage('Password must be at least 8 characters in length.');
      return;
    }

    if (mode === 'register') {
      if (password !== confirmPassword) {
        setErrorMessage('Passwords do not match. Please re-enter.');
        return;
      }
    }

    setIsLoading(true);

    try {
      if (mode === 'login') {
        const result = await loginUser({ email: cleanEmail, password });
        if (result.ok && result.data) {
          resetForm();
          onAuthSuccess(result.data);
          onClose();
        } else {
          setErrorMessage(result.error || 'Login failed. Please check your email and password.');
        }
      } else {
        const result = await registerUser({
          email: cleanEmail,
          password,
          fullName: fullName.trim() || undefined,
        });
        if (result.ok && result.data) {
          resetForm();
          onAuthSuccess(result.data);
          onClose();
        } else {
          setErrorMessage(result.error || 'Registration failed. Please check your details.');
        }
      }
    } catch (err) {
      setErrorMessage(err?.message || 'An unexpected error occurred. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="auth-modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-modal-title"
    >
      <div
        className="auth-modal-card"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with Title and Close Button */}
        <div className="auth-modal-header">
          <div className="auth-modal-brand">
            <span className="auth-modal-logo-icon" aria-hidden="true">🔐</span>
            <div>
              <h2 id="auth-modal-title" className="auth-modal-title">
                {mode === 'login' ? 'Sign In to OmniSight' : 'Create OmniSight Account'}
              </h2>
              <p className="auth-modal-subtitle">
                {mode === 'login'
                  ? 'Access your private inspection history and repair decisions.'
                  : 'Register for dedicated workspace isolation and audit logs.'}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="auth-modal-close-btn"
            onClick={onClose}
            aria-label="Close authentication modal"
            title="Close"
          >
            ✕
          </button>
        </div>

        {/* Tab Navigation: Sign In / Register */}
        <div className="auth-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            className={`auth-tab-btn ${mode === 'login' ? 'active' : ''}`}
            onClick={() => handleSwitchMode('login')}
          >
            Sign In
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'register'}
            className={`auth-tab-btn ${mode === 'register' ? 'active' : ''}`}
            onClick={() => handleSwitchMode('register')}
          >
            Create Account
          </button>
        </div>

        {/* Error Alert Banner */}
        {errorMessage && (
          <div className="auth-error-banner" role="alert">
            <span className="auth-error-icon" aria-hidden="true">⚠️</span>
            <span className="auth-error-text">{errorMessage}</span>
          </div>
        )}

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          {mode === 'register' && (
            <div className="auth-input-group">
              <label htmlFor="auth-full-name" className="auth-label">
                Full Name <span className="auth-label-opt">(optional)</span>
              </label>
              <input
                id="auth-full-name"
                type="text"
                className="auth-input"
                placeholder="Jane Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                disabled={isLoading}
                autoComplete="name"
              />
            </div>
          )}

          <div className="auth-input-group">
            <label htmlFor="auth-email" className="auth-label">
              Email Address <span className="auth-label-req">*</span>
            </label>
            <input
              id="auth-email"
              type="email"
              className="auth-input"
              placeholder="developer@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading}
              required
              autoComplete="email"
              autoFocus
            />
          </div>

          <div className="auth-input-group">
            <div className="auth-label-row">
              <label htmlFor="auth-password" className="auth-label">
                Password <span className="auth-label-req">*</span>
              </label>
              <span className="auth-label-hint">Min. 8 characters</span>
            </div>
            <div className="auth-password-wrapper">
              <input
                id="auth-password"
                type={showPassword ? 'text' : 'password'}
                className="auth-input auth-password-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={isLoading}
                required
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
              />
              <button
                type="button"
                className="auth-password-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                tabIndex={-1}
              >
                {showPassword ? '👁️' : '🔒'}
              </button>
            </div>
          </div>

          {mode === 'register' && (
            <div className="auth-input-group">
              <label htmlFor="auth-confirm-password" className="auth-label">
                Confirm Password <span className="auth-label-req">*</span>
              </label>
              <input
                id="auth-confirm-password"
                type={showPassword ? 'text' : 'password'}
                className="auth-input"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                disabled={isLoading}
                required
                autoComplete="new-password"
              />
            </div>
          )}

          <button
            type="submit"
            className="btn btn-primary auth-submit-btn"
            disabled={isLoading}
          >
            {isLoading ? (
              <span className="auth-loading-spinner">
                <span className="spinner-icon">⏳</span> Processing...
              </span>
            ) : mode === 'login' ? (
              'Sign In'
            ) : (
              'Register Account'
            )}
          </button>
        </form>

        {/* Guest Mode Callout Footer */}
        <div className="auth-modal-footer">
          <div className="auth-guest-notice">
            <span className="auth-guest-icon" aria-hidden="true">💡</span>
            <div className="auth-guest-text">
              <strong>Guest mode active:</strong> You can also run inspections and explore self-healing repairs
              without signing in. Public guest runs are shared across all sessions.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
