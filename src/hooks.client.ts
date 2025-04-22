import { user, sessionExpired } from '$lib/stores';
import type { HandleFetch } from '@sveltejs/kit';
import { get } from 'svelte/store'; // Nötig um Store-Wert außerhalb von Svelte-Komponenten zu lesen

/** @type {import('@sveltejs/kit').HandleFetch} */
export const handleFetch: HandleFetch = async ({ request, fetch }) => {
    const response = await fetch(request);

    if (response.status === 401) {
        // Prüfen, ob wir dachten, dass ein Benutzer angemeldet ist
        const currentUser = get(user); // Aktuellen Wert synchron holen

        if (currentUser) {
            console.warn(
                'Received 401 Unauthorized from API, session likely expired. Clearing user store and triggering modal.'
            );

            // Benutzer-Store leeren, um den ausgeloggten Zustand widerzuspiegeln
            user.set(undefined);

            // Flag setzen, um das Modal anzuzeigen
            sessionExpired.set(true);

            // Optional: Token aus localStorage entfernen (obwohl ein Refresh sowieso zur Auth-Seite führen sollte)
            // localStorage.removeItem('token');
        }
    }

    // Die Original-Antwort zurückgeben, damit der aufrufende Code sie erhält
    return response;
};
