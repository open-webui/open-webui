import i18next from 'i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import resourcesToBackend from 'i18next-resources-to-backend';
import type { i18n as i18nType } from 'i18next';
import { writable } from 'svelte/store';

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
		Object.keys(resources).length !== 0 && isLoading.set(false);
	});

	// if resources failed loading, set loading to true
	i18n.on('failedLoading', () => {
		isLoading.set(true);
	});

	return isLoading;
};

export const initI18n = (defaultLocale?: string) => {
	// Use object destructuring for cleaner code
	const [defaultDetection, fallbackDetection] = defaultLocale ? ['querystring', 'localStorage'] : ['querystring', 'localStorage', 'navigator'];
  
	// Use nullish coalescing operator to simplify the ternary expression
	const fallbackDefaultLocale = defaultLocale ?? 'en-US';
  
	const loadResource = (language: string, namespace: string) => import(`./locales/${language}/${namespace}.json`);
  
	i18next
	  .use(resourcesToBackend(loadResource))
	  .use(LanguageDetector)
	  .init({
		debug: false,
		detection: {
		  order: [defaultDetection, fallbackDetection],
		  caches: ['localStorage'],
		  lookupQuerystring: 'lang',
		  lookupLocalStorage: 'locale'
		},
		fallbackLng: fallbackDefaultLocale,
		ns: 'translation',
		returnEmptyString: false,
		interpolation: { escapeValue: false }
	  });
  };

const i18n = createI18nStore(i18next);
const isLoadingStore = createIsLoadingStore(i18next);

export const getLanguages = async () => {
	const languages = (await import(`./locales/languages.json`)).default;
	return languages;
};
export default i18n;
export const isLoading = isLoadingStore;
