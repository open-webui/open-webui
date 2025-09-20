import 'highlight.js/styles/github-dark.min.css';

import type { LanguageFn } from 'highlight.js';
import hljs from 'highlight.js/lib/core';
import { createLowlight } from 'lowlight';

// Pre-load essential languages
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import xml from 'highlight.js/lib/languages/xml'; // for HTML
import css from 'highlight.js/lib/languages/css';

// @ts-expect-error - virtual module
import languages from 'virtual:highlightjs-languages';

// Custom HCL language definition (since it's not available in highlight.js)
const hcl: LanguageFn = () => ({
	name: 'hcl',
	aliases: ['terraform'],
	keywords: {
		keyword: 'resource data variable locals output module provider terraform required_providers',
		built_in: 'true false null',
		type: 'string number bool list map set object tuple'
	},
	contains: [
		{
			className: 'string',
			begin: '"',
			end: '"',
			contains: [{ className: 'subst', begin: '\\$\\{', end: '\\}' }]
		},
		{ className: 'comment', begin: '#', end: '$' },
		{ className: 'comment', begin: '/\\*', end: '\\*/' },
		{ className: 'number', begin: '\\b\\d+(\\.\\d+)?' }
	]
});

export const lowlight = createLowlight();

// Initialize on import
const initialize = () => {
	const initiallyLoadedLanguages: Record<string, LanguageFn> = {
		javascript,
		typescript,
		python,
		xml,
		css,
		hcl
	};
	Object.entries(initiallyLoadedLanguages).forEach(([key, value]) => {
		hljs.registerLanguage(key, value);
		lowlight.register(key, value);
	});
};
initialize();

// Dynamic language loading
const languageCache = new Map<string, Promise<boolean> | boolean>();

export const loadLanguage = async (lang: string) => {
	lang = lang.toLowerCase();
	if (hljs.getLanguage(lang)) {
		return true;
	}
	if (languageCache.has(lang)) {
		return languageCache.get(lang)!;
	}

	if (!languages[lang]) {
		return false;
	}

	const promise = (async () => {
		try {
			const languageModule = await languages[lang]();
			lowlight.register(lang, languageModule.default);
			hljs.registerLanguage(lang, languageModule.default);

			languageCache.set(lang, true);
			return true;
		} catch (error) {
			console.warn(`Failed to load language: ${lang}`, error);
			languageCache.set(lang, false);
			return false;
		}
	})();
	languageCache.set(lang, promise);
	return promise;
};

export const isLanguageLoadedBefore = (lang: string) =>
	typeof languageCache.get(lang) === 'boolean';

export default hljs;
