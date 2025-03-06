import { writable } from 'svelte/store';

export const selectedText = writable('');
export const selectionRange = writable(null);