// src/lib/net/apiFetch.ts
import { WEBUI_BASE_URL } from '$lib/constants';
import { get } from 'svelte/store';
import { socket } from '$lib/stores';

const API_BASE = WEBUI_BASE_URL ?? '/';

function buildURL(input: string | URL): URL {
	const url = new URL(typeof input === 'string' ? input : input.toString(), API_BASE);
	return url;
}

function normalizeInit(init: RequestInit = {}) {
	const headers = new Headers(init.headers ?? {});
	return { ...init, headers };
}

export async function apiFetch(input: string | URL, init: RequestInit = {}) {
	const s = get(socket);
	const id = s?.id ?? '';

	const url = buildURL(input);
	const next = normalizeInit(init);

	if (id) {
		(next.headers as Headers).set('sid', id);
	}

	return fetch(url.toString(), next);
}
