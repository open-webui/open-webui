import { browser, dev } from '$app/environment';
import { env } from '$env/dynamic/public';
// import { version } from '../../package.json';

declare const APP_VERSION: string;
declare const APP_BUILD_HASH: string;

export const APP_NAME = 'Open WebUI';

const normalizeBaseUrl = (value: string) => value.replace(/\/+$/, '');
const normalizedPublicBaseUrl = env.PUBLIC_WEBUI_BASE_URL
	? normalizeBaseUrl(env.PUBLIC_WEBUI_BASE_URL)
	: '';

const readStoredBaseUrl = () => {
	if (!browser) {
		return '';
	}
	try {
		const localValue = localStorage.getItem('webui.baseUrl')?.trim() ?? '';
		if (localValue) {
			return localValue;
		}
		return sessionStorage.getItem('webui.baseUrl')?.trim() ?? '';
	} catch {
		return '';
	}
};

const buildUrl = (baseUrl: string, path: string) => (baseUrl ? `${baseUrl}${path}` : path);

export const WEBUI_HOSTNAME = browser ? (dev ? `${location.hostname}:8080` : ``) : '';
export let WEBUI_BASE_URL = '';
export let WEBUI_API_BASE_URL = '';
export let OLLAMA_API_BASE_URL = '';
export let OPENAI_API_BASE_URL = '';
export let GEMINI_API_BASE_URL = '';
export let AUDIO_API_BASE_URL = '';
export let IMAGES_API_BASE_URL = '';
export let RETRIEVAL_API_BASE_URL = '';

const applyBaseUrl = (baseUrl: string) => {
	const normalizedBaseUrl = baseUrl ? normalizeBaseUrl(baseUrl) : '';
	WEBUI_BASE_URL = normalizedBaseUrl;
	WEBUI_API_BASE_URL = buildUrl(WEBUI_BASE_URL, '/api/v1');
	OLLAMA_API_BASE_URL = buildUrl(WEBUI_BASE_URL, '/ollama');
	OPENAI_API_BASE_URL = buildUrl(WEBUI_BASE_URL, '/openai');
	GEMINI_API_BASE_URL = buildUrl(WEBUI_BASE_URL, '/gemini');
	AUDIO_API_BASE_URL = buildUrl(WEBUI_BASE_URL, '/api/v1/audio');
	IMAGES_API_BASE_URL = buildUrl(WEBUI_BASE_URL, '/api/v1/images');
	RETRIEVAL_API_BASE_URL = buildUrl(WEBUI_BASE_URL, '/api/v1/retrieval');
};

export const syncWebuiBaseUrl = (override?: string) => {
	const storedBaseUrl = override ?? readStoredBaseUrl();
	const normalizedStoredBaseUrl = storedBaseUrl ? normalizeBaseUrl(storedBaseUrl) : '';
	const resolvedBaseUrl = browser
		? normalizedStoredBaseUrl || normalizedPublicBaseUrl || (dev ? `http://${WEBUI_HOSTNAME}` : ``)
		: normalizedStoredBaseUrl || normalizedPublicBaseUrl || ``;

	applyBaseUrl(resolvedBaseUrl);
	return resolvedBaseUrl;
};

syncWebuiBaseUrl();

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

// Source: https://kit.svelte.dev/docs/modules#$env-dynamic-public
// Dynamic public env exposes variables prefixed with config.kit.env.publicPrefix
// (usually set to PUBLIC_) to client-side code at runtime.
