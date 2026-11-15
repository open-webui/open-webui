import { browser } from '$app/environment';
import { v4 as uuidv4 } from 'uuid';
import { writable } from 'svelte/store';
import { getChatView, updateChatView } from '$lib/apis/chats/view';
import { terminalRequest, type TerminalConnection } from '$lib/apis/terminal';
import { createBrowserSession } from '$lib/apis/terminal/browser';
import { isSavedChatId } from '$lib/utils/chatId';
import {
	emptyTabs,
	removeTab,
	type ChatViewState,
	type PanelTab
} from '$lib/components/chat/ChatTabs/tabs';

export type EditorDraft = {
	baseText: string;
	editorJSON?: any;
	text: string;
	scrollTop: number;
	scrollLeft: number;
	dirty: boolean;
};

type Entry = {
	instanceId: string;
	userId: string;
	chatId: string | null;
	state: ChatViewState;
	drafts: Map<string, any>;
	transient: Record<string, any>;
	pending: Map<string, Promise<void>>;
	revision: number;
	persistedRevision: number;
	loaded: boolean;
	persistent: boolean;
	promoting: boolean;
	error: string;
	sessionErrors: Record<string, string>;
	timer?: ReturnType<typeof setTimeout>;
	write?: Promise<void>;
	load?: Promise<void>;
};

const entries = new Map<string, Entry>();
const key = (userId: string, chatId: string) => JSON.stringify([userId, chatId]);
export const chatViewChanges = writable(0);
const notify = () => chatViewChanges.update((n) => n + 1);
let captureActive: (() => void) | undefined;

export function serializeChatView(state: ChatViewState): ChatViewState {
	let panels = state.panels;
	for (const tab of panels.tabs) {
		if (
			tab.untitled ||
			['voice', 'artifacts', 'preview'].includes(tab.kind) ||
			(tab.kind === 'side' && !isSavedChatId(tab.chatId))
		)
			panels = removeTab(panels, tab.id);
	}
	return {
		schemaVersion: 1,
		selectedTerminalId: state.selectedTerminalId,
		panels: {
			...panels,
			tabs: panels.tabs.map((tab) => ({
				id: tab.id,
				kind: tab.kind,
				label: tab.label,
				terminalId: tab.terminalId,
				terminalNumber: tab.terminalNumber,
				chatId: tab.chatId,
				sideChatNumber: tab.sideChatNumber,
				path: tab.path,
				page: tab.page,
				sessionId: tab.sessionId,
				directory: tab.directory
			}))
		}
	};
}

export function chatViewEntry(userId: string, chatId: string | null, temporary = false): Entry {
	if (!browser) throw new Error('Chat views are browser-local');
	const existing = chatId && entries.get(key(userId, chatId));
	if (existing) return existing;
	const entry: Entry = {
		instanceId: uuidv4(),
		userId,
		chatId,
		state: { schemaVersion: 1, selectedTerminalId: null, panels: emptyTabs() },
		drafts: new Map(),
		transient: {},
		pending: new Map(),
		revision: 0,
		persistedRevision: 0,
		loaded: !isSavedChatId(chatId) || temporary,
		persistent: isSavedChatId(chatId) && !temporary,
		promoting: false,
		error: '',
		sessionErrors: {}
	};
	entries.set(key(userId, chatId || entry.instanceId), entry);
	return entry;
}

export async function loadChatView(entry: Entry) {
	if (!entry.persistent) return;
	if (entry.load) return entry.load;
	entry.load = (async () => {
		try {
			// Revalidate access even when the view is already cached. Never replace local edits.
			const result = await getChatView(entry.chatId!);
			if (result.state && result.state.schemaVersion !== 1)
				throw new Error('Unsupported chat view version');
			if (!entry.loaded && result.state) entry.state = result.state;
			entry.loaded = true;
			entry.error = '';
		} catch (error) {
			entry.error = String(error);
			throw error;
		} finally {
			entry.load = undefined;
			notify();
		}
	})();
	return entry.load;
}

export function changeChatView(entry: Entry, state = entry.state, immediate = false) {
	entry.state = state;
	entry.revision++;
	clearTimeout(entry.timer);
	if (entry.loaded && entry.persistent && !entry.promoting)
		entry.timer = setTimeout(() => void flushChatView(entry), immediate ? 0 : 300);
	notify();
}

export async function flushChatView(entry: Entry): Promise<void> {
	clearTimeout(entry.timer);
	if (!entry.loaded || !entry.persistent || entry.promoting) return;
	if (entry.write) return entry.write;
	if (entry.persistedRevision >= entry.revision) return;
	entry.write = (async () => {
		try {
			while (
				entry.persistedRevision < entry.revision &&
				entries.has(key(entry.userId, entry.chatId!))
			) {
				const revision = entry.revision;
				const snapshot = structuredClone(serializeChatView(entry.state));
				await updateChatView(entry.chatId!, snapshot);
				entry.persistedRevision = revision;
				entry.error = '';
			}
		} catch (error) {
			entry.error = `Layout changes not saved. ${String(error)}`;
		} finally {
			entry.write = undefined;
			notify();
		}
	})();
	return entry.write;
}

export function updateViewTab(entry: Entry, id: string, values: Partial<PanelTab>) {
	if (!entry.state.panels.tabs.some((tab) => tab.id === id)) return;
	changeChatView(
		entry,
		{
			...entry.state,
			panels: {
				...entry.state.panels,
				tabs: entry.state.panels.tabs.map((tab) => (tab.id === id ? { ...tab, ...values } : tab))
			}
		},
		true
	);
}

export function createViewSession(entry: Entry, id: string, connection: TerminalConnection) {
	const pending = entry.pending.get(id);
	if (pending) return pending;
	const tab = entry.state.panels.tabs.find((tab) => tab.id === id);
	if (!tab) return Promise.resolve();
	delete entry.sessionErrors[id];
	const request = (async () => {
		try {
			const session =
				tab.kind === 'browser'
					? await createBrowserSession(connection, entry.chatId, tab.path ?? '')
					: await terminalRequest<{ id: string }>(connection, entry.chatId, '/api/terminals', {
							method: 'POST'
						});
			updateViewTab(entry, id, { sessionId: session.id });
		} catch (error) {
			entry.sessionErrors[id] = String(error);
		} finally {
			entry.pending.delete(id);
			notify();
		}
	})();
	entry.pending.set(id, request);
	notify();
	return request;
}

export async function promoteChatView(
	entry: Entry,
	chatId: string,
	bind: () => Promise<void>,
	temporary = false
) {
	entry.promoting = true;
	await Promise.all(entry.pending.values());
	try {
		await bind();
		entries.delete(key(entry.userId, entry.chatId || entry.instanceId));
		entry.chatId = chatId;
		entry.persistent = isSavedChatId(chatId) && !temporary;
		entries.set(key(entry.userId, chatId), entry);
		entry.error = '';
		entry.promoting = false;
		changeChatView(entry, entry.state, true);
	} catch (error) {
		entry.error = `Could not attach sessions to this chat. ${String(error)}`;
		notify();
		throw error;
	}
}

export function registerChatViewCapture(capture: () => void) {
	captureActive = capture;
	return () => {
		if (captureActive === capture) captureActive = undefined;
	};
}

export function hasChatViewDrafts() {
	captureActive?.();
	return [...entries.values()].some((entry) =>
		[...entry.drafts.values()].some((draft) => draft?.dirty)
	);
}

export function clearChatViews() {
	for (const entry of entries.values()) clearTimeout(entry.timer);
	entries.clear();
	captureActive = undefined;
	notify();
}

if (browser) {
	window.addEventListener('online', () => {
		for (const entry of entries.values()) void flushChatView(entry);
	});
	window.addEventListener('beforeunload', (event) => {
		if (hasChatViewDrafts()) {
			event.preventDefault();
			event.returnValue = '';
		}
	});
}
