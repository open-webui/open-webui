import { goto } from '$app/navigation';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';

import { WEBUI_BASE_URL } from '$lib/constants';
import { user } from '$lib/stores';
import i18n from '$lib/i18n';

// Guard so a burst of concurrent 401s only triggers a single sign-out/redirect.
let handlingUnauthorized = false;
// Guard so the global fetch is only wrapped once.
let installed = false;

// Resolve the origin the Open WebUI backend is served from. WEBUI_BASE_URL is
// '' (same-origin) in production builds and an absolute URL (e.g.
// http://localhost:8080) during development, so we can't assume same-origin.
const getBackendOrigin = (): string | null => {
	try {
		return new URL(WEBUI_BASE_URL || window.location.origin, window.location.origin).origin;
	} catch {
		return null;
	}
};

const resolveRequestUrl = (input: RequestInfo | URL): URL | null => {
	try {
		if (typeof input === 'string') return new URL(input, window.location.origin);
		if (input instanceof URL) return input;
		if (typeof Request !== 'undefined' && input instanceof Request) {
			return new URL(input.url, window.location.origin);
		}
	} catch {
		// Malformed URL – treat as non-backend and ignore.
	}
	return null;
};

// Only authenticated requests carry our bearer token. This keeps us from
// reacting to 401s on public endpoints (e.g. /api/config) or external
// connections (OpenAI / tool servers), which are cross-origin anyway.
const hasAuthorizationHeader = (input: RequestInfo | URL, init?: RequestInit): boolean => {
	const headers = init?.headers;
	if (headers) {
		if (headers instanceof Headers) return headers.has('authorization');
		if (Array.isArray(headers)) {
			return headers.some(([key]) => key.toLowerCase() === 'authorization');
		}
		return Object.keys(headers).some((key) => key.toLowerCase() === 'authorization');
	}

	if (typeof Request !== 'undefined' && input instanceof Request) {
		return input.headers.has('authorization');
	}

	return false;
};

const handleUnauthorized = () => {
	if (handlingUnauthorized) return;
	// Already on the auth page – there's nothing to redirect to.
	if (window.location.pathname === '/auth') return;

	handlingUnauthorized = true;

	// `user` is typed SessionUser | undefined; undefined is the logged-out state
	// and every consumer treats null/undefined identically.
	user.set(undefined);
	try {
		localStorage.removeItem('token');
	} catch {
		// localStorage may be unavailable; redirect regardless.
	}

	try {
		toast.error(get(i18n).t('Your session has expired. Please sign in again.'));
	} catch {
		// i18n/toaster might not be ready yet; the redirect is what matters.
	}

	const currentUrl = `${window.location.pathname}${window.location.search}`;
	// Re-arm once navigation settles so a later session (after re-login) is
	// still protected. While we're on /auth the guard above short-circuits.
	goto(`/auth?redirect=${encodeURIComponent(currentUrl)}`).finally(() => {
		handlingUnauthorized = false;
	});
};

/**
 * Install a global fetch wrapper that signs the user out and redirects to /auth
 * when an authenticated request to the Open WebUI backend returns 401 after the
 * initial page load.
 *
 * Without this, such 401s are only console.error'd by the individual API
 * helpers (e.g. getModels -> setModels().catch(console.error)), leaving the UI
 * stuck in a broken "logged-in" state with no redirect or notification.
 *
 * Idempotent: safe to call multiple times.
 */
export const installFetchAuthInterceptor = () => {
	if (typeof window === 'undefined') return;
	if (installed) return;
	installed = true;

	const originalFetch = window.fetch.bind(window);

	window.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
		const response = await originalFetch(input, init);

		try {
			if (response.status === 401 && localStorage.token && hasAuthorizationHeader(input, init)) {
				const url = resolveRequestUrl(input);
				const backendOrigin = getBackendOrigin();
				if (url && backendOrigin && url.origin === backendOrigin) {
					handleUnauthorized();
				}
			}
		} catch (error) {
			// The interceptor must never break the underlying request.
			console.error('Fetch auth interceptor error:', error);
		}

		return response;
	}) as typeof window.fetch;
};
