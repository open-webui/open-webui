import i18next from 'i18next';
import resourcesToBackend from 'i18next-resources-to-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import type { i18n as i18nType } from 'i18next';
import { writable } from 'svelte/store';
import { WEBUI_BASE_URL } from '$lib/constants';

const createI18nStore = (i18n: i18nType) => {
	const i18nWritable = writable(i18n);

	i18n.on('initialized', () => {
		i18nWritable.set(i18n);
	});
	i18n.on('loaded', () => {
		i18nWritable.set(i18n);
	});
	i18n.on('added', () => i18nWritable.set(i18n));
	i18n.on('languageChanged', (lang) => {
		i18nWritable.set(i18n);
		if (typeof document !== 'undefined') {
			document.documentElement.setAttribute('lang', lang);
		}
	});
	return i18nWritable;
};

const createIsLoadingStore = (i18n: i18nType) => {
	const isLoading = writable(false);

	// if loaded resources are empty || {}, set loading to true
	i18n.on('loaded', (resources) => {
		// console.log('loaded:', resources);
		isLoading.set(Object.keys(resources).length === 0);
	});

	// if resources failed loading, set loading to true
	i18n.on('failedLoading', () => {
		isLoading.set(true);
	});

	return isLoading;
};

const loadBundledResource = async (
	language: string,
	namespace: string
): Promise<Record<string, string>> => {
	const mod = await import(`./locales/${language}/${namespace}.json`);
	return (mod.default ?? mod) as Record<string, string>;
};

const loadRuntimeOverrides = async (
	language: string,
	namespace: string
): Promise<Record<string, string>> => {
	try {
		const res = await fetch(`${WEBUI_BASE_URL}/static/locales/${language}/${namespace}.json`, {
			credentials: 'same-origin'
		});
		if (!res.ok) {
			return {};
		}
		const data = await res.json();
		if (data && typeof data === 'object' && !Array.isArray(data)) {
			return data as Record<string, string>;
		}
	} catch {
		// Missing override file or network error — keep bundled translations
	}
	return {};
};

const loadResource = async (language: string, namespace: string) => {
	const bundled = await loadBundledResource(language, namespace);
	const overrides = await loadRuntimeOverrides(language, namespace);
	return { ...bundled, ...overrides };
};

export const initI18n = (defaultLocale?: string | undefined) => {
	const detectionOrder = defaultLocale
		? ['querystring', 'localStorage']
		: ['querystring', 'localStorage', 'navigator'];
	const fallbackDefaultLocale = defaultLocale ? [defaultLocale] : ['en-US'];

	i18next
		.use(resourcesToBackend(loadResource))
		.use(LanguageDetector)
		.init({
			debug: false,
			detection: {
				order: detectionOrder,
				caches: ['localStorage'],
				lookupQuerystring: 'lang',
				lookupLocalStorage: 'locale'
			},
			fallbackLng: {
				fr: ['fr-FR'],
				default: fallbackDefaultLocale
			},
			ns: 'translation',
			returnEmptyString: false,
			interpolation: {
				escapeValue: false // not needed for svelte as it escapes by default
			}
		});
};

const i18n = createI18nStore(i18next);
const isLoadingStore = createIsLoadingStore(i18next);

export const getLanguages = async () => {
	const languages = (await import(`./locales/languages.json`)).default;
	return languages;
};
export const changeLanguage = (lang: string) => {
	document.documentElement.setAttribute('lang', lang);
	i18next.changeLanguage(lang);
};

export default i18n;
export const isLoading = isLoadingStore;
