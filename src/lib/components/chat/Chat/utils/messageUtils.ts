import { v4 as uuidv4 } from 'uuid';
import type { ChatMessage, ChatHistory } from '../types';

export function createMessage(
	role: 'user' | 'assistant' | 'system',
	content: string,
	parentId: string | null = null,
	additionalData: Partial<ChatMessage> = {}
): ChatMessage {
	return {
		id: uuidv4(),
		parentId,
		childrenIds: [],
		role,
		content,
		timestamp: Date.now(),
		...additionalData
	};
}

export function createMessagesList(history: ChatHistory, currentId: string | null): ChatMessage[] {
	if (!currentId || !history.messages[currentId]) return [];
	
	const messages: ChatMessage[] = [];
	let current = history.messages[currentId];
	
	while (current) {
		messages.unshift(current);
		current = current.parentId ? history.messages[current.parentId] : null;
	}
	
	return messages;
}

export function findMessageById(history: ChatHistory, messageId: string): ChatMessage | null {
	return history.messages[messageId] || null;
}

export function getMessageDepth(history: ChatHistory, messageId: string): number {
	let depth = 0;
	let current = history.messages[messageId];
	
	while (current?.parentId) {
		depth++;
		current = history.messages[current.parentId];
	}
	
	return depth;
}

export function getAllDescendants(history: ChatHistory, messageId: string): string[] {
	const descendants: string[] = [];
	const message = history.messages[messageId];
	
	if (!message) return descendants;
	
	const queue = [...message.childrenIds];
	
	while (queue.length > 0) {
		const childId = queue.shift()!;
		descendants.push(childId);
		
		const child = history.messages[childId];
		if (child?.childrenIds) {
			queue.push(...child.childrenIds);
		}
	}
	
	return descendants;
}

export function cloneMessage(message: ChatMessage, newId?: string): ChatMessage {
	return {
		...message,
		id: newId || uuidv4(),
		childrenIds: [],
		timestamp: Date.now()
	};
}

export function pruneHistory(history: ChatHistory, keepMessageId: string): ChatHistory {
	const messagesToKeep = new Set<string>();
	let current = history.messages[keepMessageId];
	
	// Walk up the tree to get all ancestors
	while (current) {
		messagesToKeep.add(current.id);
		current = current.parentId ? history.messages[current.parentId] : null;
	}
	
	// Create new history with only the messages we want to keep
	const prunedMessages: Record<string, ChatMessage> = {};
	
	for (const messageId of messagesToKeep) {
		const message = history.messages[messageId];
		if (message) {
			prunedMessages[messageId] = {
				...message,
				childrenIds: message.childrenIds.filter(id => messagesToKeep.has(id))
			};
		}
	}
	
	return {
		messages: prunedMessages,
		currentId: keepMessageId
	};
}

export function mergeHistories(base: ChatHistory, incoming: ChatHistory): ChatHistory {
	const merged: ChatHistory = {
		messages: { ...base.messages },
		currentId: base.currentId
	};
	
	// Add new messages from incoming
	for (const [id, message] of Object.entries(incoming.messages)) {
		if (!merged.messages[id]) {
			merged.messages[id] = message;
		}
	}
	
	return merged;
}

export function getConversationFromMessage(history: ChatHistory, messageId: string): ChatMessage[] {
	const messages: ChatMessage[] = [];
	let current = history.messages[messageId];
	
	// Walk up to get all messages in the conversation
	while (current) {
		messages.unshift(current);
		current = current.parentId ? history.messages[current.parentId] : null;
	}
	
	return messages;
}

export function formatMessageForAPI(message: ChatMessage): any {
	const formatted: any = {
		role: message.role,
		content: message.content
	};
	
	if (message.files && message.files.length > 0) {
		formatted.images = message.files
			.filter(f => f.type.startsWith('image/'))
			.map(f => f.url)
			.filter(Boolean);
	}
	
	return formatted;
}

export function extractTextFromMessage(message: ChatMessage): string {
	// Extract plain text from message content, removing any special formatting
	return message.content.replace(/<[^>]*>/g, '').trim();
}