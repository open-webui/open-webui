import i18next from 'i18next';
import resourcesToBackend from 'i18next-resources-to-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import type { i18n as i18nType } from 'i18next';
import { writable } from 'svelte/store';
import type { I18nOverrides } from '$lib/utils/translationDictionary';

import { assembleSettingsTranslations } from './settings-translations';
import languages from './locales/languages.json';

let overrides: I18nOverrides = {};

export const loadBundledResource = async (language: string): Promise<Record<string, string>> =>
	(await import(`./locales/${language}/translation.json`)).default;

const loadResource = async (language: string) =>
	assembleSettingsTranslations(
		await loadBundledResource(language),
		await loadBundledResource('en-US'),
		overrides[language],
		overrides['en-US']
	);

export const updateI18n = async (value: I18nOverrides = {}) => {
	overrides = value;
	const resources = await Promise.all(
		Object.keys(i18next.store?.data ?? {}).map(async (language) => ({
			language,
			resource: await loadResource(language)
		}))
	);
	for (const { language, resource } of resources) {
		i18next.removeResourceBundle(language, 'translation');
		i18next.addResourceBundle(language, 'translation', resource);
	}
	i18n.set(i18next);
};

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

const languageCodes = languages.map(({ code }) => code);

const toBundleCode = (code: string) => {
	const ownBundle = languageCodes.find((bundle) => bundle.toLowerCase() === code.toLowerCase());
	if (ownBundle) return ownBundle;
	const baseLanguage = code.split('-')[0].toLowerCase();
	const primaryBundle = `${baseLanguage}-${baseLanguage.toUpperCase()}`;
	if (languageCodes.includes(primaryBundle)) return primaryBundle;
	// the first sibling of a regional code can be another script (zh-HK would get zh-CN)
	if (code.includes('-')) return code;
	return languageCodes.find((bundle) => bundle.startsWith(`${baseLanguage}-`)) ?? code;
};

export const initI18n = (defaultLocale?: string, value: I18nOverrides = {}) => {
	overrides = value;
	const detectionOrder = defaultLocale
		? ['querystring', 'localStorage']
		: ['querystring', 'localStorage', 'navigator'];
	const fallbackDefaultLocale = defaultLocale ? [defaultLocale, 'en-US'] : ['en-US'];

	return i18next
		.use(resourcesToBackend(loadResource))
		.use(LanguageDetector)
		.init({
			debug: false,
			detection: {
				order: detectionOrder,
				caches: ['localStorage'],
				lookupQuerystring: 'lang',
				lookupLocalStorage: 'locale',
				convertDetectedLanguage: toBundleCode
			},
			fallbackLng: {
				fr: ['fr-FR'],
				default: fallbackDefaultLocale
			},
			ns: 'translation',
			keySeparator: false,
			nsSeparator: false,
			returnEmptyString: false,
			interpolation: {
				escapeValue: false // not needed for svelte as it escapes by default
			}
		});
};

const i18n = createI18nStore(i18next);
const isLoadingStore = createIsLoadingStore(i18next);

export const getLanguages = async () => languages;
export const changeLanguage = (lang: string) => {
	document.documentElement.setAttribute('lang', lang);
	return i18next.changeLanguage(lang);
};

export default i18n;
export const isLoading = isLoadingStore;
