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

export const resolveLocalizedResource = (resource: any, locale: string, field = 'name') => {
	const meta = resource?.meta;
	const key = resource?.action_id ? `actions.${resource.action_id}.${field}` : field;
	return resolveLocalizedString(
		resource?.[field] ?? meta?.[field] ?? (field === 'name' ? resource?.id : ''),
		meta?.i18n,
		locale,
		key
	);
};

export const resolveLocalizedFunction = (
	item: any,
	functions: any[] | null,
	locale: string,
	field = 'name'
) => {
	const owner = (functions ?? [])
		.filter((fn) => item?.id === fn.id || item?.id?.startsWith(`${fn.id}.`))
		.sort((a, b) => b.id.length - a.id.length)[0];
	const key =
		owner && item.id !== owner.id
			? `actions.${item.id.slice(owner.id.length + 1)}.${field}`
			: field;
	return resolveLocalizedString(item?.[field], owner?.meta?.i18n ?? item?.meta?.i18n, locale, key);
};

// This is a display-only copy: identifiers, defaults and submitted values stay untouched.
export const localizeValvesSchema = (
	schema: any,
	locale: string,
	meta: any = {},
	prefix = 'valves'
) => {
	if (!schema) return schema;
	const translate = (value: string, key: string) =>
		resolveLocalizedString(value, meta?.i18n, locale, `${prefix}.${key}`);
	return {
		...schema,
		properties: Object.fromEntries(
			Object.entries(schema.properties ?? {}).map(([key, value]: [string, any]) => [
				key,
				{
					...value,
					title: translate(value.title ?? key, `${key}.title`),
					description: translate(value.description ?? '', `${key}.description`),
					...(Array.isArray(value.input?.options)
						? {
								input: {
									...value.input,
									options: value.input.options.map((option: any) =>
										typeof option === 'object'
											? {
													...option,
													label: translate(
														option.label ?? String(option.value),
														`${key}.enum.${option.value}`
													)
												}
											: { value: option, label: translate(String(option), `${key}.enum.${option}`) }
									)
								}
							}
						: {})
				}
			])
		)
	};
};

export const valveTranslationSource = (schema: any, prefix: string): Record<string, string> => {
	const strings: Record<string, string> = {};
	for (const [key, field] of Object.entries(schema?.properties ?? {}) as [string, any][]) {
		strings[`${prefix}.${key}.title`] = field.title ?? key;
		if (field.description) strings[`${prefix}.${key}.description`] = field.description;
		for (const option of field.enum ?? field.input?.options ?? []) {
			const value = typeof option === 'object' ? option.value : option;
			strings[`${prefix}.${key}.enum.${value}`] = String(
				typeof option === 'object' ? (option.label ?? value) : value
			);
		}
	}
	return strings;
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
