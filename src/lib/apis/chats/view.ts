import { WEBUI_API_BASE_URL } from '$lib/constants';
import type { ChatViewState } from '$lib/components/chat/Tabs/tabs';
import { isFolderSessionId } from '$lib/utils/chatId';

export type SavedChatView = { state: ChatViewState | null; revision?: number };
export class ChatViewConflict extends Error {
	constructor(public saved: SavedChatView) {
		super('The layout was changed in another window');
	}
}

async function request(id: string, body?: { state: ChatViewState; revision?: number }) {
	const path = isFolderSessionId(id)
		? `folders/${encodeURIComponent(id.split(':')[1])}`
		: `chats/${encodeURIComponent(id)}`;
	const response = await fetch(`${WEBUI_API_BASE_URL}/${path}/view`, {
		method: body ? 'POST' : 'GET',
		headers: {
			Authorization: `Bearer ${localStorage.token ?? ''}`,
			'Content-Type': 'application/json'
		},
		...(body ? { body: JSON.stringify(body) } : {})
	});
	if (response.status === 409) throw new ChatViewConflict(await response.json());
	if (!response.ok) throw new Error(`Chat view request failed (${response.status})`);
	return response.json();
}

export const getChatView = (id: string): Promise<SavedChatView> => request(id);
export const updateChatView = (
	id: string,
	state: ChatViewState,
	revision: number
): Promise<{ revision?: number }> =>
	request(id, isFolderSessionId(id) ? { state, revision } : { state });
