// Shared cross-site theme cookie. Same protocol used by swept-workbench and
// cloud-lock so all three apps stay in sync when deployed on a common parent
// domain (.swept.ai / .sweptai.psmic.com / staging/demo subdomains).
//
// Cookie: swept_theme = "light" | "dark" | (absent => system).
//
// Open WebUI also supports `oled-dark` and `her` which the Rails apps don't
// render; those values are kept local-only (we don't write them to the
// shared cookie, and we never overwrite them via cookie sync).

const COOKIE_NAME = 'swept_theme';
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365;
const VALID_PERSISTED = new Set(['light', 'dark']);

// Registrable parents that the three apps share. Add new envs/domains here.
const KNOWN_PARENTS = ['swept.ai', 'sweptai.psmic.com'];

export type SharedTheme = 'light' | 'dark' | 'system';

export function getCookieDomain(): string | null {
	const host = window.location.hostname;
	if (!host || host === 'localhost') return null;
	if (/^\d+\.\d+\.\d+\.\d+$/.test(host)) return null;
	if (host.includes(':')) return null;

	let matched: string | null = null;
	for (const parent of KNOWN_PARENTS) {
		if (
			(host === parent || host.endsWith('.' + parent)) &&
			(!matched || parent.length > matched.length)
		) {
			matched = parent;
		}
	}
	if (!matched) return null;

	const labels = host.split('.');
	if (labels.length < 2) return null;
	return '.' + labels.slice(1).join('.');
}

export function readThemeCookie(): 'light' | 'dark' | null {
	const match = document.cookie.match(new RegExp('(?:^|; )' + COOKIE_NAME + '=([^;]*)'));
	if (!match) return null;
	const value = decodeURIComponent(match[1]);
	return VALID_PERSISTED.has(value) ? (value as 'light' | 'dark') : null;
}

export function writeThemeCookie(value: 'light' | 'dark'): void {
	if (!VALID_PERSISTED.has(value)) return;
	document.cookie = buildCookie(`${COOKIE_NAME}=${encodeURIComponent(value)}`, COOKIE_MAX_AGE);
}

export function clearThemeCookie(): void {
	document.cookie = buildCookie(`${COOKIE_NAME}=`, 0);
}

function buildCookie(nameValue: string, maxAge: number): string {
	const parts = [nameValue, 'Path=/', `Max-Age=${maxAge}`, 'SameSite=Lax'];
	const domain = getCookieDomain();
	if (domain) parts.push(`Domain=${domain}`);
	if (window.location.protocol === 'https:') parts.push('Secure');
	return parts.join('; ');
}

// Returns "light" | "dark" | "system" — the user's chosen mode according to
// the shared cookie (or "system" if absent). Local-only Open WebUI variants
// (oled-dark, her) are ignored here — those live in localStorage.theme only.
export function readSharedTheme(): SharedTheme {
	const fromCookie = readThemeCookie();
	if (fromCookie) return fromCookie;
	return 'system';
}

// Mirrors the chosen value into the shared cookie when it's one of the
// values all three apps understand. Local-only values (oled-dark, her) are
// dropped — those never propagate cross-app.
export function syncToCookie(chosen: string): void {
	if (chosen === 'light' || chosen === 'dark') {
		writeThemeCookie(chosen);
	} else if (chosen === 'system') {
		clearThemeCookie();
	}
	// oled-dark, her: do nothing — preserve other apps' state.
}

export function isLocalOnlyTheme(value: string | null | undefined): boolean {
	return value === 'oled-dark' || value === 'her';
}
