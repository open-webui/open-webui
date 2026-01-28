/**
 * Resolve theme value to 'light' or 'dark' for API calls
 * @param theme Theme value from store ('light', 'dark', 'system', or variations)
 * @returns 'light' or 'dark'
 */
export function resolveTheme(theme: string): 'light' | 'dark' {
	if (theme.includes('dark')) {
		return 'dark';
	}

	if (theme === 'system') {
		if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
			return 'dark';
		}
		return 'light';
	}

	return 'light';
}
