// i18next-parser.config.ts
import languages from './src/lib/i18n/locales/languages.json';

export default {
	contextSeparator: '_',
	createOldCatalogs: false,
	defaultNamespace: 'translation',
	defaultValue: '',
	indentation: 2,
	keepRemoved: false,
	keySeparator: false,
	lexers: {
		svelte: ['JavascriptLexer'],
		js: ['JavascriptLexer'],
		ts: ['JavascriptLexer'],

		default: ['JavascriptLexer']
	},
	lineEnding: 'auto',
	locales: languages.map(({ code }) => code),
	namespaceSeparator: false,
	output: 'src/lib/i18n/locales/$LOCALE/$NAMESPACE.json',
	pluralSeparator: '_',
	input: 'src/**/*.{js,ts,svelte}',
	sort: true,
	verbose: true,
	failOnWarnings: false,
	failOnUpdate: false,
	customValueTemplate: null,
	resetDefaultValueLocale: null,
	i18nextOptions: null,
	yamlOptions: null
};
