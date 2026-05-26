// Cross-tab / cross-device sidebar sync — receives `type` events from the
// backend's broadcast_sidebar_event helper and patches the chat-list stores
// in place. The originating tab is excluded server-side (via X-Session-Id),
// so this only ever runs in *other* tabs / devices of the same user.
//
// Patching in place preserves the user's pagination + scroll position, which
// is why we avoid the `currentChatPage.set(1); chats.set(getChatList(...))`
// pattern that the legacy `chat:title` handler used.

import { get } from 'svelte/store';
import {
	chats,
	pinnedChats,
	tags,
	folders,
	chatId,
	chatTitle,
	currentChatPage,
	scrollPaginationEnabled
} from '$lib/stores';
import {
	getChatList,
	getPinnedChatList,
	getAllTags,
	getChatById
} from '$lib/apis/chats';
import { getFolders } from '$lib/apis/folders';
import { getTimeRange } from '$lib/utils';
import { clearLocalStorageCache } from '$lib/utils/cache';
import {
	SIDEBAR_CHATS_CACHE_KEY,
	SIDEBAR_PINNED_CHATS_CACHE_KEY,
	SIDEBAR_TAGS_CACHE_KEY,
	SIDEBAR_FOLDERS_CACHE_KEY
} from '$lib/constants/cache';

type ChatRow = {
	id: string;
	title: string;
	updated_at: number;
	created_at: number;
	pinned?: boolean;
	archived?: boolean;
	folder_id?: string | null;
	time_range?: string;
	[k: string]: any;
};

const decorate = (row: ChatRow): ChatRow => ({
	...row,
	time_range: getTimeRange(row.updated_at)
});

const removeById = (arr: any[] | null, id: string) =>
	arr ? arr.filter((c) => c.id !== id) : arr;

const upsertSorted = (arr: any[] | null, row: ChatRow): ChatRow[] => {
	const base = (arr ?? []).filter((c) => c.id !== row.id);
	base.unshift(row);
	// Keep the list ordered by updated_at desc; the sidebar then groups by time_range.
	base.sort((a, b) => (b.updated_at ?? 0) - (a.updated_at ?? 0));
	return base;
};

const invalidateChatsCaches = () => {
	clearLocalStorageCache(SIDEBAR_CHATS_CACHE_KEY);
	clearLocalStorageCache(SIDEBAR_PINNED_CHATS_CACHE_KEY);
};

export const applySidebarEvent = async (
	type: string,
	data: any,
	token: string
): Promise<void> => {
	if (!type) return;

	switch (type) {
		case 'chat:created': {
			if (!data?.id) return;
			const row = decorate(data);
			if (row.pinned) {
				pinnedChats.update((arr) => upsertSorted(arr, row));
			} else if (row.archived) {
				// Archived chats don't show in the sidebar — nothing to do.
			} else if (row.folder_id == null) {
				chats.update((arr) => upsertSorted(arr, row));
			}
			// If folder_id is set, RecursiveFolder.svelte fetches its own list
			// on expand — patching the top-level array would only mislead.
			invalidateChatsCaches();
			return;
		}

		case 'chat:deleted': {
			if (!data?.id) return;
			chats.update((arr) => removeById(arr, data.id));
			pinnedChats.update((arr) => removeById(arr, data.id) ?? []);
			invalidateChatsCaches();
			return;
		}

		case 'chat:title':
		case 'chat:renamed': {
			if (!data?.id) return;
			const patch = (c: any) =>
				c.id === data.id
					? {
							...c,
							title: data.title ?? c.title,
							updated_at: data.updated_at ?? c.updated_at,
							time_range: getTimeRange(data.updated_at ?? c.updated_at)
						}
					: c;
			chats.update((arr) =>
				arr ? [...arr].map(patch).sort((a, b) => (b.updated_at ?? 0) - (a.updated_at ?? 0)) : arr
			);
			pinnedChats.update((arr) => arr.map(patch));

			// If the receiving tab is currently viewing the renamed chat,
			// update the title in the header too — Chat.svelte does not
			// re-read on its own. (Fixes the long-standing bug where the
			// visible-chat gate suppressed sidebar updates entirely.)
			if (get(chatId) === data.id && data.title) {
				chatTitle.set(data.title);
			}

			invalidateChatsCaches();
			return;
		}

		case 'chat:pinned': {
			if (!data?.id) return;
			const targetPinned = !!data.pinned;
			let row: ChatRow | undefined;
			chats.update((arr) => {
				if (!arr) return arr;
				const idx = arr.findIndex((c) => c.id === data.id);
				if (idx >= 0) {
					row = arr[idx];
					return [...arr.slice(0, idx), ...arr.slice(idx + 1)];
				}
				return arr;
			});
			pinnedChats.update((arr) => {
				const idx = arr.findIndex((c) => c.id === data.id);
				if (idx >= 0) {
					if (!row) row = arr[idx];
					return [...arr.slice(0, idx), ...arr.slice(idx + 1)];
				}
				return arr;
			});

			// If we don't have the row locally (it was on a later, unloaded page),
			// fetch a minimal record so we can still place it correctly.
			if (!row) {
				const fetched = await getChatById(token, data.id).catch(() => null);
				if (!fetched) {
					invalidateChatsCaches();
					return;
				}
				row = {
					id: fetched.id,
					title: fetched.title,
					updated_at: fetched.updated_at,
					created_at: fetched.created_at,
					pinned: targetPinned,
					archived: fetched.archived,
					folder_id: fetched.folder_id
				};
			}

			const patched: ChatRow = decorate({ ...row, pinned: targetPinned });
			if (targetPinned) {
				pinnedChats.update((arr) => upsertSorted(arr, patched));
			} else if (patched.folder_id == null && !patched.archived) {
				chats.update((arr) => upsertSorted(arr, patched));
			}
			invalidateChatsCaches();
			return;
		}

		case 'chat:archived': {
			if (!data?.id) return;
			if (data.archived) {
				chats.update((arr) => removeById(arr, data.id));
				pinnedChats.update((arr) => removeById(arr, data.id) ?? []);
			} else {
				const row = decorate(data as ChatRow);
				if (row.pinned) {
					pinnedChats.update((arr) => upsertSorted(arr, row));
				} else if (row.folder_id == null) {
					chats.update((arr) => upsertSorted(arr, row));
				}
			}
			invalidateChatsCaches();
			return;
		}

		case 'chat:folder': {
			if (!data?.id) return;
			const patch = (c: any) =>
				c.id === data.id ? { ...c, folder_id: data.folder_id ?? null } : c;
			chats.update((arr) => {
				if (!arr) return arr;
				// Moving a chat *into* a folder hides it from the top-level list;
				// moving it *out* (folder_id === null) should keep it there. The
				// sidebar's main loop filters by folder_id implicitly via the
				// folder rendering path, so just patch in place — RecursiveFolder
				// re-fetches its own contents on next expand.
				return arr.map(patch);
			});
			pinnedChats.update((arr) => arr.map(patch));
			invalidateChatsCaches();
			return;
		}

		case 'chat:tags': {
			const fresh = await getAllTags(token).catch(() => null);
			if (Array.isArray(fresh)) {
				tags.set(fresh);
			}
			clearLocalStorageCache(SIDEBAR_TAGS_CACHE_KEY);
			return;
		}

		case 'folder:created':
		case 'folder:updated': {
			const fresh = await getFolders(token).catch(() => null);
			if (Array.isArray(fresh)) {
				folders.set(fresh);
			}
			clearLocalStorageCache(SIDEBAR_FOLDERS_CACHE_KEY);
			return;
		}

		case 'folder:deleted': {
			// Cascade: chats inside the folder were deleted server-side. Refetch
			// folders + first-page chats + pinned (the cascaded chats could have
			// been pinned). Cheaper than fanning out N chat:deleted events and
			// safer than guessing which chats were inside.
			const [freshFolders, freshChats, freshPinned] = await Promise.all([
				getFolders(token).catch(() => null),
				getChatList(token, 1).catch(() => null),
				getPinnedChatList(token).catch(() => null)
			]);
			if (Array.isArray(freshFolders)) folders.set(freshFolders);
			if (Array.isArray(freshChats)) {
				currentChatPage.set(1);
				chats.set(freshChats);
				scrollPaginationEnabled.set(true);
			}
			if (Array.isArray(freshPinned)) pinnedChats.set(freshPinned);
			clearLocalStorageCache(SIDEBAR_FOLDERS_CACHE_KEY);
			invalidateChatsCaches();
			return;
		}

		case 'chats:bulk': {
			// archive_all / unarchive_all / delete_all — easier to refetch the
			// world than to model the bulk transition locally.
			const [freshChats, freshPinned, freshTags, freshFolders] = await Promise.all([
				getChatList(token, 1).catch(() => null),
				getPinnedChatList(token).catch(() => null),
				getAllTags(token).catch(() => null),
				getFolders(token).catch(() => null)
			]);
			currentChatPage.set(1);
			if (Array.isArray(freshChats)) chats.set(freshChats);
			if (Array.isArray(freshPinned)) pinnedChats.set(freshPinned);
			if (Array.isArray(freshTags)) tags.set(freshTags);
			if (Array.isArray(freshFolders)) folders.set(freshFolders);
			scrollPaginationEnabled.set(true);
			invalidateChatsCaches();
			clearLocalStorageCache(SIDEBAR_TAGS_CACHE_KEY);
			clearLocalStorageCache(SIDEBAR_FOLDERS_CACHE_KEY);
			return;
		}

		default:
			return;
	}
};

export const SIDEBAR_EVENT_TYPES = new Set([
	'chat:created',
	'chat:deleted',
	'chat:renamed',
	'chat:title',
	'chat:pinned',
	'chat:archived',
	'chat:folder',
	'chat:tags',
	'folder:created',
	'folder:updated',
	'folder:deleted',
	'chats:bulk'
]);
