// Merges Arabic translations produced in scripts/arabic-translations-part*.json into the ar locale.
// Only fills keys whose current value is empty. Reports leftovers.
// Run: node scripts/merge-arabic-translations.mjs
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const LOCALE_PATH = path.join(__dirname, '..', 'src', 'lib', 'i18n', 'locales', 'ar', 'translation.json');

const partsDir = __dirname;
const partFiles = fs
	.readdirSync(partsDir)
	.filter((f) => /^arabic-translations-part\d+\.json$/.test(f))
	.sort((a, b) => {
		const na = parseInt(a.match(/part(\d+)/)[1], 10);
		const nb = parseInt(b.match(/part(\d+)/)[1], 10);
		return na - nb;
	});

const translations = {};
for (const f of partFiles) {
	const data = JSON.parse(fs.readFileSync(path.join(partsDir, f), 'utf8'));
	for (const [k, v] of Object.entries(data)) {
		translations[k] = v;
	}
}
console.log(`Loaded translations from ${partFiles.length} part file(s): ${Object.keys(translations).length} entries`);

const locale = JSON.parse(fs.readFileSync(LOCALE_PATH, 'utf8'));

let filled = 0;
const leftover = [];
const bad = [];
for (const [key, value] of Object.entries(translations)) {
	if (!(key in locale)) {
		bad.push(key);
		continue;
	}
	if (locale[key] === '' && typeof value === 'string' && value.trim() !== '') {
		locale[key] = value;
		filled++;
	} else if (locale[key] !== '') {
		leftover.push(key); // already translated, skipped
	}
}

fs.writeFileSync(LOCALE_PATH, JSON.stringify(locale, null, '\t') + '\n', 'utf8');
console.log(`Filled ${filled} translations`);
console.log(`Skipped (already non-empty): ${leftover.length}`);
if (bad.length) console.log(`WARNING keys not in locale: ${bad.length}`, bad.slice(0, 20).join(' | '));

const remaining = Object.entries(locale).filter(([, v]) => String(v) === '');
console.log(`Remaining empty values in ar locale: ${remaining.length}`);
