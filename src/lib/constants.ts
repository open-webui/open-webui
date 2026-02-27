import { browser, dev } from '$app/environment';
// import { version } from '../../package.json';

export const APP_NAME = 'Open WebUI';

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

export const DEFAULT_CAPABILITIES = {
	file_context: true,
	vision: true,
	file_upload: true,
	web_search: true,
	image_generation: true,
	code_interpreter: true,
	citations: true,
	status_updates: true,
	usage: undefined,
	builtin_tools: true
};

export const PASTED_TEXT_CHARACTER_LIMIT = 1000;

// Source: https://kit.svelte.dev/docs/modules#$env-static-public
// This feature, akin to $env/static/private, exclusively incorporates environment variables
// that are prefixed with config.kit.env.publicPrefix (usually set to PUBLIC_).
// Consequently, these variables can be securely exposed to client-side code.

export const MODEL_NAME_MAPPING = {
  "gemma3": "Gemma 3",
  "openthinker": "OpenThinker",
  "qwen3": "Qwen 3",
  "qwen3-8b": "Qwen 3 Small",
  "text-embedding-3-small": "Text Embedding 3 Small",
  "text-embedding-3-large": "Text Embedding 3 Large",
  "qwen3-embedding": "Qwen 3 Embedding",
  "bge-m3-embedding": "BGE M3 Embedding",
  "qwen3-rerank": "Qwen 3 Reranker",
  "o3-deep-research": "O3 Deep Research",
  "o4-mini-deep-research": "O4 Mini Deep Research",
  "gpt-5": "GPT 5",
  "gpt-5.2": "GPT 5.2",
  "gpt-5.2-codex": "GPT 5.2 Codex",
  "gpt-5-mini": "GPT 5 Mini",
  "gpt-5-nano": "GPT 5 Nano",
  "o4-mini": "O4 Mini",
  "claude-sonnet-4-5": "Claude Sonnet 4.5",
  "claude-sonnet-4-6": "Claude Sonnet 4.6",
  "claude-opus-4-6": "Claude Opus 4.6",
  "gemini-3.1-pro-preview": "Gemini 3.1 Pro Preview",
  "gpt-4o-mini-tts": "GPT-4o Mini Text-to-Speech",
  "gpt-4o-transcribe": "GPT-4o Transcription",
  "dall-e-3": "DALL·E 3",
  "gpt-image-1.5": "GPT Image 1.5",
  "qwen3-coder": "Qwen 3 Coder",
  "whisper": "Whisper",
  "kokoro": "Kokoro"
}