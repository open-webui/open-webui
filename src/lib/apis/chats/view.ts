import { WEBUI_API_BASE_URL } from '$lib/constants';
import type { ChatViewState } from '$lib/components/chat/ChatTabs/tabs';

async function request(id: string, state?: ChatViewState) {
	const response = await fetch(`${WEBUI_API_BASE_URL}/chats/${encodeURIComponent(id)}/view`, {
		method: state ? 'POST' : 'GET',
		headers: {
			Authorization: `Bearer ${localStorage.token ?? ''}`,
			'Content-Type': 'application/json'
		},
		...(state ? { body: JSON.stringify({ state }) } : {})
	});
	if (!response.ok) throw new Error(`Chat view request failed (${response.status})`);
	return response.json();
}

export const getChatView = (id: string): Promise<{ state: ChatViewState | null }> => request(id);
export const updateChatView = (id: string, state: ChatViewState): Promise<{ updated_at: number }> =>
	request(id, state);
