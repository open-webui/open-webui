/**
 * Integration tests for authentication redirect handling
 * These tests verify the complete flow of detecting and handling auth redirects
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getBackendConfig } from './index';
import { WEBUI_BASE_URL } from '$lib/constants';
import * as utils from '$lib/utils';

describe('getBackendConfig - Integration Tests', () => {
	let originalFetch: typeof fetch;
	let originalLocation: Location;
	let mockLocation: any;
	let mockLocalStorage: Storage;

	beforeEach(() => {
		// Save originals
		originalFetch = global.fetch;
		originalLocation = window.location;
		
		// Mock localStorage
		mockLocalStorage = {
			getItem: vi.fn(),
			setItem: vi.fn(),
			removeItem: vi.fn(),
			clear: vi.fn(),
			length: 0,
			key: vi.fn()
		};
		Object.defineProperty(window, 'localStorage', {
			value: mockLocalStorage,
			writable: true
		});
		
		// Mock location
		mockLocation = {
			href: 'https://app.example.com/',
			reload: vi.fn(),
			replace: vi.fn()
		};
		delete (window as any).location;
		window.location = mockLocation as any;
	});

	afterEach(() => {
		// Restore originals
		global.fetch = originalFetch;
		window.location = originalLocation;
		vi.restoreAllMocks();
	});

	it('should handle complete auth redirect flow with stored signout URL', async () => {
		// Simulate CORS error from reverse proxy redirect
		const corsError = new TypeError('Failed to fetch');
		global.fetch = vi.fn().mockRejectedValue(corsError);
		
		// Mock localStorage to return stored signout URL
		mockLocalStorage.getItem = vi.fn((key: string) => {
			if (key === 'signout_redirect_url') {
				return 'https://auth.example.com/flows/-/default/invalidation/';
			}
			return null;
		});

		// Spy on utils functions
		const isAuthRedirectErrorSpy = vi.spyOn(utils, 'isAuthRedirectError');
		const handleAuthRedirectSpy = vi.spyOn(utils, 'handleAuthRedirect');
		
		// Mock the functions to work as expected
		isAuthRedirectErrorSpy.mockReturnValue(true);

		await expect(getBackendConfig()).rejects.toThrow('AUTH_REDIRECT');
		
		// Verify error detection
		expect(isAuthRedirectErrorSpy).toHaveBeenCalledWith(corsError);
		
		// Verify redirect was triggered with stored URL
		expect(handleAuthRedirectSpy).toHaveBeenCalledWith(
			'https://auth.example.com/flows/-/default/invalidation/'
		);
		
		// Verify location was updated
		expect(mockLocation.href).toBe('https://auth.example.com/flows/-/default/invalidation/');
	});

	it('should handle auth redirect flow without stored signout URL', async () => {
		const corsError = new TypeError('Failed to fetch');
		global.fetch = vi.fn().mockRejectedValue(corsError);
		mockLocalStorage.getItem = vi.fn(() => null);

		const isAuthRedirectErrorSpy = vi.spyOn(utils, 'isAuthRedirectError');
		const handleAuthRedirectSpy = vi.spyOn(utils, 'handleAuthRedirect');
		
		isAuthRedirectErrorSpy.mockReturnValue(true);

		await expect(getBackendConfig()).rejects.toThrow('AUTH_REDIRECT');
		
		expect(handleAuthRedirectSpy).toHaveBeenCalledWith(null);
		
		// Should reload current page
		expect(mockLocation.href).toBe('https://app.example.com/');
	});

	it('should store signout URL from successful config response', async () => {
		const mockConfig = {
			name: 'Open WebUI',
			version: '0.7.2',
			features: {
				auth: true,
				auth_trusted_header: true,
				signout_redirect_url: 'https://auth.example.com/logout'
			}
		};

		global.fetch = vi.fn().mockResolvedValue({
			ok: true,
			json: async () => mockConfig
		} as Response);

		const result = await getBackendConfig();
		
		expect(result).toEqual(mockConfig);
		expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
			'signout_redirect_url',
			'https://auth.example.com/logout'
		);
	});

	it('should handle ERR_FAILED network error as auth redirect', async () => {
		const networkError: any = new Error('net::ERR_FAILED');
		networkError.name = 'TypeError';
		
		global.fetch = vi.fn().mockRejectedValue(networkError);
		mockLocalStorage.getItem = vi.fn(() => null);

		const isAuthRedirectErrorSpy = vi.spyOn(utils, 'isAuthRedirectError');
		isAuthRedirectErrorSpy.mockReturnValue(true);

		await expect(getBackendConfig()).rejects.toThrow('AUTH_REDIRECT');
		
		expect(isAuthRedirectErrorSpy).toHaveBeenCalledWith(networkError);
	});

	it('should handle error with status 0 as auth redirect', async () => {
		const statusError: any = { status: 0, message: 'Network error' };
		global.fetch = vi.fn().mockRejectedValue(statusError);
		mockLocalStorage.getItem = vi.fn(() => null);

		const isAuthRedirectErrorSpy = vi.spyOn(utils, 'isAuthRedirectError');
		isAuthRedirectErrorSpy.mockReturnValue(true);

		await expect(getBackendConfig()).rejects.toThrow('AUTH_REDIRECT');
	});
});
