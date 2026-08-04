export type ChatQueueRequest = {
	id: string;
	prompt: string;
	files: any[];
};

export type ChatRequestQueues = Record<string, ChatQueueRequest[]>;

export const dequeueChatRequest = (
	queues: ChatRequestQueues,
	chatId: string
): { queues: ChatRequestQueues; request: ChatQueueRequest | null } => {
	const [request, ...remainingQueue] = queues[chatId] ?? [];

	if (!request) {
		return { queues, request: null };
	}

	if (remainingQueue.length > 0) {
		return {
			queues: { ...queues, [chatId]: remainingQueue },
			request
		};
	}

	const { [chatId]: _, ...remainingQueues } = queues;
	return { queues: remainingQueues, request };
};
