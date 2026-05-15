// Shared cross-site theme cookie. Same protocol used by swept-workbench and
// cloud-lock so all three apps stay in sync when deployed on a common parent
// domain.
//
// Cookie: swept_theme = "light" | "dark" | "system"
//
// The cookie always carries an explicit value (including "system") once any
// Swept app has touched it. Absence-of-cookie means "never been initialized
// in this browser" and triggers a one-shot legacy-localStorage migration.
// This protocol prevents stale localStorage from re-clobbering a "system"
// pick another app made by clearing the cookie (the previous design).
//
// Open WebUI also supports `oled-dark` and `her`. Those are kept local-only:
// we never write them to the shared cookie, and we never overwrite them via
// cookie sync (the visibility/focus handler in +layout.svelte bails out when
// the local value is one of these).

import { buildCookie, DEFAULT_COOKIE_MAX_AGE, getCookieDomain } from './swept-cookies';

const COOKIE_NAME = 'swept_theme';
const VALID_COOKIE = new Set(['light', 'dark', 'system']);

export type SharedTheme = 'light' | 'dark' | 'system';

export { getCookieDomain };

export function readThemeCookie(): SharedTheme | null {
	const match = document.cookie.match(new RegExp('(?:^|; )' + COOKIE_NAME + '=([^;]*)'));
	if (!match) return null;
	let value: string;
	try {
		value = decodeURIComponent(match[1]);
	} catch (e) {
		return null; // malformed cookie value — treat as missing
	}
	return VALID_COOKIE.has(value) ? (value as SharedTheme) : null;
}

export function writeThemeCookie(value: SharedTheme): void {
	if (!VALID_COOKIE.has(value)) return;
	document.cookie = buildCookie(
		`${COOKIE_NAME}=${encodeURIComponent(value)}`,
		DEFAULT_COOKIE_MAX_AGE
	);
}

export function clearThemeCookie(): void {
	document.cookie = buildCookie(`${COOKIE_NAME}=`, 0);
}

// Returns the shared theme. Cookie is the source of truth; absent means
// "uninitialized" (handled by the FOUC migration in src/app.html and the
// theme.subscribe in +layout.svelte that propagates the current store
// value into the cookie).
export function readSharedTheme(): SharedTheme {
	return readThemeCookie() ?? 'system';
}

// Mirrors the chosen Open WebUI theme into the shared cookie when it's
// one of the values the other apps understand. Local-only Open WebUI
// variants (oled-dark, her) are dropped — those never propagate cross-app
// and their absence here means other apps keep their previous shared state.
export function syncToCookie(chosen: string): void {
	if (chosen === 'light' || chosen === 'dark' || chosen === 'system') {
		writeThemeCookie(chosen);
	}
	// oled-dark, her: do nothing — preserve other apps' state.
}

export function isLocalOnlyTheme(value: string | null | undefined): boolean {
	return value === 'oled-dark' || value === 'her';
}
