import { describe, beforeEach, expect, it, vi } from 'vitest';
import {
	LOCALSTORAGE_REFERRED_TO_SIGNUP,
	signup,
	handleSignupDone,
} from './signup';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Config = Record<string, any>;
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type User = any;
type ConfigSubscriber = (config: Config) => void
type UserSubscriber = (user: User) => void

const mocks = vi.hoisted(() => {
	return {
		stores: {
			config: {
				subscribe: vi.fn(),
			},
			user: {
				subscribe: vi.fn(),
			},
		},
		navigation: {
			goto: vi.fn(),
		},
	};
});

vi.mock('$lib/stores', async () => {
	return {
		config: mocks.stores.config,
		user: mocks.stores.user,
	};
});

vi.mock('$app/navigation', async () => {
	return {
		goto: mocks.navigation.goto,
	};
});

vi.stubGlobal('window', {
	location: { href: 'unset' },
});

vi.stubGlobal('localStorage', {
	getItem: vi.fn(),
	setItem: vi.fn(),
	removeItem: vi.fn(),
});

describe('signup', () => {
	function mockConfig(config: Config) {
		mocks.stores.config.subscribe.mockImplementation((subscriber: ConfigSubscriber) => {
			subscriber(config);
			return () => { };
		});
	}

	function mockUser(user: User|undefined) {
		mocks.stores.user.subscribe.mockImplementation((subscriber: UserSubscriber) => {
			subscriber(user);
			return () => { };
		});
	}

	function mockLocalStoage(key: string, value: string|null) {
		vi.mocked(localStorage.getItem).mockImplementation((requestedKey: string) => {
			if (requestedKey === key) {
				return value;
			}
			return null;
		});
	}

	const mockRegistrationUrl = 'http://registration/';

	beforeEach(() => {
		vi.resetAllMocks();
		window.location.href = 'unset';
	});

	describe('signup()', () => {
		it('should set a marker in localStorage then rediect to the configured signup URL if configured', () => {
			mockConfig({
				features: {
					ionos_registration_url: mockRegistrationUrl,
				},
			});

			signup();

			expect(localStorage.setItem).toHaveBeenCalledWith(LOCALSTORAGE_REFERRED_TO_SIGNUP, 'true');
			expect(window.location.href).toBe(mockRegistrationUrl);
		});

		it('should set a marker in localStorage and not redirect if no signup URL is configured', () => {
			mockConfig({
				features: {
					ionos_registration_url: null,
				},
			});

			signup();

			expect(localStorage.setItem).toHaveBeenCalledWith(LOCALSTORAGE_REFERRED_TO_SIGNUP, 'true');
			expect(window.location.href).toBe('unset');
		});
	});

	describe('handleSignupDone()', () => {
		describe('user is authenticated and went through signup', () => {
			beforeEach(() => {
				mockLocalStoage(LOCALSTORAGE_REFERRED_TO_SIGNUP, 'true');
				mockUser({ /* mock user */ });
				handleSignupDone();
			});

			it('should redirect', () => {
				expect(mocks.navigation.goto).toHaveBeenCalledWith('/explore');
			});

			it('should remove an item from localStorage', () => {
				expect(localStorage.removeItem).toHaveBeenCalledWith(LOCALSTORAGE_REFERRED_TO_SIGNUP);
			});
		});

		describe('user is authenticated and did not go through signup', () => {
			beforeEach(() => {
				mockLocalStoage(LOCALSTORAGE_REFERRED_TO_SIGNUP, 'false');
				mockUser({ /* mock user */ });
				handleSignupDone();
			});

			it('should not redirect', () => {
				expect(mocks.navigation.goto).not.toHaveBeenCalled();
			});

			it('should not remove an item from localStorage', () => {
				expect(localStorage.removeItem).not.toHaveBeenCalledWith(LOCALSTORAGE_REFERRED_TO_SIGNUP);
			});
		});

		describe('user is not authenticated and went through signup', () => {
			beforeEach(() => {
				mockLocalStoage(LOCALSTORAGE_REFERRED_TO_SIGNUP, 'true');
				mockUser(undefined);
				handleSignupDone();
			});

			it('should not redirect', () => {
				expect(mocks.navigation.goto).not.toHaveBeenCalled();
			});

			it('should not remove an item from localStorage', () => {
				expect(localStorage.removeItem).not.toHaveBeenCalledWith(LOCALSTORAGE_REFERRED_TO_SIGNUP);
			});
		});

		describe('user is not authenticated and did not go through signup', () => {
			beforeEach(() => {
				mockLocalStoage(LOCALSTORAGE_REFERRED_TO_SIGNUP, 'false');
				mockUser(undefined);
				handleSignupDone();
			});

			it('should not redirect', () => {
				expect(mocks.navigation.goto).not.toHaveBeenCalled();
			});

			it('should not remove an item from localStorage', () => {
				expect(localStorage.removeItem).not.toHaveBeenCalledWith(LOCALSTORAGE_REFERRED_TO_SIGNUP);
			});
		});
	});
});
