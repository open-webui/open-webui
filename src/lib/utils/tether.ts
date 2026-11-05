import { get } from 'svelte/store';
import { goto } from '$app/navigation';
import { WEBUI_API_BASE_URL } from '$lib/constants';
import { user, socket } from '$lib/stores';
import { receiveSpotlightQuery } from './spotlight';

let nativeFetch: typeof fetch;
let renewal: Promise<boolean> | undefined;
let applying: Promise<void> = Promise.resolve();
let generation = 0;

export function applyTetherToken(access: { token: string; expiresAt: number | null } | null) {
	const expected = generation;
	if (!access) {
		generation++;
		localStorage.removeItem('token');
		document.cookie = 'token=; Max-Age=0; path=/';
		user.set(undefined);
		get(socket)?.disconnect();
		return Promise.resolve();
	}
	const operation = applying
		.catch(() => {})
		.then(async () => {
			if (expected !== generation) return;
			const response = await nativeFetch(`${WEBUI_API_BASE_URL}/auths/`, {
				headers: { Authorization: `Bearer ${access.token}` },
				credentials: 'include'
			});
			if (!response.ok) throw new Error('Could not validate the renewed WebUI session.');
			const sessionUser = await response.json();
			if (expected !== generation) return;
			const current = get(user);
			if (current && current.id !== sessionUser.id)
				throw new Error('Sign out before switching accounts.');
			localStorage.token = access.token;
			user.set(sessionUser);
			const connection = get(socket);
			if (connection) {
				if (!connection.connected) connection.connect();
				connection.emit('user-join', { auth: { token: access.token } });
			}
			if (location.pathname.endsWith('/auth')) await goto('/');
		});
	applying = operation;
	return operation;
}

export function renewTetherSession(force = false): Promise<boolean> {
	if (!window.tether) return Promise.resolve(false);
	if (renewal) return renewal;
	renewal = window.tether
		.refresh(force)
		.then(async (access) => {
			if (!access) return false;
			await applyTetherToken(access);
			return true;
		})
		.finally(() => {
			renewal = undefined;
		});
	return renewal;
}

export async function initializeTether(fetcher: typeof fetch): Promise<() => void> {
	nativeFetch = fetcher;
	const tether = window.tether;
	if (!tether) return () => {};
	const unsubscribeToken = tether.onToken((access) => {
		void applyTetherToken(access).catch(() => {});
	});
	// Connectivity errors must not erase credentials or force a sign-out.
	await renewTetherSession().catch(() => {});
	const unsubscribeQuery = tether.onQuery?.((query) =>
		receiveSpotlightQuery(
			query,
			() => goto('/'),
			() => get(user)?.id
		)
	);
	return () => {
		unsubscribeToken();
		unsubscribeQuery?.();
	};
}
