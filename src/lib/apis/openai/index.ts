import { openaiApiClient, webuiApiClient } from '../clients';
import axios, { AxiosError } from 'axios';

interface APIError {
	detail?: string;
	message?: string;
}

interface OpenAIErrorResponse {
	error: {
		message: string;
	};
}

type OpenAIConfig = {
	ENABLE_OPENAI_API: boolean;
	OPENAI_API_BASE_URLS: string[];
	OPENAI_API_KEYS: string[];
	OPENAI_API_CONFIGS: object;
};

type OpenAIUrlsResponse = {
	OPENAI_API_BASE_URLS: string[];
};

type OpenAIKeysResponse = {
	OPENAI_API_KEYS: string[];
};

interface OpenAIModel {
	id: string;
	object: string;
	created: number;
	owned_by: string;
}

interface OpenAIModelsResponse {
	object: string;
	data: OpenAIModel[];
}

// OpenAI API specific endpoints
export const getOpenAIConfig = async (token: string = '') =>
	openaiApiClient.get<OpenAIConfig>('/config', { token }).catch((error) => {
		console.error('Failed to get OpenAI config:', error);
		throw error;
	});

export const updateOpenAIConfig = async (token: string = '', config: OpenAIConfig) =>
	openaiApiClient.post<OpenAIConfig>('/config/update', config, { token }).catch((error) => {
		console.error('Failed to update OpenAI config:', error);
		throw error;
	});

export const getOpenAIUrls = async (token: string = '') =>
	openaiApiClient
		.get<OpenAIUrlsResponse>('/urls', { token })
		.then((res) => res.OPENAI_API_BASE_URLS)
		.catch((error) => {
			console.error('Failed to get OpenAI URLs:', error);
			throw error;
		});

export const updateOpenAIUrls = async (token: string = '', urls: string[]) =>
	openaiApiClient
		.post<OpenAIUrlsResponse>('/urls/update', { urls }, { token })
		.then((res) => res.OPENAI_API_BASE_URLS)
		.catch((error) => {
			console.error('Failed to update OpenAI URLs:', error);
			throw error;
		});

export const getOpenAIKeys = async (token: string = '') =>
	openaiApiClient
		.get<OpenAIKeysResponse>('/keys', { token })
		.then((res) => res.OPENAI_API_KEYS)
		.catch((error) => {
			console.error('Failed to get OpenAI keys:', error);
			throw error;
		});

export const updateOpenAIKeys = async (token: string = '', keys: string[]) =>
	openaiApiClient
		.post<OpenAIKeysResponse>('/keys/update', { keys }, { token })
		.then((res) => res.OPENAI_API_KEYS)
		.catch((error) => {
			console.error('Failed to update OpenAI keys:', error);
			throw error;
		});

// Direct OpenAI API calls
export const getOpenAIModelsDirect = async (url: string, key: string) =>
	axios
		.get<OpenAIModelsResponse>(`${url}/models`, {
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(key && { Authorization: `Bearer ${key}` })
			}
		})
		.then((response) => response.data)
		.catch((error) => {
			throw `OpenAI: ${(error as AxiosError<OpenAIErrorResponse>).response?.data?.error?.message ?? 'Network Problem'}`;
		});

// OpenAI API endpoints through our backend
export const getOpenAIModels = async (token: string, urlIdx?: number) =>
	openaiApiClient
		.get<OpenAIModelsResponse>(`/models${typeof urlIdx === 'number' ? `/${urlIdx}` : ''}`, {
			token
		})
		.catch((error) => {
			console.error('Failed to get OpenAI models:', error);
			throw error;
		});

export const verifyOpenAIConnection = async (
	token: string = '',
	url: string = 'https://api.openai.com/v1',
	key: string = '',
	direct: boolean = false
) => {
	if (!url) throw 'OpenAI: URL is required';
	return direct
		? axios
				.get<OpenAIModelsResponse>(`${url}/models`, {
					headers: {
						Accept: 'application/json',
						'Content-Type': 'application/json',
						Authorization: `Bearer ${key}`
					}
				})
				.then((response) => response.data)
				.catch((error) => {
					throw `OpenAI: ${(error as AxiosError<OpenAIErrorResponse>).response?.data?.error?.message ?? 'Network Problem'}`;
				})
		: openaiApiClient
				.post<OpenAIModelsResponse>('/verify', { url, key }, { token })
				.catch((error) => {
					throw `OpenAI: ${(error as AxiosError<OpenAIErrorResponse>).response?.data?.error?.message ?? 'Network Problem'}`;
				});
};

// WebUI API endpoints
export const chatCompletion = async (
	token: string = '',
	body: object
): Promise<[Response | null, AbortController]> => {
	try {
		const controller = new AbortController();
		const response = await webuiApiClient.post<Response>('/api/chat/completions', body, {
			token,
			signal: controller.signal
		});
		return [response, controller];
	} catch (error) {
		console.error('Failed to generate chat completion:', error);
		throw error;
	}
};

export const generateOpenAIChatCompletion = async (token: string = '', body: object) =>
	webuiApiClient.post('/api/chat/completions', body, { token }).catch((error) => {
		throw `${(error as APIError).detail ?? error}`;
	});

export const synthesizeOpenAISpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model: string = 'tts-1'
) =>
	openaiApiClient
		.post<Blob>(
			'/audio/speech',
			{ model, input: text, voice: speaker },
			{ token, headers: { 'Content-Type': 'application/json' } }
		)
		.catch((error) => {
			console.error('Failed to synthesize speech:', error);
			throw error;
		});
