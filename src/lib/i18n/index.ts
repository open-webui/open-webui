import i18next from 'i18next';
import resourcesToBackend from 'i18next-resources-to-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import type { i18n as i18nType } from 'i18next';
import { writable } from 'svelte/store';

const createI18nStore = (i18n: i18n) => {
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

const createIsLoadingStore = (i18n: i18n) => {
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

i18next
	.use(
		resourcesToBackend((language, namespace) => import(`./locales/${language}/${namespace}.json`))
	)
	.use(LanguageDetector)
	.init({
		debug: true,
		detection: {
			order: ['querystring', 'localStorage', 'navigator'],
			caches: ['localStorage'],
			lookupQuerystring: 'lang',
			lookupLocalStorage: 'locale'
		},
		fallbackLng: 'en',
		ns: 'common',
		interpolation: {
			escapeValue: false // not needed for svelte as it escapes by default
		}
	});

const i18n = createI18nStore(i18next);
const isLoadingStore = createIsLoadingStore(i18next);
export default i18n;
export const isLoading = isLoadingStore;
