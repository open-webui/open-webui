import { createApiClient } from './apiClient';
import {
	WEBUI_API_BASE_URL,
	OLLAMA_API_BASE_URL,
	OPENAI_API_BASE_URL,
	AUDIO_API_BASE_URL,
	IMAGES_API_BASE_URL,
	RETRIEVAL_API_BASE_URL,
	WEBUI_BASE_URL
} from '$lib/constants';

// Create API client instances for different base URLs
export const webuiClient = createApiClient(`${WEBUI_BASE_URL}/api`);
export const webuiApiClient = createApiClient(WEBUI_API_BASE_URL);
export const ollamaApiClient = createApiClient(OLLAMA_API_BASE_URL);
export const openaiApiClient = createApiClient(OPENAI_API_BASE_URL);
export const audioApiClient = createApiClient(AUDIO_API_BASE_URL);
export const imagesApiClient = createApiClient(IMAGES_API_BASE_URL);
export const retrievalApiClient = createApiClient(RETRIEVAL_API_BASE_URL);
