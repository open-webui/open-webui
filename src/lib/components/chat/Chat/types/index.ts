import type { Model } from '$lib/stores';

export interface ChatHistory {
	messages: Record<string, ChatMessage>;
	currentId: string | null;
}

export interface ChatMessage {
	id: string;
	parentId: string | null;
	childrenIds: string[];
	role: 'user' | 'assistant' | 'system';
	content: string;
	model?: string;
	timestamp: number;
	done?: boolean;
	error?: boolean;
	files?: ChatFile[];
	citations?: Citation[];
	info?: MessageInfo;
	tools?: ToolCall[];
	artifacts?: Artifact[];
}

export interface ChatFile {
	id: string;
	name: string;
	type: string;
	url?: string;
	collection_name?: string;
	file?: File;
}

export interface Citation {
	id: string;
	source: string;
	metadata?: Record<string, any>;
}

export interface MessageInfo {
	eval_count?: number;
	eval_duration?: number;
	total_duration?: number;
	prompt_eval_count?: number;
	prompt_eval_duration?: number;
}

export interface ToolCall {
	id: string;
	name: string;
	parameters?: Record<string, any>;
	result?: any;
	status?: 'pending' | 'completed' | 'error';
}

export interface Artifact {
	id: string;
	type: string;
	title: string;
	content: string;
}

export interface ChatParams {
	temperature?: number;
	top_p?: number;
	top_k?: number;
	frequency_penalty?: number;
	presence_penalty?: number;
	max_tokens?: number;
	stop?: string[];
	system?: string;
}

export interface ChatState {
	id: string;
	title: string;
	models: string[];
	history: ChatHistory;
	params: ChatParams;
	tags: string[];
	timestamp: number;
	folder_id?: string;
}

export interface ChatEventData {
	type: string;
	data: any;
	modelId?: string;
	chatId?: string;
}

export interface ChatCompletionOptions {
	model: string | Model;
	messages: ChatMessage[];
	stream?: boolean;
	tools?: string[];
	filters?: string[];
	imageGenerationEnabled?: boolean;
	webSearchEnabled?: boolean;
	codeInterpreterEnabled?: boolean;
	params?: ChatParams;
}