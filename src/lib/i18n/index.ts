import i18next from 'i18next';
import resourcesToBackend from 'i18next-resources-to-backend';
import LanguageDetector from 'i18next-browser-languagedetector';
import type { i18n as i18nType } from 'i18next';

import { writable, type Readable, type Writable } from 'svelte/store';

export interface TranslationService {
	i18n: Readable<i18nType>;
}

class I18NextTranslationStore implements TranslationService {
	public i18n: Writable<i18nType>;
	public isLoading: Writable<boolean>;

	constructor(i18n: i18nType) {
		this.i18n = this.createInstance(i18n);
		this.isLoading = this.createLoadingInstance(i18n);
	}

	private createInstance(i18n: i18nType): Writable<i18nType> {
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
	}

	private createLoadingInstance(i18n: i18nType): Writable<boolean> {
		// if loaded resources are empty || {}, set loading to true
		i18n.on('loaded', (resources) => {
			if (Object.keys(resources).length !== 0) {
				isLoading.set(false);
			}
		});

		// if resources failed loading, set loading to true
		i18n.on('failedLoading', () => {
			isLoading.set(true);
		});

		return isLoading;
	}
}

const createI18nStore = (i18n: i18nType) => {
	const i18nStore = new I18NextTranslationStore(i18n);
	return i18nStore.i18n;
};

export const initI18n = (defaultLocale?: string) => {
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
};

export const isLoading = writable(true);
export const getLanguages = async () => {
	const languages = (await import(`./locales/languages.json`)).default;
	return languages;
};
export default () => createI18nStore(i18next);
