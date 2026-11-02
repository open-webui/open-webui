import { v4 as uuidv4 } from 'uuid';

const TEMPORARY_CHAT_ID_PREFIX = 'temporary:';
const LEGACY_TEMPORARY_CHAT_ID_PREFIX = 'local:'; // Legacy temporary chat prefix.
const CHANNEL_CHAT_ID_PREFIX = 'channel:';

export const createTemporaryChatId = (sessionId: string | undefined) => {
	if (!sessionId) throw new Error('Connect before starting a temporary chat');
	return `${TEMPORARY_CHAT_ID_PREFIX}${sessionId}:${uuidv4()}`;
};

export const isTemporaryChatId = (chatId: string | null | undefined) =>
	!!chatId &&
	(chatId.startsWith(TEMPORARY_CHAT_ID_PREFIX) ||
		chatId.startsWith(LEGACY_TEMPORARY_CHAT_ID_PREFIX));

export const isSavedChatId = (chatId: string | null | undefined) =>
	!!chatId && !isTemporaryChatId(chatId) && !chatId.startsWith(CHANNEL_CHAT_ID_PREFIX);
