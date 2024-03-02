import { get } from 'svelte/store';
import { settings } from './stores';
import { Settings } from './types';

// place files you want to import through the `$lib` alias in this folder.
export const saveSettings = (update: Partial<Settings>) => {
	settings.update((state) => ({ ...state, ...update }));
	localStorage.setItem('settings', JSON.stringify(get(settings)));
};
