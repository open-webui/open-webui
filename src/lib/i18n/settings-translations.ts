type Dictionary = Record<string, string>;

/** Only semantic settings keys get this fallback; other translations keep their existing behavior. */
export const assembleSettingsTranslations = (
	bundled: Dictionary,
	english: Dictionary,
	overrides: Dictionary = {},
	englishOverrides: Dictionary = {}
): Dictionary => {
	const result = { ...bundled, ...overrides };
	for (const key of Object.keys(english)) {
		if (!key.startsWith('settings.')) continue;
		result[key] =
			[overrides[key], bundled[key], englishOverrides[key], english[key]].find((value) =>
				value?.trim()
			) ?? '';
	}
	return result;
};
