import { writable, derived, get } from 'svelte/store';
import type { ChatHistory, ChatMessage, ChatParams, ChatFile } from '../types';
import type { Model } from '$lib/stores';

// Core chat state
export const chatHistory = writable<ChatHistory>({
	messages: {},
	currentId: null
});

export const selectedModels = writable<string[]>(['']);
export const atSelectedModel = writable<Model | undefined>(undefined);
export const selectedToolIds = writable<string[]>([]);
export const selectedFilterIds = writable<string[]>([]);

// Feature toggles
export const imageGenerationEnabled = writable(false);
export const webSearchEnabled = writable(false);
export const codeInterpreterEnabled = writable(false);

// Chat metadata
export const chatMetadata = writable({
	id: '',
	title: '',
	tags: [] as string[],
	timestamp: Date.now()
});

// UI state
export const processing = writable('');
export const autoScroll = writable(true);
export const showCommands = writable(false);

// Input state
export const prompt = writable('');
export const files = writable<ChatFile[]>([]);
export const chatParams = writable<ChatParams>({});

// Task management
export const taskIds = writable<string[] | null>(null);

// Derived stores
export const selectedModelIds = derived(
	[atSelectedModel, selectedModels],
	([$atSelectedModel, $selectedModels]) => 
		$atSelectedModel !== undefined ? [$atSelectedModel.id] : $selectedModels
);

export const messagesList = derived(chatHistory, ($history) => {
	const createList = (history: ChatHistory, currentId: string | null): ChatMessage[] => {
		if (!currentId) return [];
		
		const messages: ChatMessage[] = [];
		let current = history.messages[currentId];
		
		while (current) {
			messages.unshift(current);
			current = current.parentId ? history.messages[current.parentId] : null;
		}
		
		return messages;
	};
	
	return createList($history, $history.currentId);
});

// Store actions
export const chatStore = {
	// Reset chat state
	reset() {
		chatHistory.set({ messages: {}, currentId: null });
		selectedModels.set(['']);
		atSelectedModel.set(undefined);
		selectedToolIds.set([]);
		selectedFilterIds.set([]);
		imageGenerationEnabled.set(false);
		webSearchEnabled.set(false);
		codeInterpreterEnabled.set(false);
		prompt.set('');
		files.set([]);
		chatParams.set({});
		taskIds.set(null);
	},
	
	// Add a message to the history
	addMessage(message: ChatMessage) {
		chatHistory.update(history => {
			history.messages[message.id] = message;
			
			// Update parent's children
			if (message.parentId && history.messages[message.parentId]) {
				const parent = history.messages[message.parentId];
				if (!parent.childrenIds.includes(message.id)) {
					parent.childrenIds.push(message.id);
				}
			}
			
			// Update current ID if this is the latest message
			if (!message.parentId || message.parentId === history.currentId) {
				history.currentId = message.id;
			}
			
			return history;
		});
	},
	
	// Update an existing message
	updateMessage(messageId: string, updates: Partial<ChatMessage>) {
		chatHistory.update(history => {
			if (history.messages[messageId]) {
				history.messages[messageId] = {
					...history.messages[messageId],
					...updates
				};
			}
			return history;
		});
	},
	
	// Set current message ID
	setCurrentId(messageId: string) {
		chatHistory.update(history => {
			history.currentId = messageId;
			return history;
		});
	},
	
	// Load chat history
	loadHistory(newHistory: ChatHistory) {
		chatHistory.set(newHistory);
	}
};