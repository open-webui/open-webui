import { goto } from '$app/navigation';
import { get } from 'svelte/store';
import { socket, selectedFolder } from '$lib/stores';
import { updateFolderChatLists } from '$lib/stores/folderStates';
import type { AppLayoutContext } from '$lib/types';
import type { WorkspaceChat } from '$lib/utils/folders';

const wantsBrowserTab = (event?: MouseEvent) =>
	!!event && (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0);

function markRead(chat: WorkspaceChat) {
	updateFolderChatLists({ id: chat.id, last_read_at: Date.now() / 1000 });
	get(socket)?.emit('events:chat', { chat_id: chat.id, data: { type: 'last_read_at' } });
}

/**
 * Opens a chat from the folder view in an internal tab beside it, the same way mention
 * links open pages. Modifier clicks keep the browser's new-tab behaviour.
 */
export function openFolderChat(
	chat: WorkspaceChat,
	appLayout: AppLayoutContext | undefined,
	event?: MouseEvent
) {
	markRead(chat);
	const href = `/c/${chat.id}`;
	if (wantsBrowserTab(event)) {
		// A link handles its own modifier click; anywhere else on the row needs a hand.
		if (!(event?.target as Element | null)?.closest('a')) window.open(href, '_blank', 'noopener');
		return;
	}
	event?.preventDefault();
	if (appLayout?.openPageTab) {
		appLayout.openPageTab({ href, label: chat.title });
	} else {
		selectedFolder.set(null);
		void goto(href);
	}
}
