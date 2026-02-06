/**
 * Authentication State Management
 * 
 * This module provides a first-class authentication state model that distinguishes
 * between authentication states (authenticated, unauthenticated, unknown) rather
 * than inferring state from errors.
 * 
 * Why this approach:
 * - Authentication expiry is a state transition, not an error condition
 * - Network/CORS failures during auth redirects indicate unauthenticated state
 * - Explicit state prevents treating auth issues as generic backend errors
 */

import { writable, type Writable } from 'svelte/store';

/**
 * Authentication state enumeration
 */
export enum AuthState {
	/**
	 * User authentication status is unknown (initial state, before first check)
	 */
	UNKNOWN = 'unknown',
	
	/**
	 * User is authenticated and has valid session
	 */
	AUTHENTICATED = 'authenticated',
	
	/**
	 * User is not authenticated (no session, expired session, or auth redirect required)
	 */
	UNAUTHENTICATED = 'unauthenticated'
}

/**
 * Authentication mode enumeration
 */
export enum AuthMode {
	/**
	 * Standard form-based authentication
	 */
	FORM = 'form',
	
	/**
	 * Trusted header / forward authentication (e.g., Authentik, Traefik)
	 */
	TRUSTED_HEADER = 'trusted-header',
	
	/**
	 * OAuth/OIDC authentication
	 */
	OAUTH = 'oauth',
	
	/**
	 * LDAP authentication
	 */
	LDAP = 'ldap',
	
	/**
	 * Authentication disabled
	 */
	NONE = 'none'
}

/**
 * Authentication metadata from backend
 */
export interface AuthMetadata {
	/**
	 * Current authentication mode
	 */
	mode: AuthMode;
	
	/**
	 * Whether the backend expects redirects on unauthenticated requests
	 */
	redirectOnUnauthenticated: boolean;
	
	/**
	 * External signout redirect URL (for trusted header auth)
	 */
	signoutRedirectUrl?: string;
	
	/**
	 * Whether trusted header authentication is enabled
	 */
	trustedHeaderEnabled: boolean;
	
	/**
	 * Whether login form is enabled
	 */
	loginFormEnabled: boolean;
	
	/**
	 * Whether signup is enabled
	 */
	signupEnabled: boolean;
}

/**
 * Authentication state store
 * 
 * Tracks the current authentication state across the application.
 * Components should subscribe to this store to react to auth state changes.
 */
export const authState: Writable<AuthState> = writable<AuthState>(AuthState.UNKNOWN);

/**
 * Authentication metadata store
 * 
 * Contains authentication configuration from the backend.
 */
export const authMetadata: Writable<AuthMetadata | null> = writable<AuthMetadata | null>(null);

/**
 * Set authentication state
 * 
 * @param state - The new authentication state
 */
export function setAuthState(state: AuthState): void {
	authState.set(state);
}

/**
 * Get current authentication state
 * 
 * @returns Current authentication state
 */
export function getAuthState(): AuthState {
	let currentState: AuthState = AuthState.UNKNOWN;
	authState.subscribe(state => {
		currentState = state;
	})();
	return currentState;
}

/**
 * Check if user is authenticated
 * 
 * @returns true if authenticated, false otherwise
 */
export function isAuthenticated(): boolean {
	return getAuthState() === AuthState.AUTHENTICATED;
}

/**
 * Check if authentication state is known
 * 
 * @returns true if state is not UNKNOWN
 */
export function isAuthStateKnown(): boolean {
	return getAuthState() !== AuthState.UNKNOWN;
}

/**
 * Reset authentication state to unknown
 * 
 * Useful when logging out or when session expires
 */
export function resetAuthState(): void {
	setAuthState(AuthState.UNKNOWN);
	authMetadata.set(null);
}
