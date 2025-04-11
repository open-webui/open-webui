import { describe, beforeEach, expect, it, vi } from 'vitest';
import { get, writable } from 'svelte/store';
import { signout } from '$lib/services/auths';

const mocks = vi.hoisted(() => {
	return {
		userSignOut: vi.fn(),
	};
});

vi.mock('$lib/apis/auths', () => {
	return {
		userSignOut: mocks.userSignOut,
	};
});

vi.mock('$lib/stores', () => {
	mocks.config = writable({ });
	mocks.user = writable({ });

	return {
		config: mocks.config,
		user: mocks.user,
	};
});

vi.stubGlobal('location', {
	href: 'unset',
});

vi.stubGlobal('localStorage', {
	removeItem: vi.fn(),
});

describe('signout()', () => {
	beforeEach(() => {
		vi.resetAllMocks();

		mocks.config.set({
			oauth: {
				providers: {
					oidc: 'Test',
				},
			},
		});
		mocks.user.set({ });
		location.href = 'unset';
		mocks.userSignOut.mockImplementation(() => ({ status: true }));
	});

	it('should call api.userSignOut()', async () => {
		mocks.config.set({ /* No oauth configured */ });

		signout();
		await expect(mocks.userSignOut).toHaveBeenCalled();
	});

	it('should re-throw', async () => {
		mocks.userSignOut.mockImplementation(() => { throw new Error('some error'); });
		await expect(signout()).rejects.toThrowError('some error');
	});

	it('should throw if signout was not successful', async () => {
		mocks.config.set({ /* No oauth configured */ });

		mocks.userSignOut.mockImplementation(() => ({ status: false }));
		await expect(signout()).rejects.toThrowError('Signout was not successful');
	});

	describe("signout successful", () => {
		describe('no end_session_endpoint', () => {
			beforeEach(() => {
				mocks.config.set({ /* No oauth configured */ });

				mocks.userSignOut.mockImplementation(() => ({ status: true }));
			});

			it('should set location to /auth', async () => {
				await signout();
				expect(location.href).toBe('/auth');
			});

			it('should remove token from localStorage', async () => {
				await signout();
				expect(localStorage.removeItem).toHaveBeenCalledWith('token');
			});

			it('should unset the user', async () => {
				await signout();
				expect(get(mocks.user)).toEqual(null);
			});
		});

		describe('has no end_session_endpoint with OIDC configured', () => {
			beforeEach(() => {
				mocks.config.set({
					oauth: {
						providers: {
							oidc: 'Test',
						},
					},
				});

				// end_session_endpoint missing
				mocks.userSignOut.mockImplementation(() => ({ status: true }));
			});

			it('should remove token from localStorage', async () => {
				await expect(signout()).rejects.toThrowError('OIDC configured but no end_session_endpoint sent');

				expect(localStorage.removeItem).toHaveBeenCalledWith('token');
			});

			it('should unset the user', async () => {
				await expect(signout()).rejects.toThrowError('OIDC configured but no end_session_endpoint sent');

				expect(get(mocks.user)).toEqual(null);
			});

			it('should throw if no end_session_endpoint was sent', async () => {
				await expect(signout()).rejects.toThrowError('OIDC configured but no end_session_endpoint sent');
			});
		});

		describe('has end_session_endpoint', () => {
			const endpoint = 'https://acmeauth.com/logout';

			beforeEach(() => {
				mocks.config.set({
					oauth: {
						providers: {
							oidc: 'Test',
						},
					},
				});

				mocks.userSignOut.mockImplementation(() => ({ status: true, end_session_endpoint: endpoint }));
			});

			it('should set location to /auth', async () => {
				await signout();
				expect(location.href).toBe(endpoint);
			});

			it('should remove token from localStorage', async () => {
				await signout();
				expect(localStorage.removeItem).toHaveBeenCalledWith('token');
			});

			it('should unset the user', async () => {
				await signout();
				expect(get(mocks.user)).toEqual(null);
			});
		});
	});
});
