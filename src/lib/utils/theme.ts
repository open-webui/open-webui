import { theme } from '$lib/stores';

export function toggleTheme() {
	const currentTheme = localStorage.theme || 'system';
	let newTheme: string;

	if (currentTheme === 'light') {
		newTheme = 'dark';
	} else if (currentTheme === 'dark') {
		newTheme = 'light';
	} else if (currentTheme === 'system') {
		// If system, check current preference and switch to opposite
		const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
		newTheme = prefersDark ? 'light' : 'dark';
	} else {
		// Default to light if unknown theme
		newTheme = 'light';
	}

	// Update localStorage and store
	localStorage.theme = newTheme;
	theme.set(newTheme);

	// Apply theme to document
	applyTheme();
}

export function applyTheme() {
	const metaThemeColorTag = document.querySelector('meta[name="theme-color"]');
	const currentTheme = localStorage.theme || 'system';

	// Remove existing theme classes
	document.documentElement.classList.remove('dark', 'light', 'her');

	if (currentTheme === 'system') {
		const prefersDarkTheme = window.matchMedia('(prefers-color-scheme: dark)').matches;
		document.documentElement.classList.add(prefersDarkTheme ? 'dark' : 'light');
		metaThemeColorTag?.setAttribute('content', prefersDarkTheme ? '#171717' : '#ffffff');
	} else if (currentTheme === 'oled-dark') {
		document.documentElement.style.setProperty('--color-gray-800', '#101010');
		document.documentElement.style.setProperty('--color-gray-850', '#050505');
		document.documentElement.style.setProperty('--color-gray-900', '#000000');
		document.documentElement.style.setProperty('--color-gray-950', '#000000');
		document.documentElement.classList.add('dark');
		metaThemeColorTag?.setAttribute('content', '#000000');
	} else if (currentTheme === 'light') {
		document.documentElement.classList.add('light');
		metaThemeColorTag?.setAttribute('content', '#ffffff');
	} else if (currentTheme === 'her') {
		document.documentElement.classList.add('dark');
		document.documentElement.classList.add('her');
		metaThemeColorTag?.setAttribute('content', '#983724');
	} else {
		document.documentElement.classList.add('dark');
		metaThemeColorTag?.setAttribute('content', '#171717');
	}
}

export function getCurrentTheme(): string {
	return localStorage.theme || 'system';
}

export function getEffectiveTheme(): 'light' | 'dark' {
	const currentTheme = getCurrentTheme();
	
	if (currentTheme === 'light') return 'light';
	if (currentTheme === 'dark') return 'dark';
	if (currentTheme === 'system') {
		return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
	}
	
	// Default to dark for other themes
	return 'dark';
} 