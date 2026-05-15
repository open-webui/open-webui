// Shared cross-site sidebar-collapse cookie. Same protocol used by
// swept-workbench (see app/javascript/controllers/sidebar_collapse_controller.js
// in that repo) so collapsing the desktop sidebar in one app propagates to the
// others when deployed under a common parent domain.
//
// Cookie: swept_sidebar_collapsed = "true" | "false"
//
// Absence of the cookie means "uninitialized" — the Sidebar component falls
// back to the legacy `localStorage.sidebar` once for migration, then writes
// the cookie so future loads use the shared value.

import { buildCookie, DEFAULT_COOKIE_MAX_AGE } from './swept-cookies';

const COOKIE_NAME = 'swept_sidebar_collapsed';

export function readSidebarCollapsedCookie(): boolean | null {
	const match = document.cookie.match(new RegExp('(?:^|; )' + COOKIE_NAME + '=([^;]*)'));
	if (!match) return null;
	let value: string;
	try {
		value = decodeURIComponent(match[1]);
	} catch (e) {
		return null;
	}
	if (value === 'true') return true;
	if (value === 'false') return false;
	return null;
}

export function writeSidebarCollapsedCookie(collapsed: boolean): void {
	const value = collapsed ? 'true' : 'false';
	document.cookie = buildCookie(`${COOKIE_NAME}=${encodeURIComponent(value)}`, DEFAULT_COOKIE_MAX_AGE);
}

export function clearSidebarCollapsedCookie(): void {
	document.cookie = buildCookie(`${COOKIE_NAME}=`, 0);
}
