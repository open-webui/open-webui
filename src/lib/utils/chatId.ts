const TEMPORARY_CHAT_ID_PREFIX = 'temporary:';
const LEGACY_TEMPORARY_CHAT_ID_PREFIX = 'local:'; // Legacy temporary chat prefix.

export const createTemporaryChatId = (sessionId: string | undefined) =>
	`${TEMPORARY_CHAT_ID_PREFIX}${sessionId}`;

export const isTemporaryChatId = (chatId: string | null | undefined) =>
	!!chatId &&
	(chatId.startsWith(TEMPORARY_CHAT_ID_PREFIX) ||
		chatId.startsWith(LEGACY_TEMPORARY_CHAT_ID_PREFIX));
