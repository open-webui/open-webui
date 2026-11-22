import { get, readonly, writable } from 'svelte/store';
import { getChatList, getPinnedChatList } from '$lib/apis/chats';
import { markFolderChatsDirty, updateFolderChatLists } from './folderStates';
import { renameChatTabs } from './chatViewStates';

type ChatListItem = {
	id: string;
	pending_approval?: boolean;
	[key: string]: unknown;
};

const chatsStore = writable<ChatListItem[] | null>(null);
const pinnedChatsStore = writable<ChatListItem[]>([]);

export const chats = readonly(chatsStore);
export const pinnedChats = readonly(pinnedChatsStore);

// Latest few chats for the new-chat landing, from folders and pins too (the sidebar's
// list leaves those out). Null until the first load, so the landing can wait for it.
const recentChatsStore = writable<ChatListItem[] | null>(null);
export const recentChats = readonly(recentChatsStore);

const RECENT_CHATS_LIMIT = 5;

export const refreshRecentChats = async (token: string = '') => {
	const list = (await getChatList(token, 1, true, true, {
		sortBy: 'updated_at',
		status: 'active',
		limit: RECENT_CHATS_LIMIT
	}).catch(() => [])) as ChatListItem[];
	recentChatsStore.set((list ?? []).slice(0, RECENT_CHATS_LIMIT));
};

// How the sidebar's chat list is filtered and sorted; remembered per browser.
export type ChatListView = {
	status: 'active' | 'archived' | 'all';
	sortBy: 'updated_at' | 'created_at';
};

const chatListViewStore = writable<ChatListView>({
	status: 'active',
	sortBy: 'updated_at',
	...(() => {
		try {
			return JSON.parse(localStorage.getItem('sidebar-chat-list-view') ?? '{}');
		} catch {
			return {};
		}
	})()
});
export const chatListView = readonly(chatListViewStore);

export const setChatListView = async (token: string, patch: Partial<ChatListView>) => {
	chatListViewStore.update((view) => ({ ...view, ...patch }));
	try {
		localStorage.setItem('sidebar-chat-list-view', JSON.stringify(get(chatListViewStore)));
	} catch {
		// Not remembered, but the list still updates.
	}
	return refreshChatList(token);
};

let currentPage = 1;
let paginationReady = false;
let requestGeneration = 0;
export let allLoaded = false;
let loadingNextPage = false;

type RefreshChatListOptions = {
	refreshPinned?: boolean;
	clearPinned?: boolean;
};

type ChatListResult = {
	accepted: boolean;
	allLoaded: boolean;
};

export const refreshChatList = async (
	token: string = '',
	options: RefreshChatListOptions = {}
): Promise<ChatListResult> => {
	const generation = ++requestGeneration;
	paginationReady = false;
	loadingNextPage = false;

	const [nextChats, nextPinnedChats] = await Promise.all([
		getChatList(token, 1, false, false, get(chatListViewStore)) as Promise<ChatListItem[]>,
		options.refreshPinned && !options.clearPinned
			? (getPinnedChatList(token) as Promise<ChatListItem[]>)
			: Promise.resolve(undefined as ChatListItem[] | undefined)
	]);

	if (generation !== requestGeneration) {
		return { accepted: false, allLoaded };
	}

	currentPage = 1;
	allLoaded = nextChats.length === 0;
	chatsStore.set(nextChats);

	if (options.clearPinned) {
		pinnedChatsStore.set([]);
	} else if (options.refreshPinned) {
		pinnedChatsStore.set(nextPinnedChats ?? []);
	}

	paginationReady = true;
	return { accepted: true, allLoaded };
};

// Retained data is updated even when no folder component is mounted.
type FolderRefreshHandler = (folderId?: string | null, chat?: ChatListItem | null) => unknown;
const folderRefreshHandlers = new Set<FolderRefreshHandler>();

export const registerFolderRefreshHandler = (handler: FolderRefreshHandler) => {
	folderRefreshHandlers.add(handler);
	return () => {
		folderRefreshHandlers.delete(handler);
	};
};

export const refreshFolderChatLists = async (
	folderId?: string | null,
	chat?: ChatListItem | null
) => {
	if (folderId !== null) {
		if (folderId && chat) updateFolderChatLists(chat, folderId);
		else markFolderChatsDirty(folderId);
	}
	await Promise.all([...folderRefreshHandlers].map((handler) => handler(folderId, chat)));
};

// Folder lists and open tabs keep their own copy of a chat's title.
export const setChatTitle = (id: string, title: string) => {
	updateFolderChatLists({ id, title });
	renameChatTabs(id, title);
};

export const refreshSidebar = async (token: string = '') => {
	await Promise.all([
		refreshChatList(token, { refreshPinned: true }),
		refreshFolderChatLists(null),
		refreshFolderChatLists()
	]);
};

export const loadNextChatListPage = async (token: string = ''): Promise<ChatListResult> => {
	if (!paginationReady || allLoaded || loadingNextPage) {
		return { accepted: false, allLoaded };
	}

	const generation = requestGeneration;
	const nextPage = currentPage + 1;
	loadingNextPage = true;

	try {
		const nextChats = (await getChatList(
			token,
			nextPage,
			false,
			false,
			get(chatListViewStore)
		)) as ChatListItem[];

		if (generation !== requestGeneration) {
			return { accepted: false, allLoaded };
		}

		allLoaded = nextChats.length === 0;
		currentPage = nextPage;

		const existingIds = new Set((get(chatsStore) ?? []).map((chat) => chat.id));
		const uniqueChats = nextChats.filter((chat) => !existingIds.has(chat.id));
		chatsStore.set([...(get(chatsStore) ?? []), ...uniqueChats]);

		return { accepted: true, allLoaded };
	} finally {
		loadingNextPage = false;
	}
};

export const setChatActive = (
	chatId: string,
	active: boolean,
	pendingApproval = false
): boolean => {
	let found = false;
	const updateChat = (chat: ChatListItem) => {
		if (chat.id !== chatId) {
			return chat;
		}
		found = true;
		return { ...chat, active, pending_approval: pendingApproval };
	};

	chatsStore.update((items) => (items ? items.map(updateChat) : items));
	pinnedChatsStore.update((items) => items.map(updateChat));
	return found;
};

export const setChatReadAt = (chatId: string, lastReadAt: number): boolean => {
	let found = false;
	const updateChat = (chat: ChatListItem) => {
		if (chat.id !== chatId) {
			return chat;
		}
		found = true;
		return { ...chat, last_read_at: lastReadAt };
	};

	chatsStore.update((items) => (items ? items.map(updateChat) : items));
	pinnedChatsStore.update((items) => items.map(updateChat));
	return found;
};

export const setAllChatsRead = () => {
	const updateChat = (chat: ChatListItem) => ({ ...chat, last_read_at: chat.updated_at });

	chatsStore.update((items) => (items ? items.map(updateChat) : items));
	pinnedChatsStore.update((items) => items.map(updateChat));
};

export const resetChatListState = () => {
	requestGeneration += 1;
	currentPage = 1;
	paginationReady = false;
	allLoaded = false;
	loadingNextPage = false;
	chatsStore.set(null);
	pinnedChatsStore.set([]);
};
