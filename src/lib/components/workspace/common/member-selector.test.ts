import assert from 'node:assert/strict';
import test from 'node:test';

import { shouldShowSelectableUser } from './member-selector.ts';

test('hides the current user by default', () => {
	assert.equal(shouldShowSelectableUser('user-1', 'user-1'), false);
});

test('shows the current user when explicitly allowed', () => {
	assert.equal(shouldShowSelectableUser('user-1', 'user-1', true), true);
});

test('shows other users regardless of the current-user flag', () => {
	assert.equal(shouldShowSelectableUser('user-2', 'user-1'), true);
});
