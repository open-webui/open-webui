/**
 * StoryWeaver — Svelte Stores
 * ============================
 *
 * Description fonctionnelle:
 *   State management global pour l'interface StoryWeaver.
 *   Centralise la liste des romans, le roman courant, et la KB active.
 *
 * Règles métier:
 *   - `currentNovel` est initialisé depuis le backend à chaque chargement de layout.
 *   - `novels` est chargé uniquement en entrant dans l'espace StoryWeaver.
 *   - `activeKB` est chargé à la demande (page KB Editor).
 *   - Les stores sont writable — les composants peuvent les lire et les modifier via les actions.
 *
 * Architecture tech:
 *   - Imports des types depuis '$lib/apis/sw'.
 *   - Les actions (loadNovels, selectNovel, etc.) sont des fonctions async exportées
 *     qui mettent à jour les stores après appel API.
 *   - Pattern : action → API call → store.set() → UI réactive.
 */

import { writable, derived } from 'svelte/store';
import type { Writable } from 'svelte/store';
import type {
	Novel,
	KnowledgeBase,
	KBSection,
	KBItem,
	NovelCreateForm,
	NovelUpdateForm,
	Chapter,
	ChapterCreateForm,
	ChapterUpdateForm
} from '$lib/apis/sw';
import * as swApi from '$lib/apis/sw';

// ─── Stores primitifs ──────────────────────────────────────────────────────────

/** Liste complète des romans de l'utilisateur */
export const novels: Writable<Novel[]> = writable([]);

/** Roman actuellement sélectionné (session) — null si aucun */
export const currentNovel: Writable<Novel | null> = writable(null);

/** Knowledge Base du roman actif — null si non chargée */
export const activeKB: Writable<KnowledgeBase | null> = writable(null);

/** Liste des chapitres du roman actif */
export const chapters: Writable<Chapter[]> = writable([]);

/** État de chargement global */
export const swLoading: Writable<boolean> = writable(false);

/** Erreur globale StoryWeaver */
export const swError: Writable<string | null> = writable(null);

/** Mode d'affichage de l'éditeur : full | focus | research | outline */
export const editorMode = writable<'full' | 'focus' | 'research' | 'outline'>(
	(localStorage.getItem('swEditorMode') as any) || 'full'
);

// Persistance du mode
editorMode.subscribe((val) => {
	if (typeof window !== 'undefined') {
		localStorage.setItem('swEditorMode', val);
	}
});

// ─── Derived stores ────────────────────────────────────────────────────────────

/** true si un roman est sélectionné en session */
export const hasCurrentNovel = derived(currentNovel, ($n) => $n !== null);

/** Identifiant du roman courant (utile pour les routes) */
export const currentNovelId = derived(currentNovel, ($n) => $n?.id ?? null);

/** Romans par statut */
export const draftNovels = derived(novels, ($n) => $n.filter((n) => n.status === 'draft'));
export const activeNovels = derived(novels, ($n) => $n.filter((n) => n.status === 'in-progress'));

// ─── Actions ──────────────────────────────────────────────────────────────────

/**
 * Charge la liste des romans depuis le backend.
 */
export async function loadNovels(token: string): Promise<void> {
	swLoading.set(true);
	swError.set(null);
	try {
		const list = await swApi.getNovels(token);
		novels.set(list);
	} catch (e) {
		swError.set((e as Error).message);
	} finally {
		swLoading.set(false);
	}
}

/**
 * Charge le roman courant depuis le backend (session persistée).
 * Appelé au chargement du layout principal.
 */
export async function loadCurrentNovel(token: string): Promise<void> {
	try {
		const res = await swApi.getCurrentNovel(token);
		currentNovel.set(res.novel);
	} catch {
		currentNovel.set(null);
	}
}

/**
 * Sélectionne un roman comme roman courant.
 */
export async function selectNovel(token: string, novelId: string): Promise<void> {
	swLoading.set(true);
	swError.set(null);
	try {
		const res = await swApi.selectNovel(token, novelId);
		currentNovel.set(res.novel);
		activeKB.set(null); // Reset KB — sera rechargée si nécessaire
	} catch (e) {
		swError.set((e as Error).message);
	} finally {
		swLoading.set(false);
	}
}

/**
 * Désélectionne le roman courant.
 */
export async function deselectNovel(token: string): Promise<void> {
	swLoading.set(true);
	try {
		await swApi.deselectNovel(token);
		currentNovel.set(null);
		activeKB.set(null);
	} catch (e) {
		swError.set((e as Error).message);
	} finally {
		swLoading.set(false);
	}
}

/**
 * Crée un nouveau roman et rafraîchit la liste.
 */
export async function createNovel(token: string, form: NovelCreateForm): Promise<Novel | null> {
	swLoading.set(true);
	swError.set(null);
	try {
		const created = await swApi.createNovel(token, form);
		novels.update((list) => [created, ...list]);
		return created;
	} catch (e) {
		swError.set((e as Error).message);
		return null;
	} finally {
		swLoading.set(false);
	}
}

/**
 * Met à jour un roman existant.
 */
export async function updateNovel(
	token: string,
	id: string,
	form: NovelUpdateForm
): Promise<Novel | null> {
	swLoading.set(true);
	swError.set(null);
	try {
		const updated = await swApi.updateNovel(token, id, form);
		novels.update((list) => list.map((n) => (n.id === id ? updated : n)));
		// Mettre à jour currentNovel si c'est le roman édité
		currentNovel.update((cur) => (cur?.id === id ? updated : cur));
		return updated;
	} catch (e) {
		swError.set((e as Error).message);
		return null;
	} finally {
		swLoading.set(false);
	}
}

/**
 * Supprime un roman. Désélectionne si c'était le roman courant.
 */
export async function deleteNovel(token: string, id: string): Promise<boolean> {
	swLoading.set(true);
	swError.set(null);
	try {
		await swApi.deleteNovel(token, id);
		novels.update((list) => list.filter((n) => n.id !== id));
		currentNovel.update((cur) => (cur?.id === id ? null : cur));
		if (currentNovel) activeKB.set(null);
		return true;
	} catch (e) {
		swError.set((e as Error).message);
		return false;
	} finally {
		swLoading.set(false);
	}
}

/**
 * Charge la KB complète du roman actif.
 */
export async function loadActiveKB(token: string, novelId: string): Promise<void> {
	swLoading.set(true);
	swError.set(null);
	try {
		const kb = await swApi.getKB(token, novelId);
		activeKB.set(kb);
	} catch (e) {
		swError.set((e as Error).message);
	} finally {
		swLoading.set(false);
	}
}

/**
 * Ajoute un item à une section KB et met à jour le store.
 */
export async function addKBItem(
	token: string,
	novelId: string,
	section: KBSection,
	data: Record<string, unknown>
): Promise<KBItem | null> {
	swError.set(null);
	try {
		const item = await swApi.addKBItem(token, novelId, section, data);
		activeKB.update((kb) => {
			if (!kb) return kb;
			return { ...kb, [section]: [...(kb[section] ?? []), item] };
		});
		return item;
	} catch (e) {
		swError.set((e as Error).message);
		return null;
	}
}

/**
 * Met à jour un item KB et rafraîchit le store.
 */
export async function updateKBItem(
	token: string,
	novelId: string,
	section: KBSection,
	itemId: string,
	data: Record<string, unknown>
): Promise<KBItem | null> {
	swError.set(null);
	try {
		const updated = await swApi.updateKBItem(token, novelId, section, itemId, data);
		activeKB.update((kb) => {
			if (!kb) return kb;
			return {
				...kb,
				[section]: (kb[section] ?? []).map((i: KBItem) => (i.id === itemId ? updated : i))
			};
		});
		return updated;
	} catch (e) {
		swError.set((e as Error).message);
		return null;
	}
}

/**
 * Supprime un item KB et rafraîchit le store.
 */
export async function deleteKBItem(
	token: string,
	novelId: string,
	section: KBSection,
	itemId: string
): Promise<boolean> {
	swError.set(null);
	try {
		await swApi.deleteKBItem(token, novelId, section, itemId);
		activeKB.update((kb) => {
			if (!kb) return kb;
			return {
				...kb,
				[section]: (kb[section] ?? []).filter((i: KBItem) => i.id !== itemId)
			};
		});
		return true;
	} catch (e) {
		swError.set((e as Error).message);
		return false;
	}
}

// ─── Chapters — Actions ────────────────────────────────────────────────────────

/**
 * Charge tous les chapitres d'un roman.
 */
export async function loadChapters(token: string, novelId: string): Promise<void> {
	swLoading.set(true);
	swError.set(null);
	try {
		const list = await swApi.getChapters(token, novelId);
		chapters.set(list);
	} catch (e) {
		swError.set((e as Error).message);
	} finally {
		swLoading.set(false);
	}
}

/**
 * Ajoute un nouveau chapitre.
 */
export async function addChapter(
	token: string,
	novelId: string,
	form: ChapterCreateForm
): Promise<Chapter | null> {
	swLoading.set(true);
	swError.set(null);
	try {
		const created = await swApi.createChapter(token, novelId, form);
		chapters.update((list) => [...list, created]);
		return created;
	} catch (e) {
		swError.set((e as Error).message);
		return null;
	} finally {
		swLoading.set(false);
	}
}

/**
 * Met à jour un chapitre existant.
 */
export async function editChapter(
	token: string,
	chapterId: string,
	form: ChapterUpdateForm
): Promise<Chapter | null> {
	swError.set(null);
	try {
		const updated = await swApi.updateChapter(token, chapterId, form);
		chapters.update((list) => list.map((c) => (c.id === chapterId ? updated : c)));
		return updated;
	} catch (e) {
		swError.set((e as Error).message);
		return null;
	}
}

/**
 * Supprime un chapitre.
 */
export async function removeChapter(token: string, chapterId: string): Promise<boolean> {
	swError.set(null);
	try {
		await swApi.deleteChapter(token, chapterId);
		chapters.update((list) => list.filter((c) => c.id !== chapterId));
		return true;
	} catch (e) {
		swError.set((e as Error).message);
		return false;
	}
}

/**
 * Réordonne les chapitres en local et sur le serveur.
 */
export async function reorderChaptersAction(
	token: string,
	novelId: string,
	orderedIds: string[]
): Promise<void> {
	// Optimistic update : on réordonne tout de suite en local
	chapters.update((list) => {
		const map = new Map(list.map((c) => [c.id, c]));
		return orderedIds.map((id, index) => {
			const c = map.get(id);
			return c ? { ...c, order: index } : (null as any);
		}).filter(Boolean);
	});

	try {
		await swApi.reorderChapters(token, novelId, orderedIds);
	} catch (e) {
		swError.set((e as Error).message);
		// En cas d'erreur, on pourrait recharger pour annuler l'update optimiste
		await loadChapters(token, novelId);
	}
}
