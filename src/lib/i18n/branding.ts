/** Applied after translation/interpolation, including English key fallbacks and admin overrides. */
export const brandTranslation = (value: string): string =>
	value.replace(/open\s*web\s*ui/gi, 'GCAT');
