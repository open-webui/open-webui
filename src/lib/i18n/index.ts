import i18next from 'i18next';
import resourcesToBackend from 'i18next-resources-to-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import type { i18n as i18nType } from 'i18next';
import { writable, type Writable } from 'svelte/store';
import { setContext } from 'svelte';

let i18nStore: Writable<any> | undefined;

const createI18nStore = (i18n: i18nType) => {
	const i18nWritable = writable(i18n);

	i18n.on('initialized', () => {
		i18nWritable.set(i18n);
	});
	i18n.on('loaded', () => {
		i18nWritable.set(i18n);
	});
	i18n.on('added', () => i18nWritable.set(i18n));
	i18n.on('languageChanged', () => {
		i18nWritable.set(i18n);
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

export const initI18n = (defaultLocale?: string | undefined) => {
	const detectionOrder = defaultLocale
		? ['querystring', 'localStorage']
		: ['querystring', 'localStorage', 'navigator'];
	const fallbackDefaultLocale = defaultLocale ? [defaultLocale] : ['en-US'];

	const loadResource = (language: string, namespace: string) =>
		import(`./locales/${language}/${namespace}.json`);

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
				default: fallbackDefaultLocale
			},
			ns: 'translation',
			returnEmptyString: false,
			interpolation: {
				escapeValue: false // not needed for svelte as it escapes by default
			}
		});

	const lang = i18next?.language || defaultLocale || 'en-US';
	document.documentElement.setAttribute('lang', lang);

	if (!i18nStore) {
		i18nStore = createI18nStore(i18next);
	}
	return i18nStore;
};




// ---- accessors ----
export const getI18nStore = () => {
	if (!i18nStore) {
		// fallback dummy store until initI18n runs
		i18nStore = writable(i18next);
	}
	return i18nStore;
};


export const getLanguages = async () => {
	const languages = (await import(`./locales/languages.json`)).default;
	return languages;
};
export const changeLanguage = (lang: string) => {
	document.documentElement.setAttribute('lang', lang);
	i18next.changeLanguage(lang);
};

// ---- context support (optional) ----
export function initI18nContext() {
	const store = writable({
		locale: i18next.language ?? 'de',
		t: (key: string) => key
	});
	setContext('i18n', store);
	return store;
}

// ---- exports ----
export const isLoading = createIsLoadingStore(i18next);
export default getI18nStore();

// Utils for translations
export interface Translations {
  [key: string]: string;
}

/**
 * Extracts the language code from a locale string (e.g., 'en-US' -> 'en')
 * @param language - Full language code (e.g., 'en-US', 'es-ES')
 * @param fallback - Default language code if parsing fails
 * @returns Language code (e.g., 'en', 'es', 'de')
 */
export function getLangCode(language?: string, fallback: string = 'de'): string {
  return language?.split('-')[0] || fallback;
}

/**
 * Gets translated label from translation object or JSON string
 * @param label - Translation object or JSON string containing translations
 * @param langCode - Target language code (e.g., 'en', 'es', 'de')
 * @returns Translated string or empty string if not found
 */
export function getTranslatedLabel(
  label: string | Translations | null | undefined, 
  langCode: string
): string {
  if (!label) return '';

  try {
    // If it's already an object, use it directly
    const translations: Translations = typeof label === 'object' ? label : JSON.parse(label);
    
    return (
      translations[langCode] ||
      translations.en ||
      translations.de ||
      translations.fr ||
      translations.it ||
      ''
    );
  } catch (error) {
    // Log parsing errors for debugging in development
    if (process.env.NODE_ENV === 'development') {
      console.warn('Failed to parse translation label:', label, error);
    }
    
    // If parsing fails, return the original value if it's a string
    return typeof label === 'string' ? label : '';
  }
}

/**
 * Convenience function that combines getLangCode and getTranslatedLabel
 * @param label - Translation object or JSON string
 * @param language - Full language code (e.g., 'en-US')
 * @param fallback - Fallback language code
 * @returns Translated string
 */
export function translate(
  label: string | Translations | null | undefined,
  language?: string,
  fallback: string = 'de'
): string {
  const langCode = getLangCode(language, fallback);
  return getTranslatedLabel(label, langCode);
}