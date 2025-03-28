import { get } from 'svelte/store';
import { config, user } from '$lib/stores';
import { goto } from '$app/navigation';

export const LOCALSTORAGE_REFERRED_TO_SIGNUP = 'ionosgptUserReferredToSignup';

export const signup = (): void => {
	localStorage.setItem(LOCALSTORAGE_REFERRED_TO_SIGNUP, JSON.stringify(true));

	const url: string|null = get(config)?.features?.ionos_registration_url ?? null;

	if (url) {
		window.location.href = url;
	}
}

export const handleSignupDone = async (): Promise<void> => {
	const userIsAuthenticated = !!get(user);
	const userWentThroughSignup: boolean = JSON.parse(localStorage.getItem(LOCALSTORAGE_REFERRED_TO_SIGNUP) ?? 'false');

	if (userWentThroughSignup && userIsAuthenticated) {
		console.log('User went through signup, sending them to the explore page ...');

		localStorage.removeItem(LOCALSTORAGE_REFERRED_TO_SIGNUP);

		await goto('/explore');
	} else if (!userIsAuthenticated) {
		console.log('User went through signup, but is not authenticated. ');
	}
}
