export interface OpenAIConnection {
	OPENAI_API_BASE_URLS: string[];
	OPENAI_API_KEYS: string[];
	OPENAI_API_CONFIGS: {
		[key: string]: {
			enable?: boolean;
			model_ids?: string[];
			prefix_id?: string;
			tags?: string[];
		};
	};
}

export interface Model {
	id: string;
	name: string;
	owned_by?: string;
	openai?: {
		id: string;
	};
	urlIdx?: string;
	tags?: string[];
	direct?: boolean;
}

export interface ServerConfig {
	config: {
		enable: boolean;
	};
	auth_type?: string;
	key?: string;
	url: string;
	path?: string;
}

export interface I18n {
	t: (key: string, params?: Record<string, string>) => string;
}

export interface ModelMeta {
	description?: string;
	capabilities?: object;
	profile_image_url?: string;
}

export interface ModelParams {}

export interface ModelConfig {
	id: string;
	name: string;
	meta: ModelMeta;
	base_model_id?: string;
	params: ModelParams;
}

export type GlobalModelConfig = ModelConfig[];
