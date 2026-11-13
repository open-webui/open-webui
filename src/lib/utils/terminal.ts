import type { Writable } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { updateChatById } from '$lib/apis/chats';
import { isSavedChatId } from '$lib/utils/chatId';

// Select a chat's terminal at once, saving it to the chat in the background.
export const selectTerminal = (
	selectedTerminalId: Pick<Writable<string | null>, 'set'>,
	id: string | null,
	chatId: string | null
) => {
	selectedTerminalId.set(id);
	if (isSavedChatId(chatId))
		updateChatById(localStorage.token, chatId!, { terminal_id: id, working_directory: '' }).catch(
			(error) => toast.error(String(error))
		);
};
