import { get } from 'svelte/store';
import { setTheme } from './theme';
import { goto } from '$app/navigation';
import { WEBUI_API_BASE_URL } from '$lib/constants';
import { user, socket, desktopEvent, type DesktopEvent } from '$lib/stores';

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
	const unsubscribeEvents = tether.onEvent?.(async (payload) => {
		if (payload?.type === 'theme:update') {
			if (!['system', 'light', 'dark'].includes(payload.data?.theme))
				throw new Error('Invalid theme');
			setTheme(payload.data.theme);
			return;
		}
		if (!payload || !['query', 'voice'].includes(payload.type))
			throw new Error('Unsupported Tether event.');
		const userId = get(user)?.id;
		if (!userId)
			throw new Error('Sign in to WebUI, then send again. Your Spotlight draft is kept.');
		return new Promise<void>((resolve, reject) => {
			let active = true;
			const complete = (error?: string) => {
				if (!active) return;
				active = false;
				clearTimeout(timer);
				if (get(desktopEvent) === event) desktopEvent.set(null);
				if (error) reject(new Error(error));
				else resolve();
			};
			const event: DesktopEvent = {
				...payload,
				handoff: { isCurrent: () => active && get(user)?.id === userId, complete }
			};
			const timer = setTimeout(
				() => complete('WebUI is not ready. Try again from Tether.'),
				15_000
			);
			desktopEvent.set(event);
			void goto('/').catch((error) => complete(error.message || 'Could not open chat.'));
		});
	});
	return () => {
		unsubscribeToken();
		unsubscribeEvents?.();
	};
}
