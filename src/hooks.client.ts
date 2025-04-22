import { user, sessionExpired } from '$lib/stores';
import { get } from 'svelte/store';
import type { HandleClientError } from '@sveltejs/kit';

export const handleError: HandleClientError = ({ error, event }) => {
  console.error('handleError caught:', error);

    if (
        typeof error === 'object' &&
        error !== null &&
        ( (error as any).status === 401 || (error as any).detail?.includes('401 Unauthorized') )
     ) {

        const currentUser = get(user);
        console.log('handleError detected 401-like error for', event.url, 'currentUser:', currentUser);

        if (currentUser) {
            console.warn(
                'handleError: 401 Unauthorized detected. Clearing user store and triggering modal.'
            );
            user.set(undefined);
            sessionExpired.set(true);
        } else {
     console.log('handleError: 401-like error detected, but currentUser was already null/undefined.');
    }
    }

  return {
    message: (error as any)?.message ?? 'An unexpected client error occurred',
  };
};
