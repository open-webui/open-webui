import { v4 as uuidv4 } from 'uuid';
import { get } from 'svelte/store';
import { toast } from 'svelte-sonner';

import type { ChatMessage, ChatCompletionOptions, ChatEventData } from '../types';
import { createNewChat, getChatById, updateChatById } from '$lib/apis/chats';
import { generateChatCompletion } from '$lib/apis/ollama';
import { generateOpenAIChatCompletion } from '$lib/apis/openai';
import { createOpenAITextStream } from '$lib/apis/streaming';
import { chatCompleted, generateMoACompletion, getTaskIdsByChatId, stopTask } from '$lib/apis';
import { models, user } from '$lib/stores';

export class ChatService {
	private eventTarget = new EventTarget();
	
	// Create a new chat
	async createChat(chat: any) {
		const token = localStorage.getItem('token');
		return await createNewChat(token, chat);
	}
	
	// Load chat by ID
	async loadChat(chatId: string) {
		const token = localStorage.getItem('token');
		try {
			const chat = await getChatById(token, chatId);
			return chat;
		} catch (error) {
			console.error('Failed to load chat:', error);
			return null;
		}
	}
	
	// Update chat
	async updateChat(chatId: string, updates: any) {
		const token = localStorage.getItem('token');
		return await updateChatById(token, chatId, updates);
	}
	
	// Get task IDs for a chat
	async getTaskIds(chatId: string) {
		const token = localStorage.getItem('token');
		try {
			const ids = await getTaskIdsByChatId(token, chatId);
			return ids;
		} catch (error) {
			console.error('Failed to get task IDs:', error);
			return null;
		}
	}
	
	// Stop all tasks for a chat
	async stopAllTasks(taskIds: string[]) {
		const token = localStorage.getItem('token');
		for (const taskId of taskIds) {
			await stopTask(token, taskId).catch(() => {
				console.error(`Failed to stop task ${taskId}`);
			});
		}
	}
	
	// Generate chat completion
	async generateCompletion(options: ChatCompletionOptions, signal?: AbortSignal) {
		const token = localStorage.getItem('token');
		const modelData = typeof options.model === 'string' 
			? get(models).find(m => m.id === options.model)
			: options.model;
			
		if (!modelData) {
			throw new Error('Model not found');
		}
		
		// Determine which API to use based on model
		if (modelData.owned_by === 'ollama') {
			return await this.generateOllamaCompletion(options, token, signal);
		} else {
			return await this.generateOpenAICompletion(options, token, signal);
		}
	}
	
	// Generate Ollama completion
	private async generateOllamaCompletion(options: ChatCompletionOptions, token: string, signal?: AbortSignal) {
		const modelId = typeof options.model === 'string' ? options.model : options.model.id;
		
		return await generateChatCompletion(token, {
			model: modelId,
			messages: options.messages,
			options: options.params,
			format: undefined,
			tools: options.tools?.length ? options.tools : undefined,
			stream: options.stream ?? true,
			...signal && { signal }
		});
	}
	
	// Generate OpenAI completion
	private async generateOpenAICompletion(options: ChatCompletionOptions, token: string, signal?: AbortSignal) {
		const modelId = typeof options.model === 'string' ? options.model : options.model.id;
		
		return await generateOpenAIChatCompletion(token, {
			model: modelId,
			messages: options.messages,
			seed: options.params?.seed,
			temperature: options.params?.temperature,
			top_p: options.params?.top_p,
			frequency_penalty: options.params?.frequency_penalty,
			presence_penalty: options.params?.presence_penalty,
			max_tokens: options.params?.max_tokens,
			tools: options.tools?.length ? options.tools : undefined,
			stream: options.stream ?? true,
			...signal && { signal }
		});
	}
	
	// Handle MoA (Mixture of Agents) completion
	async generateMoACompletion(
		modelId: string,
		messages: ChatMessage[],
		chatId: string,
		responseMessageId: string
	) {
		const token = localStorage.getItem('token');
		return await generateMoACompletion(token, modelId, messages, chatId, responseMessageId);
	}
	
	// Mark chat as completed
	async markChatCompleted(chatId: string, modelId: string, responseMessageId: string, messages: ChatMessage[]) {
		const token = localStorage.getItem('token');
		return await chatCompleted(token, chatId, modelId, responseMessageId, messages);
	}
	
	// Create a streaming response handler
	createStreamHandler(
		onToken: (token: string) => void,
		onComplete: () => void,
		onError: (error: any) => void
	) {
		return async (response: Response) => {
			if (!response.body) {
				throw new Error('No response body');
			}
			
			const reader = response.body.getReader();
			const decoder = new TextDecoder();
			
			try {
				while (true) {
					const { done, value } = await reader.read();
					if (done) break;
					
					const chunk = decoder.decode(value);
					const lines = chunk.split('\n');
					
					for (const line of lines) {
						if (line.startsWith('data: ')) {
							const data = line.slice(6);
							if (data === '[DONE]') {
								onComplete();
								return;
							}
							
							try {
								const parsed = JSON.parse(data);
								if (parsed.choices?.[0]?.delta?.content) {
									onToken(parsed.choices[0].delta.content);
								}
							} catch (e) {
								// Handle non-JSON data
								onToken(data);
							}
						}
					}
				}
				
				onComplete();
			} catch (error) {
				onError(error);
			}
		};
	}
	
	// Event handling
	on(event: string, handler: (data: any) => void) {
		this.eventTarget.addEventListener(event, (e: any) => handler(e.detail));
	}
	
	emit(event: string, data: any) {
		this.eventTarget.dispatchEvent(new CustomEvent(event, { detail: data }));
	}
}