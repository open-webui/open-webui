export type FileEntry = {
	name: string;
	type: 'file' | 'directory';
	size?: number;
	modified?: number;
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

export type TerminalFeatures = {
	terminal?: boolean;
};

export type TerminalFileRoot = {
	path: string;
	label: string;
};

export type TerminalCwd = {
	cwd: string | null;
	home?: string;
	root?: TerminalFileRoot;
};

import { WEBUI_API_BASE_URL } from '$lib/constants';

const bearerHeaders = (apiKey: string): Record<string, string> => ({
	Authorization: `Bearer ${apiKey.trim()}`
});

const joinTerminalPath = (base: string, child: string) => {
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
	id: string;
	url: string;
	name: string;
	contexts?: Record<string, false | { context_id?: string }>;
	config?: {
		chat_uploads?: 'default' | 'filesystem';
		[key: string]: unknown;
	};
};

export const getTerminalServers = async (token: string): Promise<TerminalServer[]> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/terminals/`, {
		headers: {
			Authorization: `Bearer ${token}`
		}
	}).catch(() => null);
	if (!res || !res.ok) return [];
	return res.json().catch(() => []);
};

export const getTerminalConfig = async (
	baseUrl: string,
	apiKey: string
): Promise<{ features: TerminalFeatures } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/api/config`;
	const res = await fetch(url, {
		headers: bearerHeaders(apiKey)
	}).catch(() => null);
	if (!res || !res.ok) return null;
	return res.json().catch(() => null);
};

export const getCwd = async (
	baseUrl: string,
	apiKey: string,
	sessionId?: string
): Promise<TerminalCwd | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/cwd`;
	const headers: Record<string, string> = bearerHeaders(apiKey);
	if (sessionId) headers['X-Session-Id'] = sessionId;
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
	baseUrl: string,
	apiKey: string,
	path: string = '/',
	sessionId?: string
): Promise<TerminalFileList | null> => {
	// The endpoint uses `directory` as the query param name
	const url = `${baseUrl.replace(/\/$/, '')}/files/list?directory=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = bearerHeaders(apiKey);
	if (sessionId) headers['X-Session-Id'] = sessionId;
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
	baseUrl: string,
	apiKey: string,
	query: string,
	path: string = '.',
	limit: number = 20,
	type: 'file' | 'directory' | 'any' = 'any',
	sessionId?: string,
	showHidden: boolean = false
): Promise<TerminalFileSearchResponse | null> => {
	const headers: Record<string, string> = bearerHeaders(apiKey);
	if (sessionId) headers['X-Session-Id'] = sessionId;

	const searchParams = new URLSearchParams({
		query,
		path,
		limit: String(limit),
		type,
		show_hidden: String(showHidden)
	});
	const base = baseUrl.replace(/\/$/, '');
	const searchRes = await fetch(`${base}/files/search?${searchParams.toString()}`, {
		headers
	}).catch(() => null);

	if (searchRes?.ok) {
		const json = await searchRes.json().catch(() => null);
		if (Array.isArray(json?.results)) return { results: json.results };
	}

	const globParams = new URLSearchParams({
		pattern: query.trim() ? `*${query.trim()}*` : '*',
		path,
		type,
		max_results: String(limit)
	});
	const globRes = await fetch(`${base}/files/glob?${globParams.toString()}`, {
		headers
	}).catch((err) => {
		console.error('open-terminal searchFiles error:', err);
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
	baseUrl: string,
	apiKey: string,
	query: string,
	path: string = '.',
	showHidden: boolean = false,
	offset: number = 0,
	sessionId?: string,
	signal?: AbortSignal
): Promise<TerminalFileMatchesResponse | null> => {
	const headers: Record<string, string> = bearerHeaders(apiKey);
	if (sessionId) headers['X-Session-Id'] = sessionId;

	const params = new URLSearchParams({
		query,
		path,
		show_hidden: String(showHidden),
		offset: String(offset)
	});
	const res = await fetch(`${baseUrl.replace(/\/$/, '')}/files/matches?${params.toString()}`, {
		headers,
		signal
	}).catch((err) => {
		if (err?.name !== 'AbortError') console.error('open-terminal getFileMatches error:', err);
		return null;
	});
	if (!res?.ok) return null;
	const json = await res.json().catch(() => null);
	return Array.isArray(json?.results) ? json : null;
};

export const readFile = async (
	baseUrl: string,
	apiKey: string,
	path: string,
	sessionId?: string
): Promise<string | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/read?path=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = bearerHeaders(apiKey);
	if (sessionId) headers['X-Session-Id'] = sessionId;
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

export const downloadFileBlob = async (
	baseUrl: string,
	apiKey: string,
	path: string,
	sessionId?: string
): Promise<{ blob: Blob; filename: string } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/view?path=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = bearerHeaders(apiKey);
	if (sessionId) headers['X-Session-Id'] = sessionId;
	const res = await fetch(url, { headers }).catch(() => null);

	if (!res || !res.ok) return null;

	const filename = path.split('/').pop() ?? 'file';
	const blob = await res.blob().catch(() => null);
	if (!blob) return null;
	return { blob, filename };
};

export const downloadFilePreview = async (
	baseUrl: string,
	apiKey: string,
	path: string,
	sessionId?: string
): Promise<{ blob: Blob; filename: string } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/view?path=${encodeURIComponent(path)}&preview=true`;
	const headers: Record<string, string> = bearerHeaders(apiKey);
	if (sessionId) headers['X-Session-Id'] = sessionId;
	const res = await fetch(url, { headers }).catch(() => null);

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
	baseUrl: string,
	apiKey: string,
	paths: string[],
	sessionId?: string
): Promise<{ blob: Blob; filename: string } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/archive`;
	const headers: Record<string, string> = {
		...bearerHeaders(apiKey),
		'Content-Type': 'application/json'
	};
	if (sessionId) headers['X-Session-Id'] = sessionId;
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
	baseUrl: string,
	apiKey: string,
	directory: string,
	file: File,
	sessionId?: string
): Promise<{ path: string; size: number } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/upload?directory=${encodeURIComponent(directory)}`;
	const body = new FormData();
	body.append('file', file);
	const headers: Record<string, string> = bearerHeaders(apiKey);
	if (sessionId) headers['X-Session-Id'] = sessionId;
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

export const createDirectory = async (
	baseUrl: string,
	apiKey: string,
	path: string,
	sessionId?: string
): Promise<{ path: string } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/mkdir`;
	const headers: Record<string, string> = {
		...bearerHeaders(apiKey),
		'Content-Type': 'application/json'
	};
	if (sessionId) headers['X-Session-Id'] = sessionId;
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
	baseUrl: string,
	apiKey: string,
	path: string,
	sessionId?: string
): Promise<{ path: string; type: string } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/delete?path=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = bearerHeaders(apiKey);
	if (sessionId) headers['X-Session-Id'] = sessionId;
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
	baseUrl: string,
	apiKey: string,
	path: string,
	sessionId?: string
): Promise<{ cwd: string } | null> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/cwd`;
	const headers: Record<string, string> = {
		...bearerHeaders(apiKey),
		'Content-Type': 'application/json'
	};
	if (sessionId) headers['X-Session-Id'] = sessionId;
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
	baseUrl: string,
	apiKey: string,
	source: string,
	destination: string,
	sessionId?: string
): Promise<{ source: string; destination: string } | { error: string }> => {
	const url = `${baseUrl.replace(/\/$/, '')}/files/move`;
	const headers: Record<string, string> = {
		...bearerHeaders(apiKey),
		'Content-Type': 'application/json'
	};
	if (sessionId) headers['X-Session-Id'] = sessionId;
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
	baseUrl: string,
	apiKey: string
): Promise<ListeningPort[]> => {
	const url = `${baseUrl.replace(/\/$/, '')}/ports`;
	const res = await fetch(url, {
		headers: bearerHeaders(apiKey)
	}).catch(() => null);
	if (!res || !res.ok) return [];
	const json = await res.json().catch(() => null);
	return json?.ports ?? [];
};

export const getPortProxyUrl = (baseUrl: string, port: number, path: string = ''): string => {
	return `${baseUrl.replace(/\/$/, '')}/proxy/${port}/${path}`;
};

// ---------------------------------------------------------------------------
// Notebook execution
// ---------------------------------------------------------------------------

export const createNotebookSession = async (
	baseUrl: string,
	apiKey: string,
	path: string
): Promise<{ id: string; kernel: string; status: string } | { error: string }> => {
	const url = `${baseUrl.replace(/\/$/, '')}/notebooks`;
	const res = await fetch(url, {
		method: 'POST',
		headers: {
			...bearerHeaders(apiKey),
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
	baseUrl: string,
	apiKey: string,
	sessionId: string,
	cellIndex: number,
	source?: string
): Promise<{ status: string; execution_count?: number; outputs: any[] } | { error: string }> => {
	const url = `${baseUrl.replace(/\/$/, '')}/notebooks/${sessionId}/execute`;
	const body: Record<string, any> = { cell_index: cellIndex };
	if (source !== undefined) body.source = source;

	const res = await fetch(url, {
		method: 'POST',
		headers: {
			...bearerHeaders(apiKey),
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
	baseUrl: string,
	apiKey: string,
	sessionId: string
): Promise<boolean> => {
	const url = `${baseUrl.replace(/\/$/, '')}/notebooks/${sessionId}`;
	const res = await fetch(url, {
		method: 'DELETE',
		headers: bearerHeaders(apiKey)
	}).catch(() => null);
	return res?.ok ?? false;
};
