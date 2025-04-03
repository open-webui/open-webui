import { describe, beforeEach, expect, it, vi } from 'vitest';
import {
	resetPassword,
} from './account';

const mocks = vi.hoisted(() => {
	return {
		stores: {
			config: {
				subscribe: vi.fn(),
			},
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
});
