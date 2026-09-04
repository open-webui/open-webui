import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import i18next from 'i18next';
import { get } from 'svelte/store';
import store, { initI18n, loadBundledResource, updateI18n } from './index';
import {
	validateDictionary,
	validateI18n,
	i18nToEntries,
	entriesToI18n
} from '$lib/utils/translationDictionary';
import {
	resolveLocalizedModelName,
	resolveLocalizedModelPromptSuggestions,
	resolveLocalizedPromptSuggestions,
	resolveLocalizedResource,
	resolveLocalizedString,
	localizeValvesSchema
} from '$lib/utils/localizedContent';

beforeAll(async () => {
	await initI18n('en-US');
});

afterEach(async () => {
	await updateI18n({});
	await i18next.changeLanguage('en-US');
});

describe('UI i18n', () => {
	it('round-trips banner-style rows and preserves translations when originals are renamed', () => {
		const original = {
			'en-US': { Models: 'Assistants' },
			'de-DE': { Models: 'Assistenten', Save: 'Speichern' }
		};
		const entries = i18nToEntries(original);
		expect(entries.map((entry) => entry.content)).toEqual(['Models', 'Save']);
		expect(entriesToI18n(entries)).toEqual(original);
		entries[0].content = 'Tools';
		expect(entriesToI18n(entries)).toEqual({
			'en-US': { Tools: 'Assistants' },
			'de-DE': { Tools: 'Assistenten', Save: 'Speichern' }
		});
		expect(entriesToI18n(entries.slice(1))).toEqual({ 'de-DE': { Save: 'Speichern' } });
	});

	it('keeps empty drafts local and rejects duplicate or missing originals without losing translations', () => {
		expect(
			entriesToI18n([
				{ content: '', i18n: {} },
				{ content: 'Models', i18n: {} }
			])
		).toEqual({});
		const entries = i18nToEntries({ 'en-US': { Models: 'Assistants' } });
		expect(() => entriesToI18n([...entries, { content: 'Models', i18n: {} }])).toThrow('Duplicate');
		entries[0].content = '';
		expect(() => entriesToI18n(entries)).toThrow('Original text');
		expect(entries[0].i18n['en-US'].content).toBe('Assistants');
	});

	it('loads bootstrap overrides without modifying bundled resources', async () => {
		await initI18n('en-US', { 'en-US': { Models: 'Assistants' } });
		expect(i18next.t('Models')).toBe('Assistants');
		expect(i18next.t('Save')).toBe('Save');
		expect((await loadBundledResource('en-US')).Models).not.toBe('Assistants');
	});

	it('updates loaded languages, notifies subscribers and restores deleted keys', async () => {
		let notifications = 0;
		const unsubscribe = store.subscribe(() => notifications++);
		await updateI18n({ 'en-US': { Models: 'Assistants', 'Custom old key': 'Legacy' } });
		expect(get(store).t('Models')).toBe('Assistants');
		await updateI18n({});
		expect(i18next.t('Models')).toBe('Models');
		expect(i18next.t('Custom old key')).toBe('Custom old key');
		expect(notifications).toBeGreaterThan(2);
		unsubscribe();
	});

	it('uses saved overrides for later language loads and retains pluralization and interpolation', async () => {
		await updateI18n({
			'fr-FR': { Models: 'Assistants FR' },
			'en-US': {
				'{{count}} files_one': '{{count}} document',
				'{{count}} files_other': '{{count}} documents',
				'Hello {{name}}': 'Welcome {{name}}'
			}
		});
		await i18next.changeLanguage('fr');
		expect(i18next.t('Models')).toBe('Assistants FR');
		await i18next.changeLanguage('en-US');
		expect(i18next.t('{{count}} files', { count: 1 })).toBe('1 document');
		expect(i18next.t('{{count}} files', { count: 2 })).toBe('2 documents');
		expect(i18next.t('Hello {{name}}', { name: 'Sam' })).toBe('Welcome Sam');
		await updateI18n({});
		await i18next.changeLanguage('fr');
		expect(i18next.t('Models')).toBe((await loadBundledResource('fr-FR')).Models);
	});

	it('validates imports and removes empty overrides without trimming meaningful text', () => {
		expect(validateI18n({ 'en-US': { Models: ' Assistants ', Save: ' ' }, de: {} })).toEqual({
			'en-US': { Models: ' Assistants ' }
		});
		expect(() => validateDictionary({ 'Hello {{name}}': 'Hi {{other}}' })).toThrow('placeholders');
		expect(() => validateDictionary({ Models: 2 })).toThrow('string');
		expect(() => validateDictionary([])).toThrow('JSON object');
		expect(() => validateI18n(JSON.parse('{"__proto__":{"Models":"Bad"}}'))).toThrow('language');
		expect(() => validateDictionary(JSON.parse('{"constructor":"Bad"}'))).toThrow('key');
		expect(validateDictionary({ 'Old key': 'Retained' })).toEqual({ 'Old key': 'Retained' });
	});

	it('keeps resource localization independent of built-in UI overrides', async () => {
		await updateI18n({
			'en-US': { Models: 'Assistants', name: 'Not a resource name', content: 'Not banner content' }
		});
		const meta = {
			i18n: {
				'en-US': { name: 'Resource name', suggestion_prompts: [], 'valves.mode.title': 'Speed' }
			}
		};
		expect(resolveLocalizedModelName({ name: 'Default model', meta }, 'en-US')).toBe(
			'Resource name'
		);
		expect(resolveLocalizedResource({ name: 'Default tool', meta }, 'en-US')).toBe('Resource name');
		expect(resolveLocalizedModelPromptSuggestions({ meta }, 'en-US')).toEqual([]);
		expect(
			resolveLocalizedPromptSuggestions([], { 'en-US': { suggestion_prompts: [] } }, 'en-US')
		).toEqual([]);
		expect(
			resolveLocalizedString(
				'Default banner',
				{ 'en-US': { content: 'Banner message' } },
				'en-US',
				'content'
			)
		).toBe('Banner message');
		const schema = { properties: { mode: { title: 'Mode', enum: ['fast'], default: 'fast' } } };
		const localized = localizeValvesSchema(schema, 'en-US', meta);
		expect(localized.properties.mode).toEqual({
			title: 'Speed',
			description: '',
			enum: ['fast'],
			default: 'fast'
		});
		expect(schema.properties.mode.title).toBe('Mode');
	});
});
