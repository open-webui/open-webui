import { get } from 'svelte/store';
import { config } from '$lib/stores';
import { checkSourceSize, readSourceResponse } from './sourceText';
// The same attachment is used by @mentions, terminal uploads, and Files-pane requests.
export type FilesystemFile = {
	type: 'filesystem';
	id: string;
	path: string;
	url: string;
	name: string;
	status: string;
	size?: number;
	modified?: number;
	terminal_id?: string;
	session_id?: string | null;
};
export const filesystemFile = (
	entry: { path: string; name: string; size?: number; modified?: number },
	terminalId: string,
	sessionId: string | null
): FilesystemFile => ({
	type: 'filesystem',
	id: entry.path,
	path: entry.path,
	url: entry.path,
	name: entry.name,
	size: entry.size,
	modified: entry.modified,
	status: 'processed',
	terminal_id: terminalId,
	session_id: sessionId
});

export type FileEntry = {
	name: string;
	type: 'file' | 'directory';
	size?: number;
	modified?: number;
	created?: number | null;
	writable?: boolean;
};

export type TerminalFileList = {
	entries: FileEntry[];
	writable?: boolean;
};

export type TerminalFileSearchResult = FileEntry & {
	path: string;
};

export type TerminalFileSearchResponse = {
	results: TerminalFileSearchResult[];
};

export type TerminalContentMatch = {
	line: number;
	column: number;
	text: string;
};

export type TerminalFileMatch = {
	path: string;
	relative_path: string;
	name: string;
	type: 'file' | 'directory';
	name_match: boolean;
	content_matches: TerminalContentMatch[];
};

export type TerminalFileMatchesResponse = {
	results: TerminalFileMatch[];
	next_offset: number | null;
};

export type ListeningPort = {
	port: number;
	pid: number | null;
	process: string | null;
};

export type TerminalSystemInfo = {
	sampled_at: number;
	hostname: string;
	os: string;
	arch: string;
	environment: 'host' | 'container';
	uptime_seconds: number | null;
	service_uptime_seconds: number;
	cpu: { percent: number | null; cores: number | null; scope: 'host' | 'cgroup' };
	memory: { total: number; used: number; scope: 'host' | 'cgroup' } | null;
	disk: { path: string; total: number; used: number; free: number } | null;
	network: { name: string; up: boolean | null; addresses: string[] }[] | null;
	process_scope: 'user' | 'environment';
	processes:
		| {
				pid: number;
				name: string;
				cpu_percent: number | null;
				memory_bytes: number;
		  }[]
		| null;
	/** Present when the terminal has a setup script. */
	setup?: {
		status: 'running' | 'ok' | 'failed';
		exit_code?: number;
		log_tail?: string;
	};
};

export type TerminalFeatures = {
	agents?: boolean;
	terminal?: boolean;
	browser?: boolean;
	desktop?: boolean;
	git?: boolean;
	events?: boolean;
};

// Missing flags mean unsupported; never probe a new endpoint on an older server.
export async function getTerminalFeatures(
	target: Pick<TerminalTarget, 'baseUrl' | 'key' | 'context'>,
	signal?: AbortSignal
): Promise<TerminalFeatures> {
	try {
		const result = await terminalRequest<{ features?: TerminalFeatures }>(
			target,
			'/api/config',
			{ signal }
		);
		return result.features ?? {};
	} catch {
		return {};
	}
}

export type TerminalFileRoot = {
	path: string;
	label: string;
};

export type TerminalCwd = {
	cwd: string | null;
	home?: string;
	root?: TerminalFileRoot;
};

export type TerminalSkill = {
	id: string;
	name: string;
	description: string;
	is_active: boolean;
	source: 'terminal';
	terminal_path: string;
	terminal_selector: string;
	terminal_name?: string;
};

import { WEBUI_API_BASE_URL } from '$lib/constants';

export type TerminalTarget = {
	selector: string;
	baseUrl: string;
	key: string;
	system: boolean;
	context: { chatId: string | null; modelId: string | null };
};
export type TerminalProcess = {
	id: string;
	command: string;
	status: 'running' | 'done' | 'killed';
	exit_code: number | null;
};
export type TerminalProcessOutput = TerminalProcess & {
	output: { type: string; data: string }[];
	next_offset: number;
	truncated: boolean;
};

export const resolveTerminalTarget = (
	selector: string | null,
	servers: any[],
	directServers: any[],
	token: string,
	context: Partial<TerminalTarget['context']> = {}
): TerminalTarget | null => {
	if (!get(config)?.features?.enable_tool_servers || !selector) return null;
	const server = servers.find((server) => server.id === selector);
	if (server) {
		if (server.scope === 'model' && !context.modelId) return null;
		return {
			selector,
			baseUrl: `${WEBUI_API_BASE_URL}/terminals/${encodeURIComponent(selector)}`,
			context: {
				chatId: context.chatId ?? null,
				modelId: server.scope === 'model' ? (context.modelId ?? null) : null
			},
			// Panels outlive Tether's token rotations; read the current session at request time.
			get key() {
				return typeof localStorage === 'undefined' ? token : (localStorage.getItem('token') ?? '');
			},
			system: true
		};
	}
	const direct = directServers.find((server) => server.url === selector);
	return direct
		? {
				selector,
				baseUrl: direct.url.replace(/\/$/, ''),
				key: direct.key ?? '',
				system: false,
				context: { chatId: context.chatId ?? null, modelId: null }
			}
		: null;
};

export class TerminalRequestError extends Error {
	constructor(
		message: string,
		public status: number
	) {
		super(message);
		this.name = 'TerminalRequestError';
	}
}

export const terminalRequest = async <T>(
	target: Pick<TerminalTarget, 'baseUrl' | 'key' | 'context'>,
	path: string,
	options: RequestInit = {}
): Promise<T> => {
	if (!get(config)?.features?.enable_tool_servers)
		throw new TerminalRequestError('Tool servers are disabled', 403);
	const response = await fetch(`${target.baseUrl}${path}`, {
		...options,
		headers: {
			...terminalHeaders(target),
			...options.headers
		}
	});
	if (!response.ok) {
		const body = await response.json().catch(() => null);
		throw new TerminalRequestError(
			typeof body?.detail === 'string'
				? body.detail
				: typeof body?.error === 'string'
					? body.error
					: `Terminal request failed (${response.status})`,
			response.status
		);
	}
	return response.json();
};

export const terminalHeaders = (
	target: Pick<TerminalTarget, 'key' | 'context'>
): Record<string, string> => {
	if (!get(config)?.features?.enable_tool_servers) throw new Error('Tool servers are disabled');
	return {
		Authorization: `Bearer ${target.key.trim()}`,
		...(target.context.chatId ? { 'X-Session-Id': target.context.chatId } : {}),
		...(target.context.modelId ? { 'X-Terminal-Model-Id': target.context.modelId } : {})
	};
};

export const joinTerminalPath = (base: string, child: string) => {
	if (!child) return base;
	if (child.startsWith('/') || /^[A-Za-z]:[\\/]/.test(child)) return child;
	return `${base.replace(/[\\/]+$/, '')}/${child.replace(/^[\\/]+/, '')}`;
};

const basename = (path: string) =>
	path.replace(/\\/g, '/').split('/').filter(Boolean).at(-1) ?? path;

const hasHiddenPathPart = (path: string) =>
	path
		.replace(/\\/g, '/')
		.split('/')
		.some((part) => part.startsWith('.'));

export type TerminalServer = {
	template_id?: string;
	scope?: 'user' | 'chat' | 'model' | null;
	id: string;
	url: string;
	name: string;
	config?: {
		chat_uploads?: 'default' | 'filesystem';
		[key: string]: unknown;
	};
};

export const getTerminalServers = async (token: string): Promise<TerminalServer[]> => {
	if (!get(config)?.features?.enable_tool_servers) return [];
	const res = await fetch(`${WEBUI_API_BASE_URL}/terminals/`, {
		headers: {
			Authorization: `Bearer ${token}`
		}
	}).catch(() => null);
	if (!res || !res.ok) return [];
	return res.json().catch(() => []);
};

export const getCwd = async (target: TerminalTarget): Promise<TerminalCwd | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/cwd`;
	const headers: Record<string, string> = terminalHeaders(target);

	const res = await fetch(url, { headers }).catch(() => null);
	if (!res || !res.ok) return null;
	const json = await res.json().catch(() => null);
	if (!json) return null;
	return {
		cwd: json?.cwd ?? null,
		home: json?.home,
		root: json?.root
	};
};

export const listFiles = async (
	target: TerminalTarget,
	path: string = '/'
): Promise<TerminalFileList | null> => {
	// The endpoint uses `directory` as the query param name
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/list?directory=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = terminalHeaders(target);

	const res = await fetch(url, { headers })
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal listFiles error:', err);
			return null;
		});
	return res?.entries ? { entries: res.entries, writable: res.writable } : null;
};

export const searchFiles = async (
	target: TerminalTarget,
	query: string,
	path: string = '.',
	limit: number = 20,
	type: 'file' | 'directory' | 'any' = 'any',
	showHidden: boolean = false,
	signal?: AbortSignal
): Promise<TerminalFileSearchResponse | null> => {
	const headers: Record<string, string> = terminalHeaders(target);

	const searchParams = new URLSearchParams({
		query,
		path,
		limit: String(limit),
		type,
		show_hidden: String(showHidden)
	});
	const base = target.baseUrl.replace(/\/$/, '');
	const searchRes = await fetch(`${base}/files/search?${searchParams.toString()}`, {
		headers,
		signal
	}).catch(() => null);

	if (searchRes?.ok) {
		const json = await searchRes.json().catch(() => null);
		if (Array.isArray(json?.results)) return { results: json.results };
	}

	if (signal?.aborted) return null;

	const globParams = new URLSearchParams({
		pattern: query.trim() ? `*${query.trim()}*` : '*',
		path,
		type,
		max_results: String(limit)
	});
	const globRes = await fetch(`${base}/files/glob?${globParams.toString()}`, {
		headers,
		signal
	}).catch((err) => {
		if (!signal?.aborted) console.error('open-terminal searchFiles error:', err);
		return null;
	});
	if (!globRes?.ok) return null;

	const json = await globRes.json().catch(() => null);
	const root = json?.path ?? path;
	return {
		results: (json?.matches ?? [])
			.filter((item: FileEntry & { path: string }) => showHidden || !hasHiddenPathPart(item.path))
			.map((item: FileEntry & { path: string }) => ({
				path: joinTerminalPath(root, item.path),
				name: basename(item.path),
				type: item.type,
				size: item.size,
				modified: item.modified
			}))
	};
};

export const getFileMatches = async (
	target: TerminalTarget,
	query: string,
	path: string = '.',
	showHidden: boolean = false,
	offset: number = 0,
	signal?: AbortSignal
): Promise<TerminalFileMatchesResponse | null> => {
	const headers: Record<string, string> = terminalHeaders(target);

	const params = new URLSearchParams({
		query,
		path,
		show_hidden: String(showHidden),
		offset: String(offset)
	});
	const res = await fetch(
		`${target.baseUrl.replace(/\/$/, '')}/files/matches?${params.toString()}`,
		{
			headers,
			signal
		}
	).catch((err) => {
		if (err?.name !== 'AbortError') console.error('open-terminal getFileMatches error:', err);
		return null;
	});
	if (!res?.ok) return null;
	const json = await res.json().catch(() => null);
	return Array.isArray(json?.results) ? json : null;
};

export const readComparisonSource = async (
	target: TerminalTarget,
	path: string,
	signal: AbortSignal,
	size?: number
): Promise<string> => {
	checkSourceSize(size);
	const headers = terminalHeaders(target);

	const response = await fetch(
		`${target.baseUrl.replace(/\/$/, '')}/files/view?path=${encodeURIComponent(path)}`,
		{ headers, signal }
	).catch(() => {
		signal.throwIfAborted();
		throw new Error('Could not read file. Check your terminal connection.');
	});
	return readSourceResponse(response, signal);
};

export const readFile = async (
	target: TerminalTarget,
	path: string
): Promise<string | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/read?path=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = terminalHeaders(target);

	const res = await fetch(url, { headers }).catch((err) => {
		console.error('open-terminal readFile error:', err);
		return null;
	});

	if (!res || !res.ok) return null;

	const contentType = res.headers.get('content-type') ?? '';
	if (contentType.startsWith('image/') || contentType.startsWith('application/octet')) {
		// Binary — return a placeholder
		return `[Binary file: ${contentType}]`;
	}

	// Text files: endpoint returns JSON { path, total_lines, content }
	// Binary image files: endpoint returns raw bytes (handled above)
	const json = await res.json().catch(() => null);
	return json?.content ?? null;
};

export const listTerminalSkills = async (
	target: TerminalTarget | null
): Promise<TerminalSkill[]> => {
	if (!target) return [];

	const skills = await terminalRequest<TerminalSkill[]>(target, '/skills').catch(() => []);

	return (Array.isArray(skills) ? skills : []).map((skill) => ({
		...skill,
		is_active: true,
		source: 'terminal',
		terminal_path: skill.terminal_path ?? (skill as any).location ?? '',
		terminal_selector: target.selector,
		terminal_name: target.selector
	}));
};

export const downloadFileBlob = async (
	target: TerminalTarget,
	path: string,
	signal?: AbortSignal
): Promise<{ blob: Blob; filename: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/view?path=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = terminalHeaders(target);

	const res = await fetch(url, { headers, signal }).catch(() => null);

	if (!res || !res.ok) return null;

	const filename = path.split('/').pop() ?? 'file';
	const blob = await res.blob().catch(() => null);
	if (!blob) return null;
	return { blob, filename };
};

export const downloadFilePreview = async (
	target: TerminalTarget,
	path: string,
	signal?: AbortSignal
): Promise<{ blob: Blob; filename: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/view?path=${encodeURIComponent(path)}&preview=true`;
	const headers: Record<string, string> = terminalHeaders(target);

	const res = await fetch(url, { headers, signal }).catch(() => null);

	if (!res) return null;
	if (!res.ok) return null;

	const contentType = res.headers.get('content-type') ?? '';
	const filename = path.split('/').pop() ?? 'file';
	if (!contentType.includes('application/pdf')) return null;

	const blob = await res.blob().catch(() => null);
	if (!blob) return null;
	return { blob, filename };
};

export const archiveFromTerminal = async (
	target: TerminalTarget,
	paths: string[]
): Promise<{ blob: Blob; filename: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/archive`;
	const headers: Record<string, string> = {
		...terminalHeaders(target),
		'Content-Type': 'application/json'
	};

	const res = await fetch(url, {
		method: 'POST',
		headers,
		body: JSON.stringify({ paths })
	}).catch(() => null);

	if (!res || !res.ok) return null;

	const disposition = res.headers.get('content-disposition') ?? '';
	const match = disposition.match(/filename="?([^"]+)"?/);
	const filename = match?.[1] ?? 'download.zip';
	const blob = await res.blob().catch(() => null);
	if (!blob) return null;
	return { blob, filename };
};

export const uploadToTerminal = async (
	target: TerminalTarget,
	directory: string,
	file: File
): Promise<{ path: string; size: number } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/upload?directory=${encodeURIComponent(directory)}`;
	const body = new FormData();
	body.append('file', file);
	const headers: Record<string, string> = terminalHeaders(target);

	const res = await fetch(url, {
		method: 'POST',
		headers,
		body
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal uploadToTerminal error:', err);
			return null;
		});
	return res;
};

// ponytail: serialize new uploads in this page; cross-client races need server-side protection.
let newFileUploadQueue: Promise<void> = Promise.resolve();

export const uploadNewFileToTerminal = async (
	target: TerminalTarget,
	directory: string,
	file: File
): Promise<{ path: string; size: number } | null> => {
	const upload = newFileUploadQueue.then(async () => {
		const listing = await listFiles(target, directory);
		if (!listing) return null;

		const names = new Set(listing.entries.map((entry) => entry.name));
		const extensionIndex = file.name.startsWith('.') ? -1 : file.name.lastIndexOf('.');
		const stem = extensionIndex > 0 ? file.name.slice(0, extensionIndex) : file.name;
		const extension = extensionIndex > 0 ? file.name.slice(extensionIndex) : '';
		let name = file.name;
		for (let suffix = 1; names.has(name); suffix++) {
			name = `${stem} (${suffix})${extension}`;
		}

		const uploadFile =
			name === file.name
				? file
				: new File([file], name, { type: file.type, lastModified: file.lastModified });
		return uploadToTerminal(target, directory, uploadFile);
	});
	newFileUploadQueue = upload.then(
		() => undefined,
		() => undefined
	);
	return upload;
};

export const createDirectory = async (
	target: TerminalTarget,
	path: string
): Promise<{ path: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/mkdir`;
	const headers: Record<string, string> = {
		...terminalHeaders(target),
		'Content-Type': 'application/json'
	};

	const res = await fetch(url, {
		method: 'POST',
		headers,
		body: JSON.stringify({ path })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal createDirectory error:', err);
			return null;
		});
	return res;
};

export const deleteEntry = async (
	target: TerminalTarget,
	path: string
): Promise<{ path: string; type: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/delete?path=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = terminalHeaders(target);

	const res = await fetch(url, {
		method: 'DELETE',
		headers
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal deleteEntry error:', err);
			return null;
		});
	return res;
};

export const setCwd = async (
	target: TerminalTarget,
	path: string
): Promise<{ cwd: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/cwd`;
	const headers: Record<string, string> = {
		...terminalHeaders(target),
		'Content-Type': 'application/json'
	};

	const res = await fetch(url, {
		method: 'POST',
		headers,
		body: JSON.stringify({ path })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal setCwd error:', err);
			return null;
		});
	return res;
};

export const moveEntry = async (
	target: TerminalTarget,
	source: string,
	destination: string
): Promise<{ source: string; destination: string } | { error: string }> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/move`;
	const headers: Record<string, string> = {
		...terminalHeaders(target),
		'Content-Type': 'application/json'
	};

	const res = await fetch(url, {
		method: 'POST',
		headers,
		body: JSON.stringify({ source, destination })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal moveEntry error:', err);
			return { error: err?.detail ?? 'Move failed' };
		});
	return res;
};

export const getListeningPorts = async (
	target: TerminalTarget
): Promise<ListeningPort[]> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/ports`;
	const res = await fetch(url, {
		headers: {
			...terminalHeaders(target)
		}
	}).catch(() => null);
	if (!res || !res.ok) return [];
	const json = await res.json().catch(() => null);
	return json?.ports ?? [];
};

export const getPortProxyUrl = (baseUrl: string, port: number, path: string = ''): string => {
	if (!get(config)?.features?.enable_tool_servers) return '';
	return `${baseUrl.replace(/\/$/, '')}/proxy/${port}/${path}`;
};

// Notebook execution

export const createNotebookSession = async (
	target: TerminalTarget,
	path: string
): Promise<{ id: string; kernel: string; status: string } | { error: string }> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/notebooks`;
	const res = await fetch(url, {
		method: 'POST',
		headers: {
			...terminalHeaders(target),
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({ path })
	})
		.then(async (res) => {
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				return { error: body?.detail ?? `HTTP ${res.status}` };
			}
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal createNotebookSession error:', err);
			return { error: 'Connection failed' };
		});
	return res;
};

export const executeNotebookCell = async (
	target: TerminalTarget,
	sessionId: string,
	cellIndex: number,
	source?: string
): Promise<{ status: string; execution_count?: number; outputs: any[] } | { error: string }> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/notebooks/${sessionId}/execute`;
	const body: Record<string, any> = { cell_index: cellIndex };
	if (source !== undefined) body.source = source;

	const res = await fetch(url, {
		method: 'POST',
		headers: {
			...terminalHeaders(target),
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				return { error: body?.detail ?? `HTTP ${res.status}` };
			}
			return res.json();
		})
		.catch((err) => {
			console.error('open-terminal executeNotebookCell error:', err);
			return { error: 'Connection failed' };
		});
	return res;
};

export const stopNotebookSession = async (
	target: TerminalTarget,
	sessionId: string
): Promise<boolean> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/notebooks/${sessionId}`;
	const res = await fetch(url, {
		method: 'DELETE',
		headers: { ...terminalHeaders(target) }
	}).catch(() => null);
	return res?.ok ?? false;
};

export type TerminalDiffLine = {
	type: 'added' | 'removed' | 'context';
	oldNumber: number | null;
	newNumber: number | null;
	content: string;
	revisedContent?: string;
	segments: { text: string; changed: boolean }[];
};
export type TerminalComparisonRequest = {
	original: string;
	revised: string;
	ignore_whitespace: boolean;
};
export type TerminalComparison = {
	original: { name: string; path: string; notices: string[] };
	revised: { name: string; path: string; notices: string[] };
	additions: number;
	deletions: number;
	hunks: { header: string; lines: TerminalDiffLine[] }[];
};

export const compareFiles = async (
	target: TerminalTarget,
	request: TerminalComparisonRequest,
	signal?: AbortSignal
): Promise<TerminalComparison> => {
	const response = await fetch(`${target.baseUrl.replace(/\/$/, '')}/files/compare`, {
		method: 'POST',
		signal,
		headers: {
			...terminalHeaders(target),
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(request)
	});
	const body = await response.json().catch(() => null);
	if (
		response.status === 405 ||
		(response.status === 404 && ((!body?.detail && !body?.error) || body.detail === 'Not Found'))
	) {
		throw new Error(
			'File comparison is not available on this terminal. Update Open Terminal to use Compare.'
		);
	}
	if (!response.ok)
		throw new Error(
			typeof body?.detail === 'string'
				? body.detail
				: (body?.error ?? `Comparison failed (${response.status})`)
		);
	return body;
};

export async function templatesApi(path = '', method = 'GET', body?: unknown) {
	const response = await fetch(`${WEBUI_API_BASE_URL}/terminals/templates${path}`, {
		method,
		headers: {
			Authorization: `Bearer ${localStorage.token}`,
			...(body !== undefined ? { 'Content-Type': 'application/json' } : {})
		},
		...(body !== undefined ? { body: JSON.stringify(body) } : {})
	});
	const data = await response.json().catch(() => null);
	if (!response.ok)
		throw new Error(typeof data?.detail === 'string' ? data.detail : 'Terminal request failed');
	return data;
}
