const TEMPORARY_CHAT_ID_PREFIX = 'temporary:';
const LEGACY_TEMPORARY_CHAT_ID_PREFIX = 'local:'; // Legacy temporary chat prefix.
const CHANNEL_CHAT_ID_PREFIX = 'channel:';

export const createTemporaryChatId = (sessionId: string | undefined) =>
	`${TEMPORARY_CHAT_ID_PREFIX}${sessionId}`;

export const isTemporaryChatId = (chatId: string | null | undefined) =>
	!!chatId &&
	(chatId.startsWith(TEMPORARY_CHAT_ID_PREFIX) ||
		chatId.startsWith(LEGACY_TEMPORARY_CHAT_ID_PREFIX));

export const isSavedChatId = (chatId: string | null | undefined) =>
	!!chatId && !isTemporaryChatId(chatId) && !chatId.startsWith(CHANNEL_CHAT_ID_PREFIX);
