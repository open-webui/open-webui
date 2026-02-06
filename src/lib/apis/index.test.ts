import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getBackendConfig } from './index';
import { WEBUI_BASE_URL } from '$lib/constants';

// Mock the utils module with dynamic import
const mockIsAuthRedirectError = vi.fn();
const mockHandleAuthRedirect = vi.fn();

vi.mock('$lib/utils', () => ({
	isAuthRedirectError: (error: any) => mockIsAuthRedirectError(error),
	handleAuthRedirect: (url?: string | null) => mockHandleAuthRedirect(url)
}));

describe('getBackendConfig - Authentication Redirect Handling', () => {
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
		
		// Reset mocks
		vi.clearAllMocks();
		mockIsAuthRedirectError.mockReset();
		mockHandleAuthRedirect.mockReset();
	});

	afterEach(() => {
		// Restore originals
		global.fetch = originalFetch;
		window.location = originalLocation;
	});

	it('should successfully fetch config when authenticated', async () => {
		const mockConfig = {
			name: 'Open WebUI',
			version: '0.7.2',
			features: {
				auth: true,
				auth_trusted_header: false
			}
		};

		global.fetch = vi.fn().mockResolvedValue({
			ok: true,
			json: async () => mockConfig
		} as Response);

		const result = await getBackendConfig();
		
		expect(result).toEqual(mockConfig);
		expect(global.fetch).toHaveBeenCalledWith(
			`${WEBUI_BASE_URL}/api/config`,
			expect.objectContaining({
				method: 'GET',
				credentials: 'include',
				headers: {
					'Content-Type': 'application/json'
				}
			})
		);
	});

	it('should handle CORS-blocked authentication redirect errors', async () => {
		// Mock CORS error
		const corsError = new Error('Failed to fetch');
		corsError.name = 'TypeError';
		
		global.fetch = vi.fn().mockRejectedValue(corsError);
		
		// Mock isAuthRedirectError to return true
		mockIsAuthRedirectError.mockReturnValue(true);
		
		// Mock localStorage to return a signout URL
		mockLocalStorage.getItem = vi.fn((key: string) => {
			if (key === 'signout_redirect_url') {
				return 'https://auth.example.com/logout';
			}
			return null;
		});

		await expect(getBackendConfig()).rejects.toThrow('AUTH_REDIRECT');
		
		expect(mockIsAuthRedirectError).toHaveBeenCalledWith(corsError);
		expect(mockHandleAuthRedirect).toHaveBeenCalledWith('https://auth.example.com/logout');
	});

	it('should reload page when no signout URL is stored', async () => {
		const corsError = new Error('Failed to fetch');
		corsError.name = 'TypeError';
		
		global.fetch = vi.fn().mockRejectedValue(corsError);
		mockIsAuthRedirectError.mockReturnValue(true);
		mockLocalStorage.getItem = vi.fn(() => null);

		await expect(getBackendConfig()).rejects.toThrow('AUTH_REDIRECT');
		
		expect(mockHandleAuthRedirect).toHaveBeenCalledWith(null);
	});

	it('should store signout redirect URL from config response', async () => {
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

		await getBackendConfig();
		
		expect(mockLocalStorage.setItem).toHaveBeenCalledWith(
			'signout_redirect_url',
			'https://auth.example.com/logout'
		);
	});

	it('should not store signout URL when auth_trusted_header is false', async () => {
		const mockConfig = {
			name: 'Open WebUI',
			version: '0.7.2',
			features: {
				auth: true,
				auth_trusted_header: false,
				signout_redirect_url: 'https://auth.example.com/logout'
			}
		};

		global.fetch = vi.fn().mockResolvedValue({
			ok: true,
			json: async () => mockConfig
		} as Response);

		await getBackendConfig();
		
		expect(mockLocalStorage.setItem).not.toHaveBeenCalledWith(
			'signout_redirect_url',
			expect.any(String)
		);
	});

	it('should throw regular errors for non-auth redirect failures', async () => {
		const regularError = new Error('Server error');
		global.fetch = vi.fn().mockRejectedValue(regularError);
		mockIsAuthRedirectError.mockReturnValue(false);

		await expect(getBackendConfig()).rejects.toThrow('Server error');
	});

	it('should handle HTTP error responses', async () => {
		const errorResponse = { detail: 'Invalid token' };
		
		global.fetch = vi.fn().mockResolvedValue({
			ok: false,
			json: async () => errorResponse
		} as Response);

		await expect(getBackendConfig()).rejects.toEqual(errorResponse);
	});

	it('should handle network errors that are not auth redirects', async () => {
		const networkError = new Error('Network timeout');
		global.fetch = vi.fn().mockRejectedValue(networkError);
		mockIsAuthRedirectError.mockReturnValue(false);

		await expect(getBackendConfig()).rejects.toThrow('Network timeout');
	});

	it('should handle auth redirect error with special flag', async () => {
		const corsError = new Error('CORS error');
		global.fetch = vi.fn().mockRejectedValue(corsError);
		mockIsAuthRedirectError.mockReturnValue(true);
		mockLocalStorage.getItem = vi.fn(() => null);

		try {
			await getBackendConfig();
		} catch (error: any) {
			expect(error.message).toBe('AUTH_REDIRECT');
			expect(error.isAuthRedirect).toBe(true);
		}
	});
});
