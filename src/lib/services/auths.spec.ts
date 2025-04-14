import { describe, beforeEach, expect, it, vi } from 'vitest';
import { writable } from 'svelte/store';
import { signout } from '$lib/services/auths';

const mocks = vi.hoisted(() => {
	return {
		originUrl: 'https://gpt.local/somewhere',
		ionos_logout_url: 'https://auth.local/logout',
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

	return {
		config: mocks.config,
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
			features: {
				ionos_logout_url: mocks.ionos_logout_url,
			},
		});
		location.href = mocks.originUrl;
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
		describe('no OIDC and no ionos_logout_url', () => {
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
		});

		describe('has no ionos_logout_url with OIDC configured and no end_session_endpoint was sent', () => {
			beforeEach(() => {
				mocks.config.set({
					// No ionos_logout_url
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

			it('should throw if no end_session_endpoint was sent', async () => {
				await expect(signout()).rejects.toThrowError('OIDC configured but no end_session_endpoint sent');
			});
		});

		describe('has no ionos_logout_url with OIDC configured and end_session_endpoint works', () => {
			const endpoint = 'https://acmeauth.com/logout';

			beforeEach(() => {
				mocks.config.set({
					// No ionos_logout_url
					oauth: {
						providers: {
							oidc: 'Test',
						},
					},
				});

				mocks.userSignOut.mockImplementation(() => ({ status: true, end_session_endpoint: endpoint }));
			});

			it('should remove token from localStorage', async () => {
				await signout();
				expect(localStorage.removeItem).toHaveBeenCalledWith('token');
			});

			it('should set location to the end_session_endpoint', async () => {
				await signout();

				const postLogoutUrl = new URL(mocks.originUrl);
				postLogoutUrl.pathname = '/explore';
				const logoutUrl = new URL(endpoint);
				logoutUrl.searchParams.set('post_logout_redirect_uri', postLogoutUrl);
				expect(location.href).toBe(logoutUrl.toString());
			});
		});

		// Can happen with certain Minikube configurations
		describe('has no (empty string) ionos_logout_url with OIDC configured and end_session_endpoint works', () => {
			const endpoint = 'https://acmeauth.com/logout';

			beforeEach(() => {
				mocks.config.set({
					oauth: {
						providers: {
							oidc: 'Test',
						},
					},
					features: {
						// Empty string = effectively disabled
						ionos_logout_url: ''
					},
				});

				mocks.userSignOut.mockImplementation(() => ({ status: true, end_session_endpoint: endpoint }));
			});

			it('should remove token from localStorage', async () => {
				await signout();
				expect(localStorage.removeItem).toHaveBeenCalledWith('token');
			});

			it('should set location to the end_session_endpoint', async () => {
				await signout();

				const postLogoutUrl = new URL(mocks.originUrl);
				postLogoutUrl.pathname = '/explore';
				const logoutUrl = new URL(endpoint);
				logoutUrl.searchParams.set('post_logout_redirect_uri', postLogoutUrl);
				expect(location.href).toBe(logoutUrl.toString());
			});
		});

		describe('has end_session_endpoint', () => {
			beforeEach(() => {
				mocks.userSignOut.mockImplementation(() => ({ status: true, end_session_endpoint: 'https://doesnotmatter.local/' }));
			});

			it('should set location to ionos_logout_url with redirect_url set to /explore', async () => {
				const postLogoutUrl = new URL(mocks.originUrl);
				postLogoutUrl.pathname = '/explore';
				const logoutUrl = new URL(mocks.ionos_logout_url);
				logoutUrl.searchParams.set('redirect_url', postLogoutUrl);
				await signout();
				expect(location.href).toBe(logoutUrl.toString());
			});

			it('should remove token from localStorage', async () => {
				await signout();
				expect(localStorage.removeItem).toHaveBeenCalledWith('token');
			});
		});
	});
});
