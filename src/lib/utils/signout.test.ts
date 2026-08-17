import { describe, expect, it } from 'vitest';
import { getSignOutRedirect, shouldPreserveUserForRedirect } from './signout';

describe('sign-out redirect handling', () => {
	it('preserves the user state while navigating to an external identity provider', () => {
		const response = { redirect_url: 'https://idp.example.com/logout' };

		expect(getSignOutRedirect(response)).toBe(response.redirect_url);
		expect(shouldPreserveUserForRedirect(response)).toBe(true);
	});

	it('clears the user state for local sign-out fallback', () => {
		expect(getSignOutRedirect(null)).toBe('/auth');
		expect(shouldPreserveUserForRedirect(null)).toBe(false);
	});
});
