/**
 * Centralized Authentication Redirect Handling
 * 
 * This module centralizes all authentication redirect logic to prevent:
 * - Redirect loops
 * - Inconsistent redirect behavior
 * - Treating auth expiry as errors
 * 
 * It works in both PWA and browser contexts, handling:
 * - Trusted header / forward authentication redirects
 * - Standard form-based authentication
 * - OAuth redirects
 */

import { goto } from '$app/navigation';
import { page } from '$app/stores';
import { get } from 'svelte/store';
import { AuthState, AuthMode, type AuthMetadata, authMetadata } from './authState';

/**
 * Redirect context information
 */
interface RedirectContext {
	/**
	 * Current page path
	 */
	currentPath: string;
	
	/**
	 * Current page query string
	 */
	currentQuery: string;
	
	/**
	 * Whether we're in a PWA context
	 */
	isPWA: boolean;
}

/**
 * Get current redirect context
 * 
 * @returns Redirect context
 */
function getRedirectContext(): RedirectContext {
	const currentPage = get(page);
	return {
		currentPath: currentPage.url.pathname,
		currentQuery: currentPage.url.search,
		isPWA: window.matchMedia('(display-mode: standalone)').matches || 
		       (window.navigator as any).standalone === true ||
		       document.referrer.includes('android-app://')
	};
}

/**
 * Check if we're already on an auth-related page
 * 
 * @param pathname - Current pathname
 * @returns true if on auth page
 */
function isOnAuthPage(pathname: string): boolean {
	return pathname === '/auth' || pathname === '/error';
}

/**
 * Check if redirect would cause a loop
 * 
 * @param targetPath - Target path to redirect to
 * @param currentPath - Current path
 * @returns true if redirect would loop
 */
function wouldCauseRedirectLoop(targetPath: string, currentPath: string): boolean {
	// Prevent redirecting to the same page
	if (targetPath === currentPath) {
		return true;
	}
	
	// Prevent redirecting from /auth to /auth
	if (targetPath === '/auth' && currentPath === '/auth') {
		return true;
	}
	
	return false;
}

/**
 * Handle redirect for trusted header authentication
 * 
 * When using trusted header auth, the reverse proxy handles redirects.
 * We need to trigger a full page navigation so the proxy can intercept.
 * 
 * @param context - Redirect context
 * @param metadata - Auth metadata
 */
function handleTrustedHeaderRedirect(context: RedirectContext, metadata: AuthMetadata): void {
	// For trusted header auth, redirect to /auth which will be intercepted by reverse proxy
	// Use window.location.href for full page navigation in PWA context
	if (context.isPWA) {
		const encodedUrl = encodeURIComponent(`${context.currentPath}${context.currentQuery}`);
		window.location.href = `/auth?redirect=${encodedUrl}`;
	} else {
		// In browser context, use SvelteKit navigation
		const encodedUrl = encodeURIComponent(`${context.currentPath}${context.currentQuery}`);
		goto(`/auth?redirect=${encodedUrl}`);
	}
}

/**
 * Handle redirect for standard form-based authentication
 * 
 * @param context - Redirect context
 */
function handleFormAuthRedirect(context: RedirectContext): void {
	// For form auth, redirect to /auth page
	if (!isOnAuthPage(context.currentPath)) {
		const encodedUrl = encodeURIComponent(`${context.currentPath}${context.currentQuery}`);
		goto(`/auth?redirect=${encodedUrl}`);
	}
}

/**
 * Handle redirect for OAuth authentication
 * 
 * @param context - Redirect context
 * @param metadata - Auth metadata
 */
function handleOAuthRedirect(context: RedirectContext, metadata: AuthMetadata): void {
	// OAuth redirects are handled by the OAuth provider
	// Redirect to /auth which will initiate OAuth flow
	if (!isOnAuthPage(context.currentPath)) {
		const encodedUrl = encodeURIComponent(`${context.currentPath}${context.currentQuery}`);
		goto(`/auth?redirect=${encodedUrl}`);
	}
}

/**
 * Determine redirect target based on authentication mode
 * 
 * @param metadata - Auth metadata
 * @returns Redirect target path
 */
function getRedirectTarget(metadata: AuthMetadata | null): string {
	if (!metadata) {
		// Default to /auth if no metadata available
		return '/auth';
	}
	
	switch (metadata.mode) {
		case AuthMode.TRUSTED_HEADER:
			// Trusted header auth redirects to /auth (proxy handles external redirect)
			return '/auth';
		case AuthMode.OAUTH:
			return '/auth';
		case AuthMode.FORM:
		case AuthMode.LDAP:
			return '/auth';
		case AuthMode.NONE:
			// No auth required, shouldn't redirect
			return '/';
		default:
			return '/auth';
	}
}

/**
 * Handle authentication redirect
 * 
 * This is the main entry point for all authentication redirects.
 * It determines the appropriate redirect strategy based on:
 * - Current authentication state
 * - Authentication mode
 * - Current page context
 * - PWA vs browser context
 * 
 * @param authState - Current authentication state
 * @param metadata - Authentication metadata
 * @param forceRedirect - Force redirect even if already on auth page
 */
export function handleAuthRedirect(
	authState: AuthState,
	metadata: AuthMetadata | null,
	forceRedirect: boolean = false
): void {
	// Only redirect if unauthenticated
	if (authState !== AuthState.UNAUTHENTICATED) {
		return;
	}
	
	const context = getRedirectContext();
	
	// Check if we're already on an auth page
	if (isOnAuthPage(context.currentPath) && !forceRedirect) {
		return;
	}
	
	// Get redirect target
	const targetPath = getRedirectTarget(metadata);
	
	// Prevent redirect loops
	if (wouldCauseRedirectLoop(targetPath, context.currentPath)) {
		console.warn('Prevented redirect loop:', { from: context.currentPath, to: targetPath });
		return;
	}
	
	// Handle redirect based on auth mode
	if (metadata) {
		switch (metadata.mode) {
			case AuthMode.TRUSTED_HEADER:
				handleTrustedHeaderRedirect(context, metadata);
				break;
			case AuthMode.OAUTH:
				handleOAuthRedirect(context, metadata);
				break;
			case AuthMode.FORM:
			case AuthMode.LDAP:
				handleFormAuthRedirect(context);
				break;
			case AuthMode.NONE:
				// No redirect needed
				break;
		}
	} else {
		// Fallback to form auth if no metadata
		handleFormAuthRedirect(context);
	}
}

/**
 * Check if redirect is needed based on authentication state
 * 
 * @param authState - Current authentication state
 * @param metadata - Authentication metadata
 * @returns true if redirect is needed
 */
export function shouldRedirect(authState: AuthState, metadata: AuthMetadata | null): boolean {
	if (authState !== AuthState.UNAUTHENTICATED) {
		return false;
	}
	
	const context = getRedirectContext();
	
	// Don't redirect if already on auth page
	if (isOnAuthPage(context.currentPath)) {
		return false;
	}
	
	// Don't redirect if auth is disabled
	if (metadata?.mode === AuthMode.NONE) {
		return false;
	}
	
	return true;
}

/**
 * Handle authentication state change
 * 
 * This function should be called whenever authentication state changes.
 * It will automatically handle redirects if needed.
 * 
 * @param newState - New authentication state
 * @param metadata - Authentication metadata
 */
export function onAuthStateChange(
	newState: AuthState,
	metadata: AuthMetadata | null
): void {
	if (shouldRedirect(newState, metadata)) {
		handleAuthRedirect(newState, metadata);
	}
}
