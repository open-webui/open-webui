import { user, sessionExpired } from '$lib/stores';
import type { HandleFetch } from '@sveltejs/kit';
import { get } from 'svelte/store';

/** @type {import('@sveltejs/kit').HandleFetch} */
export const handleFetch: HandleFetch = async ({ request, fetch }) => {
    console.log(`handleFetch called for: ${request.url}`);

    const response = await fetch(request);

    if (response.status === 401) {
        const currentUser = get(user);
        console.log('Intercepted 401 for', request.url, 'currentUser:', currentUser);

        if (currentUser) {
            console.warn(
                'Received 401 Unauthorized from API, session likely expired. Clearing user store and triggering modal.'
            );
            user.set(undefined);
            sessionExpired.set(true);
        } else {
            console.log('Received 401, but currentUser was already null/undefined.');
        }
    }

    return response;
};
