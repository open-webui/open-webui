import { writable } from 'svelte/store';

export const locale = writable(localStorage.getItem('locale') || 'en-GB');

locale.subscribe((value) => {
	if (value) {
		localStorage.setItem('locale', value);
	}
});
