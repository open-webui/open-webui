import { browser, dev } from '$app/environment';
// import { version } from '../../package.json';

export const APP_NAME = 'Pilot GenAI';

export const WEBUI_HOSTNAME = browser ? (dev ? `${location.hostname}:8080` : ``) : '';
export const WEBUI_BASE_URL = browser ? (dev ? `http://${WEBUI_HOSTNAME}` : ``) : ``;
export const WEBUI_API_BASE_URL = `${WEBUI_BASE_URL}/api/v1`;

export const OLLAMA_API_BASE_URL = `${WEBUI_BASE_URL}/ollama`;
export const OPENAI_API_BASE_URL = `${WEBUI_BASE_URL}/openai`;
export const AUDIO_API_BASE_URL = `${WEBUI_BASE_URL}/api/v1/audio`;
export const IMAGES_API_BASE_URL = `${WEBUI_BASE_URL}/api/v1/images`;
export const RETRIEVAL_API_BASE_URL = `${WEBUI_BASE_URL}/api/v1/retrieval`;

export const WEBUI_VERSION = APP_VERSION;
export const WEBUI_BUILD_HASH = APP_BUILD_HASH;
export const REQUIRED_OLLAMA_VERSION = '0.1.16';

export const SUPPORTED_FILE_TYPE = [
	'application/epub+zip',
	'application/pdf',
	'text/plain',
	'text/csv',
	'text/xml',
	'text/html',
	'text/x-python',
	'text/css',
	'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
	'application/octet-stream',
	'application/x-javascript',
	'text/markdown',
	'audio/mpeg',
	'audio/wav',
	'audio/ogg',
	'audio/x-m4a'
];

export const SUPPORTED_FILE_EXTENSIONS = [
	'md',
	'rst',
	'go',
	'py',
	'java',
	'sh',
	'bat',
	'ps1',
	'cmd',
	'js',
	'ts',
	'css',
	'cpp',
	'hpp',
	'h',
	'c',
	'cs',
	'htm',
	'html',
	'sql',
	'log',
	'ini',
	'pl',
	'pm',
	'r',
	'dart',
	'dockerfile',
	'env',
	'php',
	'hs',
	'hsc',
	'lua',
	'nginxconf',
	'conf',
	'm',
	'mm',
	'plsql',
	'perl',
	'rb',
	'rs',
	'db2',
	'scala',
	'bash',
	'swift',
	'vue',
	'svelte',
	'doc',
	'docx',
	'pdf',
	'csv',
	'txt',
	'xls',
	'xlsx',
	'pptx',
	'ppt',
	'msg'
];

export const PASTED_TEXT_CHARACTER_LIMIT = 1000;

// Mermaid Scalability Configuration
export const MERMAID_CONFIG = {
	// Memory Cache (Fast Path)
	MEMORY_CACHE_SIZE: 100,

	// IndexedDB (Persistence)
	INDEXEDDB_ENABLED: true,
	INDEXEDDB_STORE_NAME: 'mermaid_cache',
	INDEXEDDB_MAX_SIZE: 5 * 1024 * 1024, // 5MB
	INDEXEDDB_TTL_DAYS: 7,

	// Cross-Tab Sync
	BROADCAST_CHANNEL_ENABLED: true,
	BROADCAST_CHANNEL_NAME: 'mermaid-cache-sync',

	// Performance
	DEBOUNCE_DELAY: 300,
	RENDER_TIMEOUT: 5000,
	LAZY_LOAD_MARGIN: 100,
	LAZY_LOAD_THRESHOLD: 0.1,

	// Error Handling
	MAX_RETRIES: 2,

	// Monitoring
	ENABLE_METRICS: true,
	METRICS_LOG_INTERVAL: 100, // Log every 100 renders

	// Performance Thresholds
	SLOW_RENDER_WARNING_MS: 500,
	LOW_CACHE_HIT_RATE: 0.5,
	HIGH_ERROR_RATE: 0.05
};

// Source: https://kit.svelte.dev/docs/modules#$env-static-public
// This feature, akin to $env/static/private, exclusively incorporates environment variables
// that are prefixed with config.kit.env.publicPrefix (usually set to PUBLIC_).
// Consequently, these variables can be securely exposed to client-side code.
