import { browser, dev } from '$app/environment';
// import { version } from '../../package.json';

/**
 * 应用名称常量
 * - 这是应用在全局使用的显示名称（默认值："Open WebUI"）。
 * - WEBUI_NAME Store 的初始值会引用这里，页面标题、导航栏、品牌展示等都会用到。
 *
 * 【修改方法】
 * - 如果你要改成自定义名字（例如 "CerebraUI"），直接修改此处的字符串即可：
 *   export const APP_NAME = 'CerebraUI';
 *
 * 【注意事项】
 * - 这是构建期常量，修改后需要重新构建/启动项目才能生效。
 * - 如果只想在运行时临时修改，可通过 WEBUI_NAME Store 调用 set() 来覆盖。
 */
export const APP_NAME = 'CerebraUI';

// ❌ 原来：const WEBUI_HOSTNAME = browser ? (dev ? `${location.hostname}:8080` : ``) : '';
// ❌ 原来：const WEBUI_BASE_URL = browser ? (dev ? `http://${WEBUI_HOSTNAME}` : ``) : '';
// ✅ 改成“相对路径”（让 5050 代理到 8080）
export const WEBUI_HOSTNAME = browser ? (dev ? location.host : '') : '';
export const WEBUI_BASE_URL = ''; // dev/prod 都用相对路径

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

// Source: https://kit.svelte.dev/docs/modules#$env-static-public
// This feature, akin to $env/static/private, exclusively incorporates environment variables
// that are prefixed with config.kit.env.publicPrefix (usually set to PUBLIC_).
// Consequently, these variables can be securely exposed to client-side code.
