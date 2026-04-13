import { browser } from '$app/environment';
import { getChatById } from '$lib/apis/chats';
import { getTaskIdsByChatId } from '$lib/apis';

export const load = ({ params }) => {
	if (browser && localStorage.token) {
		const currentChatId = params.id;

		return {
			chatId: currentChatId,
			chatPromise: getChatById(localStorage.token, currentChatId).catch(() => null),
			taskResPromise: getTaskIdsByChatId(localStorage.token, currentChatId).catch(() => null)
		};
	}
	return {};
};
