import type { i18n } from 'i18next';
import { canSearchSetting } from './settings-access';

export type SettingsTab = {
	id: string;
	titleKey: string;
	title?: string;
	searchPrefixes: string[];
};
export type SettingsAccessContext = { user: any; config: any };
export type SettingsSearchIndex = { id: string; entries: string[][] }[];

export const normalizeSettingsSearch = (text: string): string =>
	text
		.toLowerCase()
		.normalize('NFD')
		.replace(/(\p{Script=Latin})\p{M}+/gu, '$1')
		.normalize('NFC')
		.replace(/[^\p{L}\p{M}\p{N}]+/gu, ' ')
		.trim()
		.replace(/\s+/g, ' ');

export function buildSettingsSearchIndex(
	tabs: SettingsTab[],
	english: Record<string, string>,
	translator: Pick<i18n, 't'>,
	context: SettingsAccessContext
): SettingsSearchIndex {
	const variants = (key: string) => {
		const fallback = english[key] || (key.startsWith('settings.') ? '' : key);
		return [
			...new Set(
				[
					translator.t(key, { lng: 'en-US', defaultValue: fallback }),
					translator.t(key, { defaultValue: fallback })
				].filter(
					(text): text is string =>
						typeof text === 'string' &&
						!!text.trim() &&
						(!key.startsWith('settings.') || text !== key)
				)
			)
		]
			.map(normalizeSettingsSearch)
			.filter(Boolean);
	};
	const keys = Object.keys(english).filter((key) => /\.(label|title)$/.test(key));
	return tabs.map((tab) => {
		const location = [
			...variants(tab.titleKey),
			...variants(tab.id.startsWith('admin:') ? 'Admin' : 'Personal')
		];
		const entries = keys
			.filter(
				(key) =>
					tab.searchPrefixes.some((prefix) => key.startsWith(prefix)) &&
					canSearchSetting(key, tab.id, context)
			)
			.map((key) => [
				...variants(key),
				...variants(key.replace(/\.(label|title)$/, '.description')),
				...location
			]);
		// The tab itself is always a destination, including panels with only dynamic records.
		return { id: tab.id, entries: [location, ...entries] };
	});
}

export function searchSettingsTabs(index: SettingsSearchIndex, query: string): string[] {
	const words = normalizeSettingsSearch(query).split(' ').filter(Boolean);
	return index
		.filter(
			(tab) =>
				!words.length ||
				tab.entries.some((entry) =>
					words.every((word) => entry.some((text) => text.includes(word)))
				)
		)
		.map((tab) => tab.id);
}
