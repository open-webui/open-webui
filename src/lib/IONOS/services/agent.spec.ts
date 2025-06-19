import type { Unsubscriber } from 'svelte/store';
import { describe, beforeEach, expect, it, vi } from 'vitest';
import type { SessionUser } from '$lib/stores';
import {
	LOCALSTORAGE_START_MODEL_KEY,
	getAndForgetAgent,
	selectAgent,
	hasAgent,
} from './agent';

const mocks = vi.hoisted(() => {
	return {
		navigation: {
			goto: vi.fn(),
		},
		stores: {
			user: {
				subscribe: vi.fn(),
			},
		},
	};
});

vi.mock('$app/navigation', async () => {
	return {
		goto: mocks.navigation.goto,
	};
});

vi.mock('$lib/stores', async () => {
	return {
		user: mocks.stores.user,
	};
});

vi.stubGlobal('localStorage', {
	getItem: vi.fn(),
	setItem: vi.fn(),
	removeItem: vi.fn(),
});

type SessionUserSubscriberFn = (user: SessionUser|null) => void;

describe('agent', () => {
	function mockUser(user: SessionUser|null) {
		mocks.stores.user.subscribe.mockImplementation((subscriberFn: SessionUserSubscriberFn): Unsubscriber => {
			subscriberFn(user);
			return () => { }
		});
	}

	beforeEach(() => {
		vi.resetAllMocks();
	});

	describe('getAndForgetAgent()', () => {
		const mockValue = 'mock-agent-id';

		beforeEach(() => {
			vi.mocked(localStorage.getItem).mockImplementation((key: string): string|null => {
				if (key === LOCALSTORAGE_START_MODEL_KEY) {
					return mockValue;
				}
				return null;
			});
		});

		it('should return the agent from storage', () => {
			expect(getAndForgetAgent()).toBe(mockValue);
		});

		it('should remove the agent from storage', () => {
			getAndForgetAgent();
			expect(localStorage.removeItem).toHaveBeenCalledWith(LOCALSTORAGE_START_MODEL_KEY);
		});

		it('should return an empty string if not found in storage', () => {
			vi.mocked(localStorage.getItem).mockImplementation((): string|null => {
				return null;
			});
			expect(getAndForgetAgent()).toBe('');
		});
	});

	describe('hasAgent()', () => {
		const mockValue = 'mock-agent-id';

		beforeEach(() => {
			vi.mocked(localStorage.getItem).mockImplementation((key: string): string|null => {
				if (key === LOCALSTORAGE_START_MODEL_KEY) {
					return mockValue;
				}
				return null;
			});
		});

		it('should return true if the agent is in storage', () => {
			expect(hasAgent()).toBe(true);
		});

		it('should return false if the agent is not found in storage', () => {
			vi.mocked(localStorage.getItem).mockImplementation((): string|null => {
				return null;
			});
			expect(hasAgent()).toBe(false);
		});
	});

	describe('selectAgent()', () => {
		const mockValue = 'mock-agent-id';

		beforeEach(() => {
			// Not authenticated
			mockUser(null);
		});

		it('should store the agent ID in localStorage', async () => {
			await selectAgent(mockValue);
			expect(localStorage.setItem).toHaveBeenCalledWith(LOCALSTORAGE_START_MODEL_KEY, mockValue);
		});

		it('should redirect the user to / if authenticated', async () => {
			mockUser({
				id: 'foo-id-123',
				email: 'foo@bar',
				name: 'foo',
				role: 'user',
				profile_image_url: '',
				created_at: 0,
			});
			await selectAgent(mockValue);
			expect(mocks.navigation.goto).toHaveBeenCalledWith('/');
		});

		it('should redirect the user to /auth if not authenticated', async () => {
			await selectAgent(mockValue);
			expect(mocks.navigation.goto).toHaveBeenCalledWith('/auth');
		});
	});
});
