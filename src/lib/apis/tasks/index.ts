import { WEBUI_API_BASE_URL } from '$lib/constants';

export const checkActiveChats = async (token: string, chatIds: string[]) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/tasks/active/chats`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ chat_ids: chatIds })
	});
	if (!res.ok) throw await res.json();
	return res.json();
};
