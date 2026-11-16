import { getContext, setContext } from 'svelte';
import { chatId, models, temporaryChat, audioQueue } from '$lib/stores';
import type { ChatContext } from '$lib/types';

export const setChatContext = (context: ChatContext) => setContext('chat', context);

/** The enclosing chat's state, or the main chat's stores outside any chat. */
export const getChatContext = (): ChatContext =>
	getContext<ChatContext | undefined>('chat') ?? {
		chatId,
		models,
		temporary: temporaryChat,
		audioQueue
	};
