export const placeholders = (text: string) =>
	[
		...new Set(
			Array.from(text.matchAll(/\{\{\s*-?\s*([^},]+)(?:,[^}]+)?\s*\}\}/g), (match) =>
				match[1].trim()
			)
		)
	].sort();

export const validateDictionary = (
	value: unknown,
	source: Record<string, string> = {}
): Record<string, string> => {
	if (!value || typeof value !== 'object' || Array.isArray(value))
		throw new Error('Expected a JSON object of translation keys and strings.');
	for (const [key, text] of Object.entries(value)) {
		if (typeof text !== 'string') throw new Error(`Translation must be a string: ${key}`);
		if (
			text.trim() &&
			JSON.stringify(placeholders(source[key] || key)) !== JSON.stringify(placeholders(text))
		)
			throw new Error(`Interpolation placeholders do not match: ${key}`);
	}
	return value as Record<string, string>;
};
