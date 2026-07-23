import equal from 'fast-deep-equal';

export type ChatHistoryMessage = {
	id?: string;
	[key: string]: unknown;
};

export type ChatHistoryMessageMap = Record<string, ChatHistoryMessage>;

export type ChatMessageWindowState = {
	loadedIds?: string[];
	[key: string]: unknown;
};

export type WindowedChatHistory = {
	currentId?: string | null;
	messages?: ChatHistoryMessageMap;
	messageWindow?: ChatMessageWindowState;
	[key: string]: unknown;
};

export type ChatHistoryWindowResponse = {
	messages: ChatHistoryMessageMap | ChatHistoryMessage[];
	loadedIds: string[];
	hasMore: boolean;
	currentId: string | null;
};

export const DEFAULT_CHAT_MESSAGE_WINDOW = 32;

type WindowedChat = {
	history?: WindowedChatHistory;
	[key: string]: unknown;
};

const uniqueIds = (ids: unknown[]): string[] => [
	...new Set(ids.filter((id): id is string => typeof id === 'string'))
];

const normalizeMessages = (
	messages: ChatHistoryWindowResponse['messages']
): ChatHistoryMessageMap => {
	if (Array.isArray(messages)) {
		return Object.fromEntries(
			messages
				.filter((message): message is ChatHistoryMessage & { id: string } => {
					return typeof message?.id === 'string';
				})
				.map((message) => [message.id, message])
		);
	}

	return messages ?? {};
};

export const getLoadedMessageIds = (history?: WindowedChatHistory | null): string[] => {
	if (Array.isArray(history?.messageWindow?.loadedIds)) {
		return uniqueIds(history.messageWindow.loadedIds);
	}

	return Object.keys(history?.messages ?? {});
};

export const isChatMessageLoaded = (
	history: WindowedChatHistory | null | undefined,
	messageId: string
): boolean => {
	const message = history?.messages?.[messageId];
	return message !== undefined && message.__loaded !== false;
};

export const resolveLoadedCurrentMessageId = (
	history: WindowedChatHistory | null | undefined,
	persistedCurrentId?: string | null
): string | null => {
	const windowCurrentId = history?.currentId;
	if (windowCurrentId && isChatMessageLoaded(history, windowCurrentId)) {
		return windowCurrentId;
	}

	if (persistedCurrentId && isChatMessageLoaded(history, persistedCurrentId)) {
		return persistedCurrentId;
	}

	return windowCurrentId ?? persistedCurrentId ?? null;
};

export const mergeChatMessageEvent = (
	message: ChatHistoryMessage,
	data: unknown,
	replace = false
): ChatHistoryMessage => {
	const eventData =
		data !== null && typeof data === 'object' && !Array.isArray(data)
			? (data as ChatHistoryMessage)
			: {};
	const patch = { ...eventData };
	delete patch.chat_id;
	delete patch.message_id;

	if (replace) {
		return {
			...message,
			...patch,
			content: patch.content
		};
	}

	return {
		...message,
		...patch
	};
};

export const groupMessageIdsByModel = (
	parentMessage: ChatHistoryMessage | null | undefined,
	messages: ChatHistoryMessageMap
): Record<number, { messageIds: string[] }> => {
	const modelIds = Array.isArray(parentMessage?.models)
		? parentMessage.models.filter((modelId): modelId is string => typeof modelId === 'string')
		: [];
	const groups = Object.fromEntries(
		modelIds.map((_, modelIdx) => [modelIdx, { messageIds: [] as string[] }])
	) as Record<number, { messageIds: string[] }>;

	if (modelIds.length === 0) return groups;

	const childIds = Array.isArray(parentMessage?.childrenIds)
		? parentMessage.childrenIds.filter(
				(messageId): messageId is string => typeof messageId === 'string'
			)
		: [];

	for (const [childIndex, messageId] of childIds.entries()) {
		const message = messages[messageId];
		const declaredModelIdx = Number(message?.modelIdx);
		let modelIdx =
			Number.isInteger(declaredModelIdx) &&
			declaredModelIdx >= 0 &&
			declaredModelIdx < modelIds.length
				? declaredModelIdx
				: -1;

		if (modelIdx === -1 && typeof message?.model === 'string') {
			const matchingModelIndexes = modelIds
				.map((modelId, index) => (modelId === message.model ? index : -1))
				.filter((index) => index !== -1);

			if (matchingModelIndexes.length > 0) {
				modelIdx = matchingModelIndexes.reduce((leastUsedIndex, candidateIndex) =>
					groups[candidateIndex].messageIds.length < groups[leastUsedIndex].messageIds.length
						? candidateIndex
						: leastUsedIndex
				);
			}
		}

		// Topology stubs intentionally omit model data. Child order follows the
		// original multi-model request order, so keep every stub navigable until hydrated.
		if (modelIdx === -1) modelIdx = childIndex % modelIds.length;
		groups[modelIdx].messageIds.push(messageId);
	}

	return groups;
};

export const mergeChatHistoryWindow = (
	history: WindowedChatHistory,
	window: ChatHistoryWindowResponse
): WindowedChatHistory => {
	const incomingMessages = normalizeMessages(window.messages);
	const messages: ChatHistoryMessageMap = Object.fromEntries(
		Object.entries(history.messages ?? {}).map(([id, message]) => [id, { ...message }])
	);

	for (const [id, message] of Object.entries(incomingMessages)) {
		messages[id] = {
			...(messages[id] ?? {}),
			...message,
			id,
			__loaded: true
		};
	}

	const loadedIds = uniqueIds([
		...getLoadedMessageIds(history),
		...window.loadedIds,
		...Object.keys(incomingMessages)
	]);

	return {
		...history,
		currentId: window.currentId,
		messages,
		messageWindow: {
			...(history.messageWindow ?? {}),
			loadedIds,
			hasMore: window.hasMore,
			currentId: window.currentId
		}
	};
};

export const serializeChatForWindowSave = <T extends WindowedChat>(chat: T): T => {
	if (!chat.history) {
		return { ...chat };
	}

	const loadedIds = getLoadedMessageIds(chat.history);
	const messageEntries = Object.entries(chat.history.messages ?? {});
	const messageIdsToSerialize = new Set([
		...loadedIds,
		...messageEntries
			.filter(([, message]) => message.__loaded !== false)
			.map(([messageId]) => messageId)
	]);
	const messages = Object.fromEntries(
		messageEntries
			.filter(([id, message]) => messageIdsToSerialize.has(id) && message.__loaded !== false)
			.map(([id, message]) => {
				const messageCopy = { ...message };
				delete messageCopy.__loaded;
				return [id, messageCopy];
			})
	);

	return {
		...chat,
		history: {
			...chat.history,
			currentId: chat.history.currentId,
			messages,
			...(chat.history.messageWindow
				? {
						messageWindow: {
							...chat.history.messageWindow,
							loadedIds
						}
					}
				: {})
		}
	} as T;
};

export const serializeMessageForPatch = (message: ChatHistoryMessage): ChatHistoryMessage => {
	const messageCopy = { ...message };
	delete messageCopy.__loaded;
	delete messageCopy.childrenIds;
	delete messageCopy.id;
	delete messageCopy.parentId;
	delete messageCopy.role;
	delete messageCopy.timestamp;
	return messageCopy;
};

export const createMessagePatch = (
	previousMessage: ChatHistoryMessage,
	nextMessage: ChatHistoryMessage
): ChatHistoryMessage => {
	const previous = serializeMessageForPatch(previousMessage);
	const next = serializeMessageForPatch(nextMessage);
	const patch: ChatHistoryMessage = {};

	for (const [key, value] of Object.entries(next)) {
		if (!equal(previous[key], value)) {
			patch[key] = value === undefined ? null : value;
		}
	}

	for (const key of Object.keys(previous)) {
		if (!(key in next)) {
			patch[key] = null;
		}
	}

	return patch;
};
