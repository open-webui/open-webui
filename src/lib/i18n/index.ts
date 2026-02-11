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
				fr: ['fr-FR'],
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
		locale: i18next.language ?? 'en',
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
export function getLangCode(language?: string, fallback: string = 'en'): string {
  return language?.split('-')[0] || fallback;
}

// Language family definitions for fallback translations
const LANGUAGE_FAMILIES: Record<string, string[]> = {
  en: ['en', 'en-US', 'en-GB'],
  de: ['de', 'de-DE', 'de-CH'],
  fr: ['fr', 'fr-CH', 'fr-CA', 'fr-FR'],
  it: ['it', 'it-IT', 'it-CH']
};

// Default fallback order when user's language is not found
const DEFAULT_FALLBACK = [
  'de', 'de-DE', 'de-CH',
  'en', 'en-US', 'en-GB',
  'fr', 'fr-CH', 'fr-CA', 'fr-FR',
  'it', 'it-IT', 'it-CH'
];


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
    // If it's a plain string (not JSON), return it as-is
    if (typeof label === 'string' && !label.trim().startsWith('{')) {
      return label;
    }

    // If it's already an object, use it directly
    const rawTranslations: Translations = typeof label === 'object' ? label : JSON.parse(label);

    // Normalize translations object by trimming all keys and values
    const translations: Translations = {};
    for (const [key, value] of Object.entries(rawTranslations)) {
      const trimmedKey = key.trim();
      const trimmedValue = typeof value === 'string' ? value.trim() : value;
      if (trimmedKey) {
        translations[trimmedKey] = trimmedValue;
      }
    }

    // Extract base language code (e.g., 'it' from 'it-CH', 'fr' from 'fr-CA')
    // Also trim the langCode to handle any spaces
    const cleanLangCode = langCode.trim();
    const baseLangCode = cleanLangCode.split('-')[0];

    // Build priority list for lookups
    const priorityList: string[] = [];

    // 1. Add exact match first
    priorityList.push(cleanLangCode);

    // 2. Add user's language family (if it exists)
    const userFamily = LANGUAGE_FAMILIES[baseLangCode];
    if (userFamily) {
      // Add all variants from user's family, excluding the exact match already added
      userFamily.forEach(variant => {
        if (variant !== cleanLangCode && !priorityList.includes(variant)) {
          priorityList.push(variant);
        }
      });
    }

    // 3. Add default fallback order, excluding already added languages
    DEFAULT_FALLBACK.forEach(fallbackLang => {
      if (!priorityList.includes(fallbackLang)) {
        priorityList.push(fallbackLang);
      }
    });

    // Try each language in priority order and return first non-empty translation
    for (const lang of priorityList) {
      const translation = translations[lang];
      if (translation && translation.trim() !== '') {
        return translation;
      }
    }

    // If nothing found, return empty string
    return '';
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
  fallback: string = 'en'
): string {
  const langCode = getLangCode(language, fallback);
  return getTranslatedLabel(label, langCode);
}