export type Banner = {
	id: string;
	type: string;
	title?: string;
	content: string;
	url?: string;
	dismissible?: boolean;
	timestamp: number;
};

export enum TTS_RESPONSE_SPLIT {
	PUNCTUATION = 'punctuation',
	PARAGRAPHS = 'paragraphs',
	NONE = 'none'
}

export interface Message {
	id: string;
	role: 'user' | 'assistant' | 'system';
	content: string;
	model: string;
	chatCompletionId?: string;
	done: boolean;
	timestamp?: number;
}
