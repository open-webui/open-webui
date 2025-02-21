import { get } from 'svelte/store';
import { goto } from '$app/navigation';
import { user } from '$lib/stores';

export const LOCALSTORAGE_START_MODEL_KEY = 'ionosgptStartWithModel';

const isUserAuthenticated = () => !!get(user);

export const getAgent = (): string => {
	const agent = localStorage.getItem(LOCALSTORAGE_START_MODEL_KEY) ?? '';
	localStorage.removeItem(LOCALSTORAGE_START_MODEL_KEY);
	return agent;
}

export const selectAgent = async (id: string): void => {
	console.log('Store agent', id);
	localStorage.setItem(LOCALSTORAGE_START_MODEL_KEY, id);

	if (isUserAuthenticated()) {
		await goto('/');
	} else {
		await goto('/auth');
	}
}
