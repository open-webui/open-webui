import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { isAuthRedirectError, handleAuthRedirect } from './index';

describe('isAuthRedirectError', () => {
	it('should detect CORS errors', () => {
		const error = new Error('Access to fetch at \'https://auth.example.com/\' (redirected from \'https://app.example.com/api/config\') has been blocked by CORS policy: No \'Access-Control-Allow-Origin\' header is present on the requested resource.');
		expect(isAuthRedirectError(error)).toBe(true);
	});

	it('should detect ERR_FAILED network errors', () => {
		const error = new Error('Failed to fetch');
		error.name = 'TypeError';
		expect(isAuthRedirectError(error)).toBe(true);
	});

	it('should detect NetworkError', () => {
		const error = new Error('Network request failed');
		error.name = 'NetworkError';
		expect(isAuthRedirectError(error)).toBe(true);
	});

	it('should detect errors with status 0', () => {
		const error: any = { status: 0, message: 'Network error' };
		expect(isAuthRedirectError(error)).toBe(true);
	});

	it('should detect errors with ok=false and no status', () => {
		const error: any = { ok: false, message: 'Request failed' };
		expect(isAuthRedirectError(error)).toBe(true);
	});

	it('should detect errors containing "redirected from"', () => {
		const error = new Error('Request redirected from https://app.example.com/api/config');
		expect(isAuthRedirectError(error)).toBe(true);
	});

	it('should return false for regular errors', () => {
		const error = new Error('Some other error');
		expect(isAuthRedirectError(error)).toBe(false);
	});

	it('should return false for null/undefined', () => {
		expect(isAuthRedirectError(null)).toBe(false);
		expect(isAuthRedirectError(undefined)).toBe(false);
	});

	it('should handle errors with only message string', () => {
		const error: any = { message: 'Failed to fetch' };
		expect(isAuthRedirectError(error)).toBe(true);
	});

	it('should handle errors with only name', () => {
		const error: any = { name: 'TypeError' };
		expect(isAuthRedirectError(error)).toBe(false); // Needs message or status to be true
	});
});

describe('handleAuthRedirect', () => {
	let originalLocation: Location;
	let mockLocation: any;

	beforeEach(() => {
		// Save original location
		originalLocation = window.location;
		
		// Create mock location
		mockLocation = {
			href: 'https://app.example.com/',
			reload: vi.fn(),
			replace: vi.fn()
		};
		
		// Mock window.location
		delete (window as any).location;
		window.location = mockLocation as any;
	});

	afterEach(() => {
		// Restore original location
		window.location = originalLocation;
	});

	it('should redirect to signout URL when provided', () => {
		const signoutUrl = 'https://auth.example.com/logout';
		handleAuthRedirect(signoutUrl);
		
		expect(mockLocation.href).toBe(signoutUrl);
	});

	it('should reload current page when signout URL is not provided', () => {
		const currentUrl = 'https://app.example.com/current-page';
		mockLocation.href = currentUrl;
		
		handleAuthRedirect(null);
		
		expect(mockLocation.href).toBe(currentUrl);
	});

	it('should reload current page when signout URL is empty string', () => {
		const currentUrl = 'https://app.example.com/';
		mockLocation.href = currentUrl;
		
		handleAuthRedirect('');
		
		expect(mockLocation.href).toBe(currentUrl);
	});

	it('should handle undefined signout URL', () => {
		const currentUrl = 'https://app.example.com/';
		mockLocation.href = currentUrl;
		
		handleAuthRedirect(undefined);
		
		expect(mockLocation.href).toBe(currentUrl);
	});
});
