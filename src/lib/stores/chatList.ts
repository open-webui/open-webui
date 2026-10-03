import { get, readonly, writable } from 'svelte/store';
import { getChatList, getPinnedChatList } from '$lib/apis/chats';

type ChatListItem = {
	id: string;
	[key: string]: unknown;
};

const chatsStore = writable<ChatListItem[] | null>(null);
const pinnedChatsStore = writable<ChatListItem[]>([]);
const allChatsLoadedStore = writable(false);

export const chats = readonly(chatsStore);
export const pinnedChats = readonly(pinnedChatsStore);
export const allChatsLoaded = readonly(allChatsLoadedStore);

let currentPage = 1;
let paginationReady = false;
let requestGeneration = 0;
let loadingNextPage = false;

type RefreshChatListOptions = {
	refreshPinned?: boolean;
	clearPinned?: boolean;
};

type ChatListResult = {
	accepted: boolean;
};

export const refreshChatList = async (
	token: string = '',
	options: RefreshChatListOptions = {}
): Promise<ChatListResult> => {
	const generation = ++requestGeneration;
	paginationReady = false;
	loadingNextPage = false;

	const [nextChats, nextPinnedChats] = await Promise.all([
		getChatList(token, 1) as Promise<ChatListItem[]>,
		options.refreshPinned && !options.clearPinned
			? (getPinnedChatList(token) as Promise<ChatListItem[]>)
			: Promise.resolve(undefined as ChatListItem[] | undefined)
	]);

	if (generation !== requestGeneration) {
		return { accepted: false };
	}

	chatsStore.set(nextChats);
	currentPage = 1;
	allChatsLoadedStore.set(nextChats.length === 0);

	if (options.clearPinned) {
		pinnedChatsStore.set([]);
	} else if (options.refreshPinned) {
		pinnedChatsStore.set(nextPinnedChats ?? []);
	}

	paginationReady = true;
	return { accepted: true };
};

// The sidebar owns folder state. This bridge lets other components refresh it.
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
	await Promise.all([...folderRefreshHandlers].map((handler) => handler(folderId, chat)));
};

export const refreshSidebar = async (token: string = '') => {
	await Promise.all([
		refreshChatList(token, { refreshPinned: true }),
		refreshFolderChatLists(null),
		refreshFolderChatLists()
	]);
};

export const loadNextChatListPage = async (token: string = ''): Promise<ChatListResult> => {
	if (!paginationReady || get(allChatsLoadedStore) || loadingNextPage) {
		return { accepted: false };
	}

	const generation = requestGeneration;
	const nextPage = currentPage + 1;
	loadingNextPage = true;

	try {
		const nextChats = (await getChatList(token, nextPage)) as ChatListItem[];

		if (generation !== requestGeneration) {
			return { accepted: false };
		}

		allChatsLoadedStore.set(nextChats.length === 0);
		currentPage = nextPage;

		const existingIds = new Set((get(chatsStore) ?? []).map((chat) => chat.id));
		const uniqueChats = nextChats.filter((chat) => !existingIds.has(chat.id));
		chatsStore.set([...(get(chatsStore) ?? []), ...uniqueChats]);

		return { accepted: true };
	} finally {
		loadingNextPage = false;
	}
};

export const setChatActive = (chatId: string, active: boolean): boolean => {
	let found = false;
	const updateChat = (chat: ChatListItem) => {
		if (chat.id !== chatId) {
			return chat;
		}
		found = true;
		return { ...chat, active };
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
	allChatsLoadedStore.set(false);
	loadingNextPage = false;
	chatsStore.set(null);
	pinnedChatsStore.set([]);
};
