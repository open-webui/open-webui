import migration from './settings-key-migration.json';

type Dictionary = Record<string, string>;

/** Preserve existing administrator overrides while settings move to semantic keys. */
export const settingsOverrides = (overrides: Dictionary = {}): Dictionary => {
	const result = Object.fromEntries(Object.entries(overrides).filter(([, value]) => value.trim()));
	for (const [oldKey, keys] of Object.entries(migration)) {
		if (!overrides[oldKey]?.trim()) continue;
		for (const key of keys) {
			if (!overrides[key]?.trim()) result[key] = overrides[oldKey];
		}
	}
	return result;
};

/** Only semantic settings keys get this fallback; legacy i18n behavior stays intact. */
export const assembleSettingsTranslations = (
	bundled: Dictionary,
	english: Dictionary,
	overrides: Dictionary = {},
	englishOverrides: Dictionary = {}
): Dictionary => {
	const result = { ...bundled, ...overrides };
	const local = settingsOverrides(overrides);
	const fallback = { ...english, ...settingsOverrides(englishOverrides) };
	for (const key of Object.keys(english)) {
		if (!key.startsWith('settings.')) continue;
		result[key] = local[key]?.trim()
			? local[key]
			: bundled[key]?.trim()
				? bundled[key]
				: fallback[key];
	}
	return result;
};
