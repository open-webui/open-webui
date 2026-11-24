import { get } from 'svelte/store';
import { user } from '$lib/stores';

const MAX_CACHED_CHATS = 20;

/** The user's own chats opened before, oldest first; each shows at once when opened again. */
export const cachedChats = new Map<string, any>();

export const cacheChat = (chat: any) => {
	cachedChats.delete(chat.id);
	if (chat.user_id !== get(user)?.id) return;
	cachedChats.set(chat.id, chat);
	if (cachedChats.size > MAX_CACHED_CHATS) cachedChats.delete(cachedChats.keys().next().value!);
};

export const getCachedChat = (id: string) => {
	const chat = cachedChats.get(id);
	const history = chat?.chat?.history;
	const messages: any[] = Object.values(history?.messages ?? {});
	const current = history?.messages?.[chat.current_message_id ?? history?.currentId];
	// A reply that was still running continues from the server's copy.
	const replying =
		messages.some((message) => message.role === 'assistant' && message.done === false) ||
		(current?.role === 'assistant' && !current.done);
	return replying ? undefined : chat;
};
