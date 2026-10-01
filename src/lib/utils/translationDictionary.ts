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
		if (!key.trim() || unsafeKeys.has(key)) throw new Error(`Invalid translation key: ${key}`);
		if (typeof text !== 'string') throw new Error(`Translation must be a string: ${key}`);
		if (
			text.trim() &&
			JSON.stringify(placeholders(source[key] || key)) !== JSON.stringify(placeholders(text))
		)
			throw new Error(`Interpolation placeholders do not match: ${key}`);
	}
	return value as Record<string, string>;
};

export const validateI18n = (value: I18nOverrides): I18nOverrides => {
	const cleaned: I18nOverrides = {};
	for (const [locale, entries] of Object.entries(value)) {
		if (!locale.trim() || unsafeKeys.has(locale)) throw new Error(`Invalid language: ${locale}`);
		const dictionary = validateDictionary(entries);
		const nonempty = Object.fromEntries(
			Object.entries(dictionary).filter(([, text]) => text.trim())
		);
		if (Object.keys(nonempty).length) cleaned[locale] = nonempty;
	}
	return cleaned;
};
export type I18nOverrides = Record<string, Record<string, string>>;
export type I18nEntry = { content: string; i18n: I18nOverrides };

export const i18nToEntries = (value: I18nOverrides): I18nEntry[] => {
	const entries = new Map<string, I18nEntry>();
	for (const [locale, dictionary] of Object.entries(value)) {
		for (const [content, translation] of Object.entries(dictionary)) {
			if (!entries.has(content)) entries.set(content, { content, i18n: {} });
			entries.get(content)!.i18n[locale] = { content: translation };
		}
	}
	return [...entries.values()];
};

export const entriesToI18n = (entries: I18nEntry[]): I18nOverrides => {
	const value: I18nOverrides = {};
	const seen = new Set<string>();
	for (const entry of entries) {
		const translations = Object.entries(entry.i18n).filter(([, text]) => text.content.trim());
		if (!entry.content.trim()) {
			if (translations.length) throw new Error('Original text is required for translated rows.');
			continue;
		}
		if (seen.has(entry.content)) throw new Error(`Duplicate original text: ${entry.content}`);
		seen.add(entry.content);
		validateDictionary({ [entry.content]: '' });
		for (const [locale, translation] of translations) {
			value[locale] = { ...value[locale], [entry.content]: translation.content };
		}
	}
	return validateI18n(value);
};

const unsafeKeys = new Set(['__proto__', 'prototype', 'constructor']);
