/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly OPENAI_API_BASE_URLS: string;
	readonly OPENAI_API_KEYS: string[];
	readonly OPENAI_API_CONFIGS: Record<string, unknown>;
}

interface ImportMeta {
	readonly env: ImportMetaEnv;
}
