import { describe, beforeEach, expect, it, vi } from 'vitest';
import {
	LOCALSTORAGE_SHOW_LOGIN_FORM,
	isShowLoginForm,
} from './auth';

vi.stubGlobal('localStorage', {
	getItem: vi.fn(),
	setItem: vi.fn(),
	removeItem: vi.fn(),
});

describe('auth', () => {
	beforeEach(() => {
		vi.resetAllMocks();
	});

	describe('isShowLoginForm()', () => {
		function mockLocalStorage(key: string, value: string|null) {
			vi.mocked(localStorage.getItem).mockImplementation((requestedKey: string) => {
				if (requestedKey === key) {
					return value;
				}
				return null;
			});
		}

		it('should default to false', async () => {
			expect(isShowLoginForm()).toBe(false);
		});

		it('should return false if set to false in localStorage', async () => {
			mockLocalStorage(LOCALSTORAGE_SHOW_LOGIN_FORM, 'false');
			expect(isShowLoginForm()).toBe(false);
		});

		it('should return true if set to true in localStorage', async () => {
			mockLocalStorage(LOCALSTORAGE_SHOW_LOGIN_FORM, 'true');
			expect(isShowLoginForm()).toBe(true);
		});
	});
});
