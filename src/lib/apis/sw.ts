/**
 * StoryWeaver — API Client TypeScript
 * =====================================
 *
 * Description fonctionnelle:
 *   Client fetch pour tous les endpoints StoryWeaver backend.
 *   Couvre : Novels (CRUD + Session) + Knowledge Base (CRUD par section).
 *
 * Règles métier:
 *   - Toutes les fonctions exigent un `token` Bearer pour l'authentification.
 *   - Les erreurs HTTP lèvent des Error avec le message du backend.
 *   - BASE_URL = WEBUI_API_BASE_URL (ex: http://localhost:8080/api)
 *
 * Architecture tech:
 *   - Fonctions pures sans état — le state est géré dans sw.ts (stores).
 *   - Typage strict TypeScript sur tous les types Novels et KB.
 */

import { WEBUI_API_BASE_URL } from '$lib/constants';

// ─── Types ────────────────────────────────────────────────────────────────────

export type NovelStatus = 'draft' | 'in-progress' | 'completed' | 'archived';

export interface Novel {
	id: string;
	user_id: string;
	title: string;
	description?: string | null;
	status: NovelStatus;
	created_at: number;
	updated_at: number;
}

export interface NovelCreateForm {
	title: string;
	description?: string;
	status?: NovelStatus;
}

export interface NovelUpdateForm {
	title?: string;
	description?: string;
	status?: NovelStatus;
}

export interface CurrentNovelResponse {
	novel: Novel | null;
	is_selected: boolean;
}

// KB types
export type KBSection = 'universe_docs' | 'characters' | 'locations' | 'objects' | 'timeline';

export interface KBItem {
	id: string;
	[key: string]: unknown;
}

export interface KnowledgeBase {
	id: string;
	novel_id: string;
	universe_docs: KBItem[];
	characters: KBItem[];
	locations: KBItem[];
	objects: KBItem[];
	timeline: KBItem[];
	updated_at: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

const SW_BASE = `${WEBUI_API_BASE_URL}/sw`;

async function swFetch<T>(
	token: string,
	path: string,
	options: RequestInit = {}
): Promise<T> {
	const res = await fetch(`${SW_BASE}${path}`, {
		...options,
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`,
			...(options.headers ?? {})
		}
	});

	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: res.statusText }));
		throw new Error(err?.detail ?? `HTTP ${res.status}`);
	}

	return res.json() as Promise<T>;
}

// ─── Novels — CRUD ────────────────────────────────────────────────────────────

export const getNovels = (token: string): Promise<Novel[]> =>
	swFetch<Novel[]>(token, '/novels/');

export const getNovelById = (token: string, id: string): Promise<Novel> =>
	swFetch<Novel>(token, `/novels/${id}`);

export const createNovel = (token: string, form: NovelCreateForm): Promise<Novel> =>
	swFetch<Novel>(token, '/novels/create', {
		method: 'POST',
		body: JSON.stringify(form)
	});

export const updateNovel = (
	token: string,
	id: string,
	form: NovelUpdateForm
): Promise<Novel> =>
	swFetch<Novel>(token, `/novels/${id}/update`, {
		method: 'POST',
		body: JSON.stringify(form)
	});

export const deleteNovel = (token: string, id: string): Promise<boolean> =>
	swFetch<boolean>(token, `/novels/${id}/delete`, { method: 'DELETE' });

// ─── Novels — Session Management ──────────────────────────────────────────────

export const getCurrentNovel = (token: string): Promise<CurrentNovelResponse> =>
	swFetch<CurrentNovelResponse>(token, '/novels/current');

export const selectNovel = (token: string, id: string): Promise<CurrentNovelResponse> =>
	swFetch<CurrentNovelResponse>(token, `/novels/${id}/select`, { method: 'POST' });

export const deselectNovel = (token: string): Promise<CurrentNovelResponse> =>
	swFetch<CurrentNovelResponse>(token, '/novels/deselect', { method: 'POST' });

// ─── Knowledge Base ────────────────────────────────────────────────────────────

export const getKB = (token: string, novelId: string): Promise<KnowledgeBase> =>
	swFetch<KnowledgeBase>(token, `/novels/${novelId}/kb/`);

export const getKBSection = (
	token: string,
	novelId: string,
	section: KBSection
): Promise<KBItem[]> =>
	swFetch<KBItem[]>(token, `/novels/${novelId}/kb/${section}`);

export const addKBItem = (
	token: string,
	novelId: string,
	section: KBSection,
	data: Record<string, unknown>
): Promise<KBItem> =>
	swFetch<KBItem>(token, `/novels/${novelId}/kb/${section}/add`, {
		method: 'POST',
		body: JSON.stringify({ data })
	});

export const updateKBItem = (
	token: string,
	novelId: string,
	section: KBSection,
	itemId: string,
	data: Record<string, unknown>
): Promise<KBItem> =>
	swFetch<KBItem>(token, `/novels/${novelId}/kb/${section}/${itemId}/update`, {
		method: 'POST',
		body: JSON.stringify({ data })
	});

export const deleteKBItem = (
	token: string,
	novelId: string,
	section: KBSection,
	itemId: string
): Promise<boolean> =>
	swFetch<boolean>(token, `/novels/${novelId}/kb/${section}/${itemId}/delete`, {
		method: 'DELETE'
	});

export const replaceKBSection = (
	token: string,
	novelId: string,
	section: KBSection,
	items: Record<string, unknown>[]
): Promise<KnowledgeBase> =>
	swFetch<KnowledgeBase>(token, `/novels/${novelId}/kb/${section}/replace`, {
		method: 'PUT',
		body: JSON.stringify({ items })
	});
