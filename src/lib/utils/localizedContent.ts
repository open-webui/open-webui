type LocaleEntry = Record<string, any>;
type LocalizedMap = Record<string, LocaleEntry>;

export type PromptSuggestion = {
	title: [string, string] | string[];
	content: string;
	[key: string]: any;
};

const isPresent = (value: unknown) => typeof value === 'string' && value.trim() !== '';

export const getLocaleCandidates = (locale?: string | null) => {
	if (!locale) return [];
	const normalized = locale.trim();
	if (!normalized) return [];

	const base = normalized.split('-')[0];
	return base && base !== normalized ? [normalized, base] : [normalized];
};

export const resolveLocalizedString = (
	fallback: string | null | undefined,
	i18n: LocalizedMap | null | undefined,
	locale: string | null | undefined,
	key: string
) => {
	for (const candidate of getLocaleCandidates(locale)) {
		const value = i18n?.[candidate]?.[key];
		if (isPresent(value)) return value;
	}

	return fallback ?? '';
};

export const resolveLocalizedModelName = (model: any, locale?: string | null) => {
	const meta = model?.info?.meta ?? model?.meta;
	const info = model?.info ?? model;
	return resolveLocalizedString(model?.name ?? info?.name ?? model?.id, meta?.i18n, locale, 'name');
};

export const resolveLocalizedModelDescription = (model: any, locale?: string | null) => {
	const meta = model?.info?.meta ?? model?.meta;
	return resolveLocalizedString(meta?.description, meta?.i18n, locale, 'description');
};

export const resolveLocalizedPromptSuggestions = (
	fallback: PromptSuggestion[] | null | undefined,
	i18n: LocalizedMap | null | undefined,
	locale?: string | null
) => {
	for (const candidate of getLocaleCandidates(locale)) {
		const prompts = i18n?.[candidate]?.suggestion_prompts ?? i18n?.[candidate];
		if (Array.isArray(prompts)) return prompts;
	}

	return fallback ?? [];
};

export const resolveLocalizedModelPromptSuggestions = (model: any, locale?: string | null) => {
	const meta = model?.info?.meta ?? model?.meta;

	for (const candidate of getLocaleCandidates(locale)) {
		const prompts = meta?.i18n?.[candidate]?.suggestion_prompts;
		if (Array.isArray(prompts)) return prompts;
	}

	return meta?.suggestion_prompts ?? null;
};

export const pruneEmptyLocaleEntries = (i18n: LocalizedMap | null | undefined) => {
	if (!i18n) return {};

	return Object.fromEntries(
		Object.entries(i18n)
			.map(([locale, entry]) => [
				locale,
				Object.fromEntries(
					Object.entries(entry ?? {}).filter(([_, value]) => {
						if (typeof value === 'string') return value.trim() !== '';
						if (Array.isArray(value)) return true;
						return value !== null && value !== undefined;
					})
				)
			])
			.filter(([_, entry]) => Object.keys(entry as LocaleEntry).length > 0)
	);
};
