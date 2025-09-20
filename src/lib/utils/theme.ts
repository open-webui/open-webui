import type { Theme } from '$lib/types';

export const validateTheme = (theme: any): { valid: boolean; error?: string } => {
	if (typeof theme.id !== 'string' || !theme.id) {
		return { valid: false, error: 'Invalid theme: "id" must be a non-empty string.' };
	}
	if (typeof theme.name !== 'string' || !theme.name) {
		return { valid: false, error: 'Invalid theme: "name" must be a non-empty string.' };
	}
	const allowedBases = ['system', 'light', 'dark', 'oled-dark', 'her'];
	if (typeof theme.base !== 'string' || !allowedBases.includes(theme.base)) {
		return {
			valid: false,
			error: `Invalid theme: "base" must be one of ${allowedBases.join(', ')}.`
		};
	}
	if (theme.author && typeof theme.author !== 'string') {
		return { valid: false, error: 'Invalid theme: "author" must be a string.' };
	}
	if (theme.version && typeof theme.version !== 'string') {
		return { valid: false, error: 'Invalid theme: "version" must be a string.' };
	}
	if (
		theme.variables &&
		(typeof theme.variables !== 'object' ||
			Array.isArray(theme.variables) ||
			theme.variables === null)
	) {
		return { valid: false, error: 'Invalid theme: "variables" must be an object.' };
	}
	if (theme.css && typeof theme.css !== 'string') {
		return { valid: false, error: 'Invalid theme: "css" must be a string.' };
	}
	if (theme.animationScript && typeof theme.animationScript !== 'string') {
		return { valid: false, error: 'Invalid theme: "animationScript" must be a string.' };
	}
	return { valid: true };
};

export const isDuplicateTheme = (
	theme: Theme,
	existingThemes: Theme[],
	isEditing: boolean,
	idToUpdate?: string
): boolean => {
	for (const existingTheme of existingThemes) {
		// Skip self-comparison when editing
		if (isEditing && existingTheme.id === idToUpdate) {
			continue;
		}

		if (
			theme.imageFingerprint &&
			existingTheme.imageFingerprint &&
			JSON.stringify(existingTheme.imageFingerprint) === JSON.stringify(theme.imageFingerprint)
		) {
			return true;
		}

		const newThemeCopy = { ...theme };
		delete newThemeCopy.id;
		delete newThemeCopy.sourceUrl;
		delete newThemeCopy.emoji;
		delete newThemeCopy.imageFingerprint;

		const existingThemeCopy = { ...existingTheme };
		delete existingThemeCopy.id;
		delete existingThemeCopy.sourceUrl;
		delete existingThemeCopy.emoji;
		delete existingThemeCopy.imageFingerprint;

		if (JSON.stringify(existingThemeCopy) === JSON.stringify(newThemeCopy)) {
			return true;
		}
	}
	return false;
};

export const isMismatchedVersion = (uiVersion: string, themeVersion: string) => {
	if (!themeVersion) {
		return false;
	}

	const [uiMajor, uiMinor] = uiVersion.split('.').map(Number);
	const [themeMajor, themeMinor] = themeVersion.split('.').map(Number);

	if (uiMajor !== themeMajor || uiMinor !== themeMinor) {
		return true;
	}

	return false;
};

export const objectToCss = (obj: { [key: string]: string }): string => {
	if (!obj) return '';
	let css = '';
	for (const key in obj) {
		css += `${key}: ${obj[key]};\n`;
	}
	return css;
};

export const cssToObject = (css: string): { [key: string]: string } => {
	const obj = {};
	// Remove comments, then find all key-value pairs
	const uncommentedCss = css.replace(/\/\*[\s\S]*?\*\/|([^:]|^)\/\/.*$/gm, '$1');

	const regex = /([\w-]+)\s*:\s*([^;]+);?/g;
	let match;
	while ((match = regex.exec(uncommentedCss)) !== null) {
		obj[match[1].trim()] = match[2].trim();
	}

	return obj;
};
