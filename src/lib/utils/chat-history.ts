type ChatMessageLike = {
	id?: string;
	parentId?: string | null;
	childrenIds?: string[];
	[key: string]: unknown;
};

type ChatHistoryLike = {
	currentId?: string | null;
	messages: Record<string, ChatMessageLike>;
};

export const deepestDescendantId = (
	messages: Record<string, ChatMessageLike>,
	startId: string | null | undefined
): string | null => {
	if (!startId) return null;

	const visited = new Set<string>();
	let messageId = startId;

	while (messageId) {
		visited.add(messageId);
		const children = messages[messageId]?.childrenIds ?? [];
		if (children.length === 0) return messageId;

		const nextId = children.at(-1);
		if (!nextId || !messages[nextId] || visited.has(nextId)) return messageId;
		messageId = nextId;
	}

	return messageId;
};

export const restoreStoppedResponse = (
	history: ChatHistoryLike,
	responseMessage: ChatMessageLike | null | undefined
): ChatHistoryLike => {
	if (!responseMessage?.id) return history;
	history.messages[responseMessage.id] = responseMessage;
	return history;
};

export const shouldProcessQueueAfterTaskCancel = ({
	cancelMessageId,
	currentId,
	skipQueueOnTaskCancel
}: {
	cancelMessageId?: string | null;
	currentId?: string | null;
	skipQueueOnTaskCancel: boolean;
}): boolean => {
	return Boolean(
		!skipQueueOnTaskCancel && cancelMessageId && currentId && cancelMessageId === currentId
	);
};

export const isDescendantMessage = (
	messages: Record<string, ChatMessageLike>,
	nodeId: string,
	currentId: string,
	visited = new Set<string>()
): boolean => {
	if (!nodeId || visited.has(nodeId)) return false;
	visited.add(nodeId);

	const node = messages[nodeId];
	return Boolean(
		node?.childrenIds?.some(
			(id) => id === currentId || isDescendantMessage(messages, id, currentId, visited)
		)
	);
};
