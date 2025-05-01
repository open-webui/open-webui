import { retrievalApiClient } from '../clients';

// Interfaces
export interface ChunkConfig {
	chunk_size: number;
	chunk_overlap: number;
}

export interface DocumentIntelligenceConfig {
	key: string;
	endpoint: string;
}

export interface ContentExtractConfig {
	engine: string;
	tika_server_url: string | null;
	document_intelligence_config: DocumentIntelligenceConfig | null;
}

export interface YoutubeConfig {
	language: string[];
	translation?: string | null;
	proxy_url: string;
}

export interface RAGConfig {
	PDF_EXTRACT_IMAGES?: boolean;
	ENABLE_GOOGLE_DRIVE_INTEGRATION?: boolean;
	ENABLE_ONEDRIVE_INTEGRATION?: boolean;
	chunk?: ChunkConfig;
	content_extraction?: ContentExtractConfig;
	web_loader_ssl_verification?: boolean;
	youtube?: YoutubeConfig;
}

export interface QuerySettings {
	k: number | null;
	r: number | null;
	template: string | null;
}

export interface OpenAIConfig {
	key: string;
	url: string;
}

export interface EmbeddingModelConfig {
	openai_config?: OpenAIConfig;
	embedding_engine: string;
	embedding_model: string;
	embedding_batch_size?: number;
}

export interface RerankingModelConfig {
	reranking_model: string;
}

export interface SearchDocument {
	status: boolean;
	collection_name: string;
	filenames: string[];
}

// Configuration Operations
export const getRAGConfig = async (token: string): Promise<RAGConfig> => {
	try {
		return await retrievalApiClient.get('/config', { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to get RAG configuration';
	}
};

export const updateRAGConfig = async (token: string, config: RAGConfig) => {
	try {
		return await retrievalApiClient.post('/config/update', config, { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to update RAG configuration';
	}
};

// Query Settings Operations
export const getQuerySettings = async (token: string): Promise<QuerySettings> => {
	try {
		return await retrievalApiClient.get('/query/settings', { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to get query settings';
	}
};

export const updateQuerySettings = async (token: string, settings: QuerySettings) => {
	try {
		return await retrievalApiClient.post('/query/settings/update', settings, { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to update query settings';
	}
};

// Embedding Operations
export const getEmbeddingConfig = async (token: string): Promise<EmbeddingModelConfig> => {
	try {
		return await retrievalApiClient.get('/embedding', { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to get embedding configuration';
	}
};

export const updateEmbeddingConfig = async (token: string, config: EmbeddingModelConfig) => {
	try {
		return await retrievalApiClient.post('/embedding/update', config, { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to update embedding configuration';
	}
};

// Reranking Operations
export const getRerankingConfig = async (token: string): Promise<RerankingModelConfig> => {
	try {
		return await retrievalApiClient.get('/reranking', { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to get reranking configuration';
	}
};

export const updateRerankingConfig = async (token: string, config: RerankingModelConfig) => {
	try {
		return await retrievalApiClient.post('/reranking/update', config, { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to update reranking configuration';
	}
};

// Processing Operations
export const processFile = async (
	token: string,
	file_id: string,
	collection_name: string | null = null
) => {
	try {
		return await retrievalApiClient.post(
			'/process/file',
			{ file_id, collection_name: collection_name ?? undefined },
			{ token }
		);
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to process file';
	}
};

export const processYoutubeVideo = async (token: string, url: string) => {
	try {
		return await retrievalApiClient.post('/process/youtube', { url }, { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to process YouTube video';
	}
};

export const processWeb = async (token: string, collection_name: string, url: string) => {
	try {
		return await retrievalApiClient.post('/process/web', { url, collection_name }, { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to process web content';
	}
};

export const processWebSearch = async (
	token: string,
	query: string,
	collection_name?: string
): Promise<SearchDocument> => {
	try {
		return await retrievalApiClient.post(
			'/process/web/search',
			{ query, collection_name: collection_name ?? '' },
			{ token }
		);
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to process web search';
	}
};

// Query Operations
export const queryDoc = async (
	token: string,
	collection_name: string,
	query: string,
	k: number | null = null
) => {
	try {
		return await retrievalApiClient.post('/query/doc', { collection_name, query, k }, { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to query document';
	}
};

export const queryCollection = async (
	token: string,
	collection_names: string,
	query: string,
	k: number | null = null
) => {
	try {
		return await retrievalApiClient.post(
			'/query/collection',
			{ collection_names, query, k },
			{ token }
		);
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to query collection';
	}
};

// Reset Operations
export const resetUploadDir = async (token: string) => {
	try {
		return await retrievalApiClient.post('/reset/uploads', undefined, { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to reset upload directory';
	}
};

export const resetVectorDB = async (token: string) => {
	try {
		return await retrievalApiClient.post('/reset/db', undefined, { token });
	} catch (error) {
		throw error instanceof Error ? error.message : 'Failed to reset vector database';
	}
};
