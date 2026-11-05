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
	// Match Settings: light themes leave the existing CSS palette untouched.
	if (dark) {
		const colors =
			value === 'oled-dark'
				? ['#101010', '#050505', '#000000', '#000000']
				: ['#333', '#262626', '#171717', '#0d0d0d'];
		['800', '850', '900', '950'].forEach((shade, index) => {
			root.style.setProperty(`--color-gray-${shade}`, colors[index]);
		});
	}
	document
		.querySelector('meta[name="theme-color"]')
		?.setAttribute(
			'content',
			value === 'her' ? '#983724' : value === 'oled-dark' ? '#000000' : dark ? '#171717' : '#ffffff'
		);
	window.applyTheme?.();
}
