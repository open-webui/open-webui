import { RAG_API_BASE_URL } from '$lib/constants';
import { fetchApi } from '$lib/apis/utils';

export const getRAGConfig = async (token: string) =>
	await fetchApi(`${RAG_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

type ChunkConfigForm = {
	chunk_size: number;
	chunk_overlap: number;
};

type YoutubeConfigForm = {
	language: string[];
	translation?: string | null;
};

type RAGConfigForm = {
	pdf_extract_images?: boolean;
	chunk?: ChunkConfigForm;
	web_loader_ssl_verification?: boolean;
	youtube?: YoutubeConfigForm;
};

export const updateRAGConfig = async (token: string, payload: RAGConfigForm) =>
	await fetchApi(`${RAG_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...payload
		})
	});

export const getRAGTemplate = async (token: string) => {
	const res = await fetchApi(`${RAG_API_BASE_URL}/template`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	return res?.template ?? '';
};

export const getQuerySettings = async (token: string) =>
	await fetchApi(`${RAG_API_BASE_URL}/query/settings`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

type QuerySettings = {
	k: number | null;
	r: number | null;
	template: string | null;
};

export const updateQuerySettings = async (token: string, settings: QuerySettings) =>
	await fetchApi(`${RAG_API_BASE_URL}/query/settings/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...settings
		})
	});

export const uploadDocToVectorDB = async (token: string, collection_name: string, file: File) => {
	const data = new FormData();
	data.append('file', file);
	data.append('collection_name', collection_name);

	return await fetchApi(`${RAG_API_BASE_URL}/doc`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		},
		body: data
	});
};

export const uploadWebToVectorDB = async (token: string, collection_name: string, url: string) =>
	await fetchApi(`${RAG_API_BASE_URL}/web`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			url: url,
			collection_name: collection_name
		})
	});

export const uploadYoutubeTranscriptionToVectorDB = async (token: string, url: string) =>
	await fetchApi(`${RAG_API_BASE_URL}/youtube`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			url: url
		})
	});

export const queryDoc = async (
	token: string,
	collection_name: string,
	query: string,
	k: number | null = null
) =>
	await fetchApi(`${RAG_API_BASE_URL}/query/doc`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			collection_name: collection_name,
			query: query,
			k: k
		})
	});

export const queryCollection = async (
	token: string,
	collection_names: string,
	query: string,
	k: number | null = null
) =>
	await fetchApi(`${RAG_API_BASE_URL}/query/collection`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			collection_names: collection_names,
			query: query,
			k: k
		})
	});

export const scanDocs = async (token: string) =>
	await fetchApi(`${RAG_API_BASE_URL}/scan`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		}
	});

export const resetVectorDB = async (token: string) =>
	await fetchApi(`${RAG_API_BASE_URL}/reset`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		}
	});

export const getEmbeddingConfig = async (token: string) =>
	await fetchApi(`${RAG_API_BASE_URL}/embedding`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

type OpenAIConfigForm = {
	key: string;
	url: string;
};

type EmbeddingModelUpdateForm = {
	openai_config?: OpenAIConfigForm;
	embedding_engine: string;
	embedding_model: string;
};

export const updateEmbeddingConfig = async (token: string, payload: EmbeddingModelUpdateForm) =>
	await fetchApi(`${RAG_API_BASE_URL}/embedding/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...payload
		})
	});

export const getRerankingConfig = async (token: string) =>
	await fetchApi(`${RAG_API_BASE_URL}/reranking`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

type RerankingModelUpdateForm = {
	reranking_model: string;
};

export const updateRerankingConfig = async (token: string, payload: RerankingModelUpdateForm) =>
	await fetchApi(`${RAG_API_BASE_URL}/reranking/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...payload
		})
	});
