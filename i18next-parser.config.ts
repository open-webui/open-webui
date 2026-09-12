// i18next-parser.config.ts
import { getLanguages } from './src/lib/i18n/index.ts';

const getLangCodes = async () => {
	const languages = await getLanguages();
	return languages.map((l) => l.code);
};

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
	locales: await getLangCodes(),
	namespaceSeparator: false,
	output: 'src/lib/i18n/locales/$LOCALE/$NAMESPACE.json',
	pluralSeparator: '_',
	input: 'src/**/*.{js,svelte}',
	sort: true,
	verbose: true,
	failOnWarnings: false,
	failOnUpdate: false,
	customValueTemplate: null,
	resetDefaultValueLocale: null,
	i18nextOptions: null,
	yamlOptions: null
};
