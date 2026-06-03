import { beforeEach, describe, expect, it, vi } from 'vitest';

const { removeItem, setUser, userSignOut } = vi.hoisted(() => ({
	removeItem: vi.fn(),
	setUser: vi.fn(),
	userSignOut: vi.fn()
}));

vi.mock('$lib/apis/auths', () => ({
	userSignOut
}));

vi.mock('$lib/stores', () => ({
	user: {
		set: setUser
	}
}));

import { performSignOut, resolveSignOutRedirect } from './signout';

describe('signout helper', () => {
	beforeEach(() => {
		removeItem.mockReset();
		setUser.mockReset();
		userSignOut.mockReset();

		Object.defineProperty(globalThis, 'localStorage', {
			value: {
				removeItem
			},
			configurable: true
		});

		Object.defineProperty(globalThis, 'location', {
			value: {
				href: 'http://localhost/app'
			},
			configurable: true,
			writable: true
		});
	});

	it('uses the backend redirect when signout returns one', async () => {
		userSignOut.mockResolvedValue({ redirect_url: 'https://idp.example/logout' });

		await performSignOut();

		expect(userSignOut).toHaveBeenCalledTimes(1);
		expect(setUser).toHaveBeenCalledWith(null);
		expect(removeItem).toHaveBeenCalledWith('token');
		expect(globalThis.location.href).toBe('https://idp.example/logout');
	});

	it('falls back to /auth when signout has no redirect url', async () => {
		userSignOut.mockResolvedValue(null);

		await performSignOut();

		expect(globalThis.location.href).toBe('/auth');
	});

	it('resolves the default auth path without a response payload', () => {
		expect(resolveSignOutRedirect(null)).toBe('/auth');
	});
});
