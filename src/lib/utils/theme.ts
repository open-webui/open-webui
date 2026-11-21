import { theme } from '$lib/stores';

type Mode = 'light' | 'dark';
export type ThemeColors = Partial<Record<Mode, { bg: string; fg: string }>>;

// What the default greys are mixed from (see `--app-bg` / `--app-fg` in tailwind.css).
export const DEFAULT_THEME_COLORS: Record<Mode, { bg: string; fg: string }> = {
	light: { bg: '#ffffff', fg: '#000000' },
	dark: { bg: '#171717', fg: '#ffffff' }
};

export function getThemeColors(): ThemeColors {
	try {
		return JSON.parse(localStorage.themeColors ?? '{}');
	} catch {
		return {};
	}
}

export function setThemeColors(colors: ThemeColors): void {
	if (colors.light || colors.dark) localStorage.themeColors = JSON.stringify(colors);
	else localStorage.removeItem('themeColors');
	applyThemeColors();
}

// Keep in sync with the copy in app.html, which runs before first paint.
export function applyThemeColors(): void {
	const root = document.documentElement;
	const colors = root.classList.contains('her')
		? undefined
		: getThemeColors()[root.classList.contains('dark') ? 'dark' : 'light'];
	if (colors) {
		root.style.setProperty('--app-bg', colors.bg);
		root.style.setProperty('--app-fg', colors.fg);
		document.querySelector('meta[name="theme-color"]')?.setAttribute('content', colors.bg);
	} else {
		root.style.removeProperty('--app-bg');
		root.style.removeProperty('--app-fg');
	}
}

export function setTheme(value: string): void {
	localStorage.setItem('theme', value);
	theme.set(value);
	const dark =
		value === 'system'
			? window.matchMedia('(prefers-color-scheme: dark)').matches
			: value.includes('dark');
	const root = document.documentElement;
	const resolved = dark ? 'dark' : 'light';
	for (const name of ['light', 'dark', 'oled-dark']) {
		if (name !== resolved) root.classList.remove(name);
	}
	root.classList.add(resolved);
	// OLED greys live in tailwind.css under `.oled-dark`, so custom CSS can still override them.
	if (value === 'oled-dark') root.classList.add('oled-dark');
	document
		.querySelector('meta[name="theme-color"]')
		?.setAttribute(
			'content',
			value === 'her' ? '#983724' : value === 'oled-dark' ? '#000000' : dark ? '#171717' : '#ffffff'
		);
	applyThemeColors();
	window.applyTheme?.();
}
