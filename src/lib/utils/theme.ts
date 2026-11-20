import { theme } from '$lib/stores';

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
	window.applyTheme?.();
}
