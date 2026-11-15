import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { getUserInitial, getUserDisplayName } from './user.js';

describe('User Profile & Avatar Initial Helpers', () => {
  it('derives initial from user.full_name (e.g. Prabath D -> P)', () => {
    assert.equal(getUserInitial({ full_name: 'Prabath D' }), 'P');
    assert.equal(getUserDisplayName({ full_name: 'Prabath D' }), 'Prabath D');
  });

  it('handles leading and trailing whitespace cleanly', () => {
    assert.equal(getUserInitial({ full_name: '   alice smith   ' }), 'A');
    assert.equal(getUserDisplayName({ full_name: '   alice smith   ' }), 'alice smith');
  });

  it('derives initial from user.name if full_name is omitted', () => {
    assert.equal(getUserInitial({ name: 'Bob Builder' }), 'B');
    assert.equal(getUserDisplayName({ name: 'Bob Builder' }), 'Bob Builder');
  });

  it('derives initial from user.firstName if full_name/name omitted', () => {
    assert.equal(getUserInitial({ firstName: 'charlie' }), 'C');
    assert.equal(getUserDisplayName({ firstName: 'charlie' }), 'charlie');
  });

  it('falls back to email prefix initial when name is not provided', () => {
    assert.equal(getUserInitial({ email: 'developer@omnisight.dev' }), 'D');
    assert.equal(getUserDisplayName({ email: 'developer@omnisight.dev' }), 'developer');
  });

  it('returns "U" / "User" gracefully when user is null, undefined, or empty', () => {
    assert.equal(getUserInitial(null), 'U');
    assert.equal(getUserDisplayName(null), 'User');

    assert.equal(getUserInitial(undefined), 'U');
    assert.equal(getUserDisplayName(undefined), 'User');

    assert.equal(getUserInitial({}), 'U');
    assert.equal(getUserDisplayName({}), 'User');

    assert.equal(getUserInitial({ full_name: '   ' }), 'U');
    assert.equal(getUserDisplayName({ full_name: '   ' }), 'User');
  });
});
