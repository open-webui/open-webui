import { ollamaApiClient } from '../clients';

interface OllamaConfig {
	ENABLE_OLLAMA_API: boolean;
	OLLAMA_BASE_URLS: string[];
	OLLAMA_API_CONFIGS: Record<string, unknown>;
}

interface OllamaModel {
	model: string;
	name?: string;
	[key: string]: unknown;
}

export const verifyOllamaConnection = async (
	token: string = '',
	url: string = '',
	key: string = ''
) => {
	try {
		return await ollamaApiClient.post('/verify', { url, key }, { token });
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Network Problem';
		throw `Ollama: ${errorMessage}`;
	}
};

export const getOllamaConfig = async (token: string = '') => {
	try {
		return await ollamaApiClient.get<OllamaConfig>('/config', { token });
	} catch (error) {
		console.error('Failed to get Ollama config:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	}
};

export const updateOllamaConfig = async (token: string = '', config: OllamaConfig) => {
	try {
		return await ollamaApiClient.post('/config/update', config, { token });
	} catch (error) {
		console.error('Failed to update Ollama config:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	}
};

export const getOllamaUrls = async (token: string = '') => {
	try {
		const response = await ollamaApiClient.get<{ OLLAMA_BASE_URLS: string[] }>('/urls', { token });
		return response.OLLAMA_BASE_URLS;
	} catch (error) {
		console.error('Failed to get Ollama URLs:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	}
};

export const updateOllamaUrls = async (token: string = '', urls: string[]) => {
	try {
		const response = await ollamaApiClient.post<{ OLLAMA_BASE_URLS: string[] }>(
			'/urls/update',
			{ urls },
			{ token }
		);
		return response.OLLAMA_BASE_URLS;
	} catch (error) {
		console.error('Failed to update Ollama URLs:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	}
};

export const getOllamaVersion = async (token: string, urlIdx?: number) => {
	try {
		const response = await ollamaApiClient.get<{ version: string }>(
			`/api/version${urlIdx ? `/${urlIdx}` : ''}`,
			{
				token
			}
		);
		return response?.version ?? false;
	} catch (error) {
		console.error('Failed to get Ollama version:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	}
};

export const getOllamaModels = async (token: string = '', urlIdx: number | null = null) => {
	try {
		const response = await ollamaApiClient.get<{ models: OllamaModel[] }>(
			`/api/tags${urlIdx !== null ? `/${urlIdx}` : ''}`,
			{ token }
		);
		return (response?.models ?? [])
			.map((model: OllamaModel) => ({ id: model.model, name: model.name ?? model.model, ...model }))
			.sort((a: OllamaModel, b: OllamaModel) => (a.name || '').localeCompare(b.name || ''));
	} catch (error) {
		console.error('Failed to get Ollama models:', error);
		throw error instanceof Error ? error.message : 'Server connection failed';
	}
};

export const generatePrompt = async (token: string = '', model: string, conversation: string) => {
	try {
		if (conversation === '') {
			conversation = '[no existing conversation]';
		}
		return await ollamaApiClient.post(
			'/api/generate',
			{
				model,
				prompt: `Conversation:
			${conversation}

			As USER in the conversation above, your task is to continue the conversation. Remember, Your responses should be crafted as if you're a human conversing in a natural, realistic manner, keeping in mind the context and flow of the dialogue. Please generate a fitting response to the last message in the conversation, or if there is no existing conversation, initiate one as a normal person would.
			
			Response:
			`
			},
			{ token }
		);
	} catch (error) {
		console.error('Failed to generate prompt:', error);
		throw error;
	}
};

export const generateEmbeddings = async (token: string = '', model: string, text: string) => {
	try {
		return await ollamaApiClient.post('/api/embeddings', { model, prompt: text }, { token });
	} catch (error) {
		console.error('Failed to generate embeddings:', error);
		throw error;
	}
};

export const generateTextCompletion = async (token: string = '', model: string, text: string) => {
	try {
		return await ollamaApiClient.post(
			'/api/generate',
			{ model, prompt: text, stream: true },
			{ token }
		);
	} catch (error) {
		console.error('Failed to generate text completion:', error);
		throw error;
	}
};

export const generateChatCompletion = async (token: string = '', body: Record<string, unknown>) => {
	try {
		const controller = new AbortController();
		const response = await ollamaApiClient.post('/api/chat', body, {
			token,
			signal: controller.signal
		});
		return [response, controller];
	} catch (error) {
		console.error('Failed to generate chat completion:', error);
		throw error;
	}
};

export const createModel = async (
	token: string,
	payload: Record<string, unknown>,
	urlIdx: string | null = null
) => {
	try {
		return await ollamaApiClient.post(
			`/api/create${urlIdx !== null ? `/${urlIdx}` : ''}`,
			payload,
			{ token }
		);
	} catch (error) {
		console.error('Failed to create model:', error);
		throw error;
	}
};

export const deleteModel = async (token: string, tagName: string, urlIdx: string | null = null) => {
	try {
		return await ollamaApiClient.del(
			`/api/delete${urlIdx !== null ? `/${urlIdx}` : ''}`,
			{ name: tagName },
			{ token }
		);
	} catch (error) {
		console.error('Failed to delete model:', error);
		throw error;
	}
};

export const pullModel = async (token: string, tagName: string, urlIdx: number | null = null) => {
	try {
		const controller = new AbortController();
		const response = await ollamaApiClient.post(
			`/api/pull${urlIdx !== null ? `/${urlIdx}` : ''}`,
			{ name: tagName },
			{ token, signal: controller.signal }
		);
		return [response, controller];
	} catch (error) {
		console.error('Failed to pull model:', error);
		throw error;
	}
};

export const downloadModel = async (
	token: string,
	download_url: string,
	urlIdx: string | null = null
) => {
	try {
		return await ollamaApiClient.post(
			`/models/download${urlIdx !== null ? `/${urlIdx}` : ''}`,
			{ url: download_url },
			{ token }
		);
	} catch (error) {
		console.error('Failed to download model:', error);
		throw error;
	}
};

export const uploadModel = async (token: string, file: File, urlIdx: string | null = null) => {
	try {
		const formData = new FormData();
		formData.append('file', file);
		return await ollamaApiClient.post(
			`/models/upload${urlIdx !== null ? `/${urlIdx}` : ''}`,
			formData,
			{ token }
		);
	} catch (error) {
		console.error('Failed to upload model:', error);
		throw error;
	}
};

// export const pullModel = async (token: string, tagName: string) => {
// 	return await fetch(`${OLLAMA_API_BASE_URL}/pull`, {
// 		method: 'POST',
// 		headers: {
// 			'Content-Type': 'text/event-stream',
// 			Authorization: `Bearer ${token}`
// 		},
// 		body: JSON.stringify({
// 			name: tagName
// 		})
// 	});
// };
