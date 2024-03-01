import i18next from 'i18next';
import resourcesToBackend from 'i18next-resources-to-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import { createI18nStore, isLoading as isLoadingStore } from './store';

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
		// backend: {
		// 	loadPath: '/locales/{{lng}}/{{ns}}.json'
		// }
		interpolation: {
			escapeValue: false // not needed for svelte as it escapes by default
		}
	});
const i18n = createI18nStore(i18next);
export default i18n;
export const isLoading = isLoadingStore;
