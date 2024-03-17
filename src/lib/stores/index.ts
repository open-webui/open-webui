import { APP_NAME } from '$lib/constants';
import { writable, derived } from 'svelte/store';

// Backend
export const WEBUI_NAME = writable(APP_NAME);
export const config = writable(undefined);
export const user = writable(undefined);

// Frontend
const rawThemeSetting = writable('system');
export const theme = derived(rawThemeSetting, ($rawThemeSetting) => {
	if ($rawThemeSetting === 'system') {
		return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
	}
	return $rawThemeSetting;
});

window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
	rawThemeSetting.update((currentTheme) => {
		if (currentTheme === 'system') {
			return e.matches ? 'dark' : 'light';
		}
		return currentTheme;
	});
});

export function setTheme(theme) {
	rawThemeSetting.set(theme);
	localStorage.setItem('theme', theme);
}

export const chatId = writable('');

export const chats = writable([]);
export const tags = writable([]);
export const models = writable([]);

export const modelfiles = writable([]);
export const prompts = writable([]);
export const documents = writable([
	{
		collection_name: 'collection_name',
		filename: 'filename',
		name: 'name',
		title: 'title'
	},
	{
		collection_name: 'collection_name1',
		filename: 'filename1',
		name: 'name1',
		title: 'title1'
	}
]);

export const settings = writable({});
export const showSettings = writable(false);
export const showChangelog = writable(false);
