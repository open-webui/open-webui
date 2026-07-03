import { getOutputText, type OutputItem } from './Messages/structuredOutput';

type ChatHistoryMessage = {
	id?: string;
	role?: string;
	content?: string;
	info?: unknown;
	timestamp?: number;
	sources?: unknown;
	output?: OutputItem[];
};

export const toChatActionMessage = (message: ChatHistoryMessage) => {
	const outputContent =
		message.role === 'assistant' && message.output?.length ? getOutputText(message.output) : '';

	return {
		id: message.id,
		role: message.role,
		content: outputContent || message.content || '',
		info: message.info ? message.info : undefined,
		timestamp: message.timestamp,
		...(message.role === 'assistant' && message.output?.length ? { output: message.output } : {}),
		...(message.sources ? { sources: message.sources } : {})
	};
};
