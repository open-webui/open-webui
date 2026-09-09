export const setTextScale = (scale: number) => {
	if (typeof document === 'undefined') {
		return;
	}

	document.documentElement.style.setProperty('--app-text-scale', `${scale}`);
};

export const normalizeAppFontFamily = (fontFamily?: string | null) =>
	typeof fontFamily === 'string' ? fontFamily.trim().replace(/[\u0000-\u001f\u007f]/g, '') : '';

export const setAppFontFamily = (fontFamily?: string | null) => {
	if (typeof document === 'undefined') {
		return;
	}

	const normalized = normalizeAppFontFamily(fontFamily);
	if (!normalized) {
		document.documentElement.style.removeProperty('--app-font-family');
		return;
	}

	document.documentElement.style.setProperty(
		'--app-font-family',
		`"${normalized.replace(/\\/g, '\\\\').replace(/"/g, '\\"')}"`
	);
};
