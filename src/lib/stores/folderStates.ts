import { readonly, writable } from 'svelte/store';
import { getFolderById, getSharedFolderChats } from '$lib/apis/folders';
import { getChatListByFolderId } from '$lib/apis/chats';
import { getModels } from '$lib/apis';
import type { Model } from '$lib/stores';

export type FolderDetails = {
	id: string;
	name: string;
	parent_id?: string | null;
	user_id?: string;
	data?: {
		terminal_id?: string;
		working_directory?: string;
		model_ids?: string[];
		[key: string]: any;
	} | null;
	meta?: Record<string, any> | null;
	write_access?: boolean;
	access_grants?: any[];
	[key: string]: any;
};
export type FolderChat = { id: string; [key: string]: any };
export type FolderChatQuery = {
	page?: number;
	sortBy?: 'title' | 'updated_at' | 'unread_updated_at';
	sortDir?: 'asc' | 'desc';
};
export type FolderChatPage = {
	chats: FolderChat[];
	total: number;
	has_more: boolean;
	folder_permission?: string;
	dirty: boolean;
};
export type FolderState = {
	details: FolderDetails | null;
	chatPages: Record<string, FolderChatPage>;
	sidebarPage: number;
	agentModels: {
		terminalId: string;
		directory: string;
		connectionRevision: number;
		models: Model[];
	} | null;
};

let entries: Record<string, FolderState> = {};
const state = writable(entries);
export const folderStates = readonly(state);
const notify = () => state.set(entries);
let session = 0;
let opening = 0;
const revisions = new Map<string, number>();
const pending = new Map<string, { revision: number; promise: Promise<any> }>();
const resourceKey = (id: string, resource: string) => JSON.stringify([id, resource]);
const revision = (key: string) => revisions.get(key) ?? 0;
const changed = (key: string) => revisions.set(key, revision(key) + 1);

export const folderChatPageKey = (query: FolderChatQuery = {}) =>
	JSON.stringify([query.page ?? 1, query.sortBy ?? 'unread_updated_at', query.sortDir ?? 'desc']);

export function getFolderState(id: string): FolderState {
	return (entries[id] ??= { details: null, chatPages: {}, sidebarPage: 1, agentModels: null });
}

export const beginFolderOpening = () => ++opening;
export const isCurrentFolderOpening = (generation: number) => generation === opening;
export const isCancelledFolderRequest = (error: unknown) =>
	error instanceof Error && error.name === 'AbortError';

// Navigation changes readers, not the lifetime of their successfully loaded data.
async function request<T>(
	id: string,
	resource: string,
	fetch: () => Promise<T>,
	accept: (data: T) => void
) {
	const key = resourceKey(id, resource);
	const version = revision(key);
	const existing = pending.get(key);
	if (existing?.revision === version) return existing.promise as Promise<T>;
	const generation = session;
	const task = { revision: version, promise: null as unknown as Promise<T> };
	task.promise = (async () => {
		try {
			const data = await fetch();
			if (generation !== session || version !== revision(key))
				throw new DOMException('Folder request superseded', 'AbortError');
			if (!data) throw new Error('Could not load folder');
			accept(data);
			notify();
			return data;
		} catch (error) {
			if (generation === session && version === revision(key)) {
				if (
					!resource.startsWith('models:') &&
					[403, 404].includes((error as { status?: number })?.status ?? 0)
				)
					removeFolderState(id);
				if ((error as { status?: number })?.status === 401) clearFolderStates();
			}
			throw error;
		} finally {
			if (pending.get(key) === task) pending.delete(key);
		}
	})();
	pending.set(key, task);
	return task.promise;
}

export function loadFolderDetails(
	token: string,
	id: string,
	refresh = false
): Promise<FolderDetails> {
	const folder = getFolderState(id);
	if (folder.details && !refresh) return Promise.resolve(folder.details);
	return request(
		id,
		'details',
		() => getFolderById(token, id),
		(details) => {
			folder.details = details;
		}
	);
}

export function updateFolderDetails(id: string, details: Partial<FolderDetails>) {
	changed(resourceKey(id, 'details'));
	const folder = getFolderState(id);
	// Mutation responses omit access fields; never turn a partial response into full details.
	if (folder.details) folder.details = { ...folder.details, ...details };
	notify();
}

export function loadFolderChatPage(
	token: string,
	id: string,
	query: FolderChatQuery = {},
	refresh = false
): Promise<FolderChatPage> {
	const folder = getFolderState(id);
	const key = folderChatPageKey(query);
	const page = folder.chatPages[key];
	if (page && !page.dirty && !refresh) return Promise.resolve(page);
	return request(
		id,
		key,
		async () => {
			let result;
			try {
				result = await getSharedFolderChats(token, id, { ...query, page: query.page ?? 1 });
			} catch (error) {
				// Keep the sidebar's legacy fallback, but never use it to bypass access failures.
				if (
					(query.sortBy && query.sortBy !== 'unread_updated_at') ||
					[401, 403, 404].includes((error as any)?.status)
				)
					throw error;
				const chats = await getChatListByFolderId(token, id, query.page ?? 1);
				if (!chats) throw error;
				result = { chats, total: chats.length, has_more: chats.length === 10 };
			}
			if (!result?.chats) throw new Error('Could not load folder chats');
			return {
				...result,
				total: result.total ?? result.chats.length,
				has_more: result.has_more ?? result.chats.length === 10,
				dirty: false
			};
		},
		(result) => {
			folder.chatPages[key] = result;
		}
	);
}

export function setFolderSidebarPage(id: string, page: number) {
	getFolderState(id).sidebarPage = page;
	notify();
}

export function markFolderChatsDirty(id?: string) {
	for (const folderId of id ? [id] : Object.keys(entries)) {
		const folder = entries[folderId];
		if (!folder) continue;
		for (const [key, page] of Object.entries(folder.chatPages)) {
			page.dirty = true;
			changed(resourceKey(folderId, key));
		}
		for (const key of pending.keys()) {
			const [pendingId, resource] = JSON.parse(key);
			if (pendingId === folderId && resource.startsWith('[') && !folder.chatPages[resource])
				changed(key);
		}
	}
	notify();
}

const unread = (chat: FolderChat) =>
	!chat.active && (chat.last_read_at == null || chat.updated_at > chat.last_read_at);
export function sortFolderChats(
	chats: FolderChat[],
	sortBy = 'unread_updated_at',
	sortDir = 'desc'
) {
	return [...chats].sort((a, b) => {
		const order =
			sortBy === 'title'
				? String(a.title ?? '').localeCompare(String(b.title ?? ''))
				: (sortBy === 'unread_updated_at' ? Number(unread(a)) - Number(unread(b)) : 0) ||
					Number(a.updated_at ?? 0) - Number(b.updated_at ?? 0);
		return sortDir === 'asc' ? order : -order;
	});
}

export function updateFolderChatLists(chat: FolderChat, destination?: string | null, remove = false) {
	const { chat: conversation, ...row } = chat;
	chat = row;
	for (const [id, folder] of Object.entries(entries)) {
		const known = Object.values(folder.chatPages).some((page) =>
			page.chats.some((item) => item.id === chat.id)
		);
		const removingFromFolder = remove || (destination !== undefined && destination !== id);
		const countChange =
			removingFromFolder && known
				? -1
				: !removingFromFolder && destination === id && !known
					? 1
					: 0;
		for (const [key, page] of Object.entries(folder.chatPages)) {
			const [number, sortBy, sortDir] = JSON.parse(key);
			page.total = Math.max(0, page.total + countChange);
			page.has_more = page.total > number * 10;
			const existing = page.chats.find((item) => item.id === chat.id);
			const removing = remove || (destination !== undefined && destination !== id);
			if (!existing && (removing || destination !== id || number !== 1)) continue;
			changed(resourceKey(id, key));
			if (removing) {
				page.chats = page.chats.filter((item) => item.id !== chat.id);
			} else {
				page.chats = sortFolderChats(
					[...page.chats.filter((item) => item.id !== chat.id), { ...existing, ...chat }],
					sortBy,
					sortDir
				);
			}
		}
	}
	// Membership and ordering can change page boundaries. Keep rows until reconciliation.
	if (remove || destination !== undefined || chat.title !== undefined) markFolderChatsDirty();
	else notify();
}

export function markFolderRead(id: string, userId: string | undefined) {
	if (!userId) return;
	for (const page of Object.values(entries[id]?.chatPages ?? {})) {
		for (const chat of page.chats) {
			if (!chat.user_id || chat.user_id === userId)
				updateFolderChatLists({ id: chat.id, last_read_at: chat.updated_at });
		}
	}
}

export function removeFolderState(id: string) {
	const descendants = Object.keys(entries).filter(
		(child) => entries[child].details?.parent_id === id
	);
	for (const child of descendants) removeFolderState(child);
	for (const key of new Set([...revisions.keys(), ...pending.keys()])) {
		if (JSON.parse(key)[0] === id) changed(key);
	}
	delete entries[id];
	notify();
}

let connectionRevision = 0;
let connectionsSignature = '';
const agentRequests = new Map<string, Promise<Model[]>>();
export function setFolderModelConnections(configuration: unknown) {
	const signature = JSON.stringify(configuration);
	if (signature !== connectionsSignature) {
		connectionsSignature = signature;
		connectionRevision++;
	}
}

export function getFolderAgentModels(folder: FolderDetails): Model[] | null {
	const loaded = entries[folder.id]?.agentModels;
	return loaded &&
		loaded.terminalId === folder.data?.terminal_id &&
		loaded.directory === (folder.data?.working_directory ?? '') &&
		loaded.connectionRevision === connectionRevision
		? loaded.models
		: null;
}

export async function loadFolderAgentModels(
	token: string,
	folder: FolderDetails,
	connections: any,
	refresh = false
): Promise<Model[]> {
	const loaded = getFolderAgentModels(folder);
	if (loaded && !refresh) return loaded;
	const terminalId = folder.data?.terminal_id;
	if (!terminalId) return [];
	const directory = folder.data?.working_directory ?? '';
	const version = connectionRevision;
	const resource = `models:${JSON.stringify([terminalId, directory, version])}`;
	return request(
		folder.id,
		resource,
		async () => {
			let discovery = agentRequests.get(resource);
			if (!discovery) {
				discovery = getModels(token, connections, false, false, {
					terminalId,
					chatId: null,
					cwd: directory || null
				}).then((models) => models.filter((model: Model) => model.owned_by === 'terminal'));
				agentRequests.set(resource, discovery);
			}
			try {
				return await discovery;
			} finally {
				if (agentRequests.get(resource) === discovery) agentRequests.delete(resource);
			}
		},
		(models) => {
			const current = getFolderState(folder.id);
			const details = current.details;
			if (
				details &&
				(details.data?.terminal_id !== terminalId ||
					(details.data?.working_directory ?? '') !== directory)
			)
				return;
			if (version === connectionRevision)
				current.agentModels = {
					terminalId,
					directory,
					connectionRevision: version,
					models
				};
		}
	);
}

export function clearFolderStates() {
	session++;
	opening++;
	entries = {};
	pending.clear();
	agentRequests.clear();
	revisions.clear();
	connectionsSignature = '';
	connectionRevision++;
	notify();
}
