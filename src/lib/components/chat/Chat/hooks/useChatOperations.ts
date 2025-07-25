import { v4 as uuidv4 } from 'uuid';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';
import { goto } from '$app/navigation';

import type { ChatMessage, ChatHistory, ChatCompletionOptions } from '../types';
import { ChatService } from '../services/chatService';
import { chatStore, chatHistory, selectedModels, chatMetadata } from '../stores/chatStore';
import { createMessage, formatMessageForAPI } from '../utils/messageUtils';
import { user, settings, models as modelsStore } from '$lib/stores';
import { queryMemory } from '$lib/apis/memories';
import { processWebSearch } from '$lib/apis/retrieval';

export function useChatOperations() {
	const chatService = new ChatService();
	let abortController: AbortController | null = null;
	
	// Initialize a new chat
	const initNewChat = async () => {
		chatStore.reset();
		
		const chatId = uuidv4();
		const chat = {
			id: chatId,
			title: 'New Chat',
			models: get(selectedModels),
			system: get(settings).system ?? undefined,
			params: {},
			history: {
				messages: {},
				currentId: null
			},
			tags: [],
			timestamp: Date.now()
		};
		
		await chatService.createChat(chat);
		await goto(`/c/${chatId}`);
		
		return chatId;
	};
	
	// Load an existing chat
	const loadChat = async (chatId: string): Promise<boolean> => {
		try {
			const chat = await chatService.loadChat(chatId);
			if (!chat) return false;
			
			// Load chat data into stores
			chatHistory.set(chat.chat.history);
			selectedModels.set(chat.chat.models || ['']);
			chatMetadata.set({
				id: chat.id,
				title: chat.chat.title || 'Untitled',
				tags: chat.chat.tags || [],
				timestamp: chat.chat.timestamp || Date.now()
			});
			
			// Load task IDs if any
			const taskIds = await chatService.getTaskIds(chatId);
			if (taskIds) {
				chatStore.taskIds.set(taskIds);
			}
			
			return true;
		} catch (error) {
			console.error('Failed to load chat:', error);
			toast.error('Failed to load chat');
			return false;
		}
	};
	
	// Create a message pair (user + assistant placeholder)
	const createMessagePair = async (userPrompt: string, files: any[] = []) => {
		const history = get(chatHistory);
		
		// Create user message
		const userMessage = createMessage('user', userPrompt, history.currentId, {
			files: files.length > 0 ? files : undefined
		});
		
		// Create assistant placeholder
		const assistantMessage = createMessage('assistant', '', userMessage.id, {
			model: get(selectedModels)[0],
			timestamp: Date.now()
		});
		
		// Add messages to history
		chatStore.addMessage(userMessage);
		chatStore.addMessage(assistantMessage);
		
		return {
			userMessage,
			assistantMessage
		};
	};
	
	// Send a prompt and get response
	const sendPrompt = async (
		prompt: string,
		options: {
			model?: string;
			parentId?: string;
			files?: any[];
			webSearchEnabled?: boolean;
			imageGenerationEnabled?: boolean;
			tools?: string[];
			params?: any;
		} = {}
	) => {
		try {
			const { userMessage, assistantMessage } = await createMessagePair(prompt, options.files);
			
			// Prepare messages for API
			const messages = get(chatHistory);
			const messagesList = [];
			let current = messages.messages[userMessage.id];
			
			while (current) {
				messagesList.unshift(formatMessageForAPI(current));
				current = current.parentId ? messages.messages[current.parentId] : null;
			}
			
			// Handle web search if enabled
			if (options.webSearchEnabled) {
				const searchResults = await handleWebSearch(prompt);
				if (searchResults) {
					messagesList.push({
						role: 'system',
						content: `Web search results:\n${searchResults}`
					});
				}
			}
			
			// Handle memory query
			const memoryContext = await handleMemoryQuery(prompt);
			if (memoryContext) {
				messagesList.unshift({
					role: 'system',
					content: `Relevant context from memory:\n${memoryContext}`
				});
			}
			
			// Generate completion
			abortController = new AbortController();
			
			const completionOptions: ChatCompletionOptions = {
				model: options.model || get(selectedModels)[0],
				messages: messagesList,
				stream: true,
				tools: options.tools,
				imageGenerationEnabled: options.imageGenerationEnabled,
				webSearchEnabled: options.webSearchEnabled,
				params: options.params || get(settings)
			};
			
			let responseText = '';
			const response = await chatService.generateCompletion(
				completionOptions,
				abortController.signal
			);
			
			// Handle streaming response
			await chatService.createStreamHandler(
				(token) => {
					responseText += token;
					chatStore.updateMessage(assistantMessage.id, {
						content: responseText
					});
				},
				() => {
					chatStore.updateMessage(assistantMessage.id, {
						content: responseText,
						done: true
					});
					abortController = null;
				},
				(error) => {
					console.error('Stream error:', error);
					chatStore.updateMessage(assistantMessage.id, {
						error: true,
						content: responseText || 'An error occurred'
					});
					toast.error('Failed to generate response');
					abortController = null;
				}
			)(response);
			
			return assistantMessage;
		} catch (error) {
			console.error('Send prompt error:', error);
			toast.error('Failed to send message');
			throw error;
		}
	};
	
	// Stop the current response
	const stopResponse = async () => {
		if (abortController) {
			abortController.abort();
			abortController = null;
		}
		
		// Stop any running tasks
		const taskIds = get(chatStore.taskIds);
		if (taskIds && taskIds.length > 0) {
			await chatService.stopAllTasks(taskIds);
		}
	};
	
	// Regenerate a response
	const regenerateResponse = async (message: ChatMessage) => {
		if (message.role !== 'assistant') return;
		
		// Find the parent user message
		const history = get(chatHistory);
		const userMessage = message.parentId ? history.messages[message.parentId] : null;
		
		if (!userMessage || userMessage.role !== 'user') {
			toast.error('Cannot regenerate: parent message not found');
			return;
		}
		
		// Create new assistant message
		const newAssistantMessage = createMessage('assistant', '', userMessage.id, {
			model: message.model || get(selectedModels)[0]
		});
		
		chatStore.addMessage(newAssistantMessage);
		chatStore.setCurrentId(newAssistantMessage.id);
		
		// Send the prompt again
		await sendPrompt(userMessage.content, {
			model: message.model,
			parentId: userMessage.parentId || undefined,
			files: userMessage.files
		});
	};
	
	// Continue a response
	const continueResponse = async () => {
		const history = get(chatHistory);
		const currentMessage = history.currentId ? history.messages[history.currentId] : null;
		
		if (!currentMessage || currentMessage.role !== 'assistant' || !currentMessage.done) {
			toast.error('Cannot continue: no completed assistant message');
			return;
		}
		
		// Create a continuation prompt
		const continuationPrompt = 'Continue from where you left off.';
		await sendPrompt(continuationPrompt, {
			model: currentMessage.model,
			parentId: currentMessage.id
		});
	};
	
	// Handle web search
	const handleWebSearch = async (query: string): Promise<string | null> => {
		try {
			const token = localStorage.getItem('token');
			const results = await processWebSearch(token, {
				query,
				limit: 5
			});
			
			if (results && results.length > 0) {
				return results.map((r: any) => 
					`Title: ${r.title}\nURL: ${r.url}\nSnippet: ${r.snippet}`
				).join('\n\n');
			}
			
			return null;
		} catch (error) {
			console.error('Web search error:', error);
			return null;
		}
	};
	
	// Handle memory query
	const handleMemoryQuery = async (prompt: string): Promise<string | null> => {
		try {
			const token = localStorage.getItem('token');
			const results = await queryMemory(token, {
				content: prompt,
				k: 10
			});
			
			if (results && results.length > 0) {
				return results.map((r: any) => r.content).join('\n\n');
			}
			
			return null;
		} catch (error) {
			console.error('Memory query error:', error);
			return null;
		}
	};
	
	// Update chat metadata
	const updateChatMetadata = async (updates: Partial<{ title: string; tags: string[] }>) => {
		const metadata = get(chatMetadata);
		if (!metadata.id) return;
		
		try {
			await chatService.updateChat(metadata.id, updates);
			chatMetadata.update(m => ({ ...m, ...updates }));
		} catch (error) {
			console.error('Failed to update chat metadata:', error);
			toast.error('Failed to update chat');
		}
	};
	
	return {
		initNewChat,
		loadChat,
		sendPrompt,
		stopResponse,
		regenerateResponse,
		continueResponse,
		updateChatMetadata,
		createMessagePair
	};
}