/** Nebulon AI brand asset paths (v1.1 pack under /static/brand/). */
export const BRAND_ROOT = '/static/brand/nebulon-ai-logo-v1.1';

export const NEBULON_COLORS = {
	indigo: '#3341c9',
	violet: '#7b5cff',
	periwinkle: '#a9b6ff',
	ink: '#0d1120',
	white: '#ffffff'
} as const;

export type BrandIconSize = 16 | 32 | 48 | 64 | 128 | 180 | 256 | 512 | 1024;

export function brandIconFile(variant: 'light' | 'dark', transparent: boolean, size: BrandIconSize) {
	const stem = transparent ? `icon-${variant}-transparent` : `icon-${variant}`;
	return `${BRAND_ROOT}/icons/${stem}-${size}.png`;
}

/** Small mark (transparent sphere) for sidebar, favicon fallbacks, etc. */
export function brandMarkUrl(dark: boolean, size: BrandIconSize = 64) {
	return brandIconFile(dark ? 'dark' : 'light', true, size);
}

/** Horizontal wordmark lockup for splash, sign-in, onboarding. */
export function brandLockupUrl(dark: boolean) {
	return `${BRAND_ROOT}/lockups/nebulon-ai-horizontal-${dark ? 'dark' : 'light'}.png`;
}

export function brandFaviconIco(dark: boolean) {
	return `${BRAND_ROOT}/icons/favicon-${dark ? 'dark' : 'light'}.ico`;
}

export function brandFaviconSvg(dark: boolean) {
	return `${BRAND_ROOT}/icons/icon-${dark ? 'dark' : 'light'}.svg`;
}

/** Match document theme classes set in app.html / theme store. */
export function documentIsDark(): boolean {
	if (typeof document === 'undefined') return false;
	return document.documentElement.classList.contains('dark');
}