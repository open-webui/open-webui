import { browser } from '$app/environment';
import { getChatById } from '$lib/apis/chats';
import { getTaskIdsByChatId } from '$lib/apis';

export const load = async ({ params }) => {
	if (browser && localStorage.token) {
		const currentChatId = params.id;

		const [_chat, _taskRes] = await Promise.all([
			getChatById(localStorage.token, currentChatId).catch(() => null),
			getTaskIdsByChatId(localStorage.token, currentChatId).catch(() => null)
		]);

		return {
			chatId: currentChatId,
			chat: _chat,
			taskRes: _taskRes
		};
	}
	return {};
};
