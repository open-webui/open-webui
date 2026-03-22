import { browser } from '$app/environment';
import { getChatById, getTagsById } from '$lib/apis/chats';
import { getTaskIdsByChatId } from '$lib/apis';
import { getUserSettings } from '$lib/apis/users';

export const load = async ({ params }) => {
	if (browser && localStorage.token) {
		const currentChatId = params.id;

		const [_chat, _tags, _userSettings, _taskRes] = await Promise.all([
			getChatById(localStorage.token, currentChatId).catch(() => null),
			getTagsById(localStorage.token, currentChatId).catch(() => []),
			getUserSettings(localStorage.token).catch(() => null),
			getTaskIdsByChatId(localStorage.token, currentChatId).catch(() => null)
		]);

		return {
			chatId: currentChatId,
			chat: _chat,
			tags: _tags,
			userSettings: _userSettings,
			taskRes: _taskRes
		};
	}
	return {};
};
