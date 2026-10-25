import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
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

/** @param {string} key @param {unknown} value @param {string} source */
export function repairTranslation(key, value, source = key) {
	if (typeof value !== 'string' || !validateTranslation(key, value, source).length) return value;
	let repaired = value;
	const expected = interpolation(source);
	for (const name of expected.names) {
		// Recover placeholders accidentally written with only one pair of braces.
		if (!interpolation(repaired).names.has(name)) {
			repaired = repaired.replaceAll(`{${name}}`, `{{${name}}}`);
		}
	}
	const missing = [...expected.names].filter((name) => !interpolation(repaired).names.has(name));
	if (
		missing.length === 1 &&
		!source.includes('[') &&
		(repaired.match(/\[[^\[\]]+\]/g) ?? []).length === 1
	) {
		repaired = repaired.replace(/\[[^\[\]]+\]/, () => `{{${missing[0]}}}`);
	}
	// Unwrap escaped literal examples without changing their translated surroundings.
	for (const [literal] of source.matchAll(/\{[^{}]+\}/g)) {
		repaired = repaired.replaceAll("{{'{" + literal + "}'}}", literal);
	}
	for (const [url] of source.matchAll(/https?:\/\/[^\s)]+/g)) {
		repaired = repaired.replaceAll(`{${url}}`, url);
	}
	return validateTranslation(key, repaired, source).length ? value : repaired;
}

/** @param {string} directory @param {boolean} fix */
export function checkCatalogs(directory, fix = false) {
	/** @param {string} locale @returns {Record<string, string>} */
	const readCatalog = (locale) =>
		JSON.parse(readFileSync(join(directory, locale, 'translation.json'), 'utf8'));
	const english = readCatalog('en-US');
	const problems = [];
	let fixed = 0;
	for (const locale of readdirSync(directory, { withFileTypes: true })
		.filter((entry) => entry.isDirectory())
		.map((entry) => entry.name)
		.sort()) {
		const catalog = readCatalog(locale);
		let changed = false;
		for (const [key, value] of Object.entries(catalog)) {
			const baseKey = key.replace(pluralSuffix, '');
			const source = english[key] || english[baseKey] || english[`${baseKey}_other`] || key;
			const repaired = fix ? repairTranslation(key, value, source) : value;
			if (repaired !== value) {
				catalog[key] = repaired;
				changed = true;
				fixed++;
			}
			const issues = validateTranslation(key, repaired, source);
			if (issues.length) {
				problems.push(`${locale}/translation.json: ${JSON.stringify(key)}: ${issues.join('; ')}`);
			}
		}
		if (changed) {
			writeFileSync(
				join(directory, locale, 'translation.json'),
				JSON.stringify(catalog, null, '\t') + '\n'
			);
		}
	}
	return { problems, fixed };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
	const fix = process.argv.includes('--fix');
	const { problems, fixed } = checkCatalogs(resolve('src/lib/i18n/locales'), fix);
	if (fixed) console.log(`i18n: repaired ${fixed} translation(s).`);
	if (problems.length) {
		console.error(problems.join('\n'));
		console.error(`i18n: ${problems.length} invalid translation(s). Fix the entries above.`);
		process.exitCode = 1;
	} else {
		console.log('i18n: translation placeholders verified.');
	}
}
