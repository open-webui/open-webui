import { describe, beforeEach, expect, it, vi } from 'vitest';
import {
	resetPassword,
	deleteAccount,
} from './account';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Config = Record<string, any>;
type ConfigSubscriber = (config: Config) => void

const mocks = vi.hoisted(() => {
	return {
		stores: {
			config: {
				subscribe: vi.fn(),
			},
		},
		apis: {
			users: {
				deleteAccount: vi.fn(),
			}
		},
		services: {
			auths: {
				signout: vi.fn(),
			}
		}
	};
});

vi.mock('$lib/stores', async () => {
	return {
		config: mocks.stores.config,
	};
});

vi.mock('$lib/services/auths', async () => {
	return {
		signout: mocks.services.auths.signout,
	};
});

vi.mock('$lib/IONOS/apis/users', async () => {
	return {
		deleteAccount: mocks.apis.users.deleteAccount,
	};
});

vi.stubGlobal('localStorage', {
	token: 'mock-token',
});

describe('account', () => {
	const mockPasswordResetUrl = 'https://acmeauth.local/password-reset';

	function mockConfig(config: Config) {
		mocks.stores.config.subscribe.mockImplementation((subscriber: ConfigSubscriber) => {
			subscriber(config);
			return () => { };
		});
	}

	beforeEach(() => {
		vi.resetAllMocks();

		mockConfig({
			features: {
				ionos_password_reset_url: mockPasswordResetUrl,
			},
		});
	});

	describe('resetPassword()', () => {
		it('should pass the value of ionos_password_reset_url to signout()', async () => {
			await resetPassword();
			expect(mocks.services.auths.signout).toHaveBeenCalledWith(mockPasswordResetUrl);
		});
	});

	describe('deleteAccount()', () => {
		it('should call deleteAccount() on API, then signout', async () => {
			const order: string[] = [];

			mocks.apis.users.deleteAccount.mockImplementation(() => order.push('deleteAccount'));
			mocks.services.auths.signout.mockImplementation(() => order.push('signout'));

			await deleteAccount();

			expect(mocks.apis.users.deleteAccount).toHaveBeenCalledWith(localStorage.token);
			expect(mocks.services.auths.signout).toHaveBeenCalled();
			expect(order).toEqual(['deleteAccount', 'signout']);
		});
	});
});
