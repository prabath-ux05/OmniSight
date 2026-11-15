/**
 * OmniSight User Profile & Avatar Helper Utilities
 *
 * Dynamically resolves user display names and avatar initials from authenticated
 * user payloads (supporting backend `full_name`, `name`, `firstName`, and email fallback).
 */

/**
 * Derives the uppercase avatar initial from a user object.
 *
 * Checks in order:
 * 1. user.full_name
 * 2. user.fullName
 * 3. user.name
 * 4. user.firstName
 * 5. user.email prefix
 *
 * Trims leading/trailing whitespace and returns the uppercase first character.
 * Falls back gracefully to 'U'.
 *
 * @param {Object|null|undefined} user
 * @returns {string} Single uppercase character initial
 */
export function getUserInitial(user) {
  if (!user || typeof user !== 'object') return 'U';
  const candidate = (
    user.full_name ||
    user.fullName ||
    user.name ||
    user.firstName ||
    (typeof user.email === 'string' ? user.email.split('@')[0] : '') ||
    ''
  ).trim();

  return candidate ? candidate.charAt(0).toUpperCase() : 'U';
}

/**
 * Derives a human-readable display name from a user object.
 *
 * @param {Object|null|undefined} user
 * @returns {string} Formatted display name or 'User'
 */
export function getUserDisplayName(user) {
  if (!user || typeof user !== 'object') return 'User';
  const name = (
    user.full_name ||
    user.fullName ||
    user.name ||
    user.firstName ||
    (typeof user.email === 'string' ? user.email.split('@')[0] : '') ||
    ''
  ).trim();

  return name || 'User';
}
