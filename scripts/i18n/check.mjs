import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const pluralSuffix = /_(zero|one|two|few|many|other)$/;

/** @param {string} text */
function interpolation(text) {
	const names = new Set();
	const literal = text.replace(/\{\{([^{}]+)\}\}/g, (_, expression) => {
		names.add(expression.replace(/^-/, '').split(',')[0].trim());
		return '';
	});
	return { names, literal };
}

/**
 * @param {string} key
 * @param {unknown} value
 * @param {string} source
 */
export function validateTranslation(key, value, source = key) {
	if (typeof value !== 'string') return ['translation must be a string'];
	if (!value.trim()) return [];

	const expected = interpolation(source);
	const actual = interpolation(value);
	const problems = [];
	for (const name of expected.names) {
		// Plural forms can express the count in words (e.g. "one file").
		if (name === 'count' && pluralSuffix.test(key)) continue;
		if (!actual.names.has(name)) problems.push(`missing {{${name}}}`);
	}
	for (const name of actual.names) {
		if (!expected.names.has(name)) problems.push(`unexpected {{${name}}}`);
	}

	// Literal JSON is allowed, but translations must not introduce extra braces.
	for (const brace of ['{', '}']) {
		if (actual.literal.split(brace).length > expected.literal.split(brace).length) {
			problems.push('unexpected braces outside {{placeholders}}');
			break;
		}
	}
	return problems;
}

/** @param {string} directory */
export function checkCatalogs(directory) {
	/** @param {string} locale @returns {Record<string, string>} */
	const readCatalog = (locale) =>
		JSON.parse(readFileSync(join(directory, locale, 'translation.json'), 'utf8'));
	const english = readCatalog('en-US');
	const problems = [];
	for (const locale of readdirSync(directory, { withFileTypes: true })
		.filter((entry) => entry.isDirectory())
		.map((entry) => entry.name)
		.sort()) {
		for (const [key, value] of Object.entries(readCatalog(locale))) {
			const baseKey = key.replace(pluralSuffix, '');
			const source = english[key] || english[baseKey] || english[`${baseKey}_other`] || key;
			const issues = validateTranslation(key, value, source);
			if (issues.length) {
				problems.push(`${locale}/translation.json: ${JSON.stringify(key)}: ${issues.join('; ')}`);
			}
		}
	}
	return problems;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
	const problems = checkCatalogs(resolve('src/lib/i18n/locales'));
	if (problems.length) {
		console.error(problems.join('\n'));
		console.error(`i18n: ${problems.length} invalid translation(s). Fix the entries above.`);
		process.exitCode = 1;
	} else {
		console.log('i18n: translation placeholders verified.');
	}
}
