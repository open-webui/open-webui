import { get } from 'svelte/store';
import { config } from '$lib/stores';
import { checkSourceSize, readSourceResponse } from './sourceText';
// The same attachment is used by @mentions, machine uploads, and Files-pane requests.
export type FilesystemFile = {
	type: 'filesystem';
	id: string;
	path: string;
	url: string;
	name: string;
	status: string;
	size?: number;
	modified?: number;
	machine_id?: string;
	session_id?: string | null;
};
export const filesystemFile = (
	entry: { path: string; name: string; size?: number; modified?: number },
	machineId: string,
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
	machine_id: machineId,
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

export type MachineFileList = {
	entries: FileEntry[];
	writable?: boolean;
};

export type MachineFileSearchResult = FileEntry & {
	path: string;
};

export type MachineFileSearchResponse = {
	results: MachineFileSearchResult[];
};

export type MachineContentMatch = {
	line: number;
	column: number;
	text: string;
};

export type MachineFileMatch = {
	path: string;
	relative_path: string;
	name: string;
	type: 'file' | 'directory';
	name_match: boolean;
	content_matches: MachineContentMatch[];
};

export type MachineFileMatchesResponse = {
	results: MachineFileMatch[];
	next_offset: number | null;
};

export type ListeningPort = {
	port: number;
	pid: number | null;
	process: string | null;
};

export type MachineSystemInfo = {
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
	/** Present when the machine has a setup script. */
	setup?: {
		status: 'running' | 'ok' | 'failed';
		exit_code?: number;
		log_tail?: string;
	};
};

export type MachineFeatures = {
	agents?: boolean;
	terminal?: boolean;
	browser?: boolean;
	desktop?: boolean;
	git?: boolean;
	events?: boolean;
};

// Missing flags mean unsupported; never probe a new endpoint on an older server.
export async function getMachineFeatures(
	target: Pick<MachineTarget, 'baseUrl' | 'key' | 'context'>,
	signal?: AbortSignal
): Promise<MachineFeatures> {
	try {
		const result = await machineRequest<{ features?: MachineFeatures }>(target, '/api/config', {
			signal
		});
		return result.features ?? {};
	} catch {
		return {};
	}
}

export type MachineFileRoot = {
	path: string;
	label: string;
};

export type MachineCwd = {
	cwd: string | null;
	home?: string;
	root?: MachineFileRoot;
};

export type MachineSkill = {
	id: string;
	name: string;
	description: string;
	is_active: boolean;
	source: 'machine';
	machine_path: string;
	machine_selector: string;
	machine_name?: string;
};

import { WEBUI_API_BASE_URL } from '$lib/constants';

export type MachineTarget = {
	selector: string;
	baseUrl: string;
	key: string;
	system: boolean;
	/** userId names another person's instance; only someone who manages the machine may reach it. */
	context: { userId?: string | null; chatId: string | null; modelId: string | null };
};
export type MachineProcess = {
	id: string;
	command: string;
	status: 'running' | 'done' | 'killed';
	exit_code: number | null;
};
export type MachineProcessOutput = MachineProcess & {
	output: { type: string; data: string }[];
	next_offset: number;
	truncated: boolean;
};

export const resolveMachineTarget = (
	selector: string | null,
	servers: any[],
	token: string,
	context: Partial<MachineTarget['context']> = {}
): MachineTarget | null => {
	if (!get(config)?.features?.enable_tool_servers || !selector) return null;
	const server = servers.find((server) => server.id === selector);
	if (server) {
		if (server.scope === 'model' && !context.modelId) return null;
		return {
			selector,
			baseUrl: `${WEBUI_API_BASE_URL}/machines/${encodeURIComponent(selector)}`,
			context: {
				userId: context.userId ?? null,
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
	return null;
};

export class MachineRequestError extends Error {
	constructor(
		message: string,
		public status: number
	) {
		super(message);
		this.name = 'MachineRequestError';
	}
}

export const machineRequest = async <T>(
	target: Pick<MachineTarget, 'baseUrl' | 'key' | 'context'>,
	path: string,
	options: RequestInit = {}
): Promise<T> => {
	if (!get(config)?.features?.enable_tool_servers)
		throw new MachineRequestError('Tool servers are disabled', 403);
	const response = await fetch(`${target.baseUrl}${path}`, {
		...options,
		headers: {
			...machineHeaders(target),
			...options.headers
		}
	});
	if (!response.ok) {
		const body = await response.json().catch(() => null);
		throw new MachineRequestError(
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

export const machineHeaders = (
	target: Pick<MachineTarget, 'key' | 'context'>
): Record<string, string> => {
	if (!get(config)?.features?.enable_tool_servers) throw new Error('Tool servers are disabled');
	return {
		Authorization: `Bearer ${target.key.trim()}`,
		...(target.context.userId ? { 'X-Terminal-User-Id': target.context.userId } : {}),
		...(target.context.chatId ? { 'X-Session-Id': target.context.chatId } : {}),
		...(target.context.modelId ? { 'X-Terminal-Model-Id': target.context.modelId } : {})
	};
};

export const joinMachinePath = (base: string, child: string) => {
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

export type MachineServer = {
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

export const getMachines = async (token: string): Promise<MachineServer[]> => {
	if (!get(config)?.features?.enable_tool_servers) return [];
	const res = await fetch(`${WEBUI_API_BASE_URL}/machines/`, {
		headers: {
			Authorization: `Bearer ${token}`
		}
	}).catch(() => null);
	if (!res || !res.ok) return [];
	return res.json().catch(() => []);
};

export const getCwd = async (target: MachineTarget): Promise<MachineCwd | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/cwd`;
	const headers: Record<string, string> = machineHeaders(target);

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
	target: MachineTarget,
	path: string = '/'
): Promise<MachineFileList | null> => {
	// The endpoint uses `directory` as the query param name
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/list?directory=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = machineHeaders(target);

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
	target: MachineTarget,
	query: string,
	path: string = '.',
	limit: number = 20,
	type: 'file' | 'directory' | 'any' = 'any',
	showHidden: boolean = false,
	signal?: AbortSignal
): Promise<MachineFileSearchResponse | null> => {
	const headers: Record<string, string> = machineHeaders(target);

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
				path: joinMachinePath(root, item.path),
				name: basename(item.path),
				type: item.type,
				size: item.size,
				modified: item.modified
			}))
	};
};

export const getFileMatches = async (
	target: MachineTarget,
	query: string,
	path: string = '.',
	showHidden: boolean = false,
	offset: number = 0,
	signal?: AbortSignal
): Promise<MachineFileMatchesResponse | null> => {
	const headers: Record<string, string> = machineHeaders(target);

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
	target: MachineTarget,
	path: string,
	signal: AbortSignal,
	size?: number
): Promise<string> => {
	checkSourceSize(size);
	const headers = machineHeaders(target);

	const response = await fetch(
		`${target.baseUrl.replace(/\/$/, '')}/files/view?path=${encodeURIComponent(path)}`,
		{ headers, signal }
	).catch(() => {
		signal.throwIfAborted();
		throw new Error('Could not read file. Check the machine connection.');
	});
	return readSourceResponse(response, signal);
};

export const readFile = async (target: MachineTarget, path: string): Promise<string | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/read?path=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = machineHeaders(target);

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

export const listMachineSkills = async (target: MachineTarget | null): Promise<MachineSkill[]> => {
	if (!target) return [];

	const skills = await machineRequest<MachineSkill[]>(target, '/skills').catch(() => []);

	return (Array.isArray(skills) ? skills : []).map((skill) => ({
		...skill,
		is_active: true,
		source: 'machine',
		machine_path:
			skill.machine_path ?? (skill as any).terminal_path ?? (skill as any).location ?? '',
		machine_selector: target.selector,
		machine_name: target.selector
	}));
};

export const downloadFileBlob = async (
	target: MachineTarget,
	path: string,
	signal?: AbortSignal
): Promise<{ blob: Blob; filename: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/view?path=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = machineHeaders(target);

	const res = await fetch(url, { headers, signal }).catch(() => null);

	if (!res || !res.ok) return null;

	const filename = path.split('/').pop() ?? 'file';
	const blob = await res.blob().catch(() => null);
	if (!blob) return null;
	return { blob, filename };
};

export const downloadFilePreview = async (
	target: MachineTarget,
	path: string,
	signal?: AbortSignal
): Promise<{ blob: Blob; filename: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/view?path=${encodeURIComponent(path)}&preview=true`;
	const headers: Record<string, string> = machineHeaders(target);

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

export const archiveFromMachine = async (
	target: MachineTarget,
	paths: string[]
): Promise<{ blob: Blob; filename: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/archive`;
	const headers: Record<string, string> = {
		...machineHeaders(target),
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

export const uploadToMachine = async (
	target: MachineTarget,
	directory: string,
	file: File
): Promise<{ path: string; size: number } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/upload?directory=${encodeURIComponent(directory)}`;
	const body = new FormData();
	body.append('file', file);
	const headers: Record<string, string> = machineHeaders(target);

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
			console.error('open-terminal uploadToMachine error:', err);
			return null;
		});
	return res;
};

// ponytail: serialize new uploads in this page; cross-client races need server-side protection.
let newFileUploadQueue: Promise<void> = Promise.resolve();

export const uploadNewFileToMachine = async (
	target: MachineTarget,
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
		return uploadToMachine(target, directory, uploadFile);
	});
	newFileUploadQueue = upload.then(
		() => undefined,
		() => undefined
	);
	return upload;
};

export const createDirectory = async (
	target: MachineTarget,
	path: string
): Promise<{ path: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/mkdir`;
	const headers: Record<string, string> = {
		...machineHeaders(target),
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
	target: MachineTarget,
	path: string
): Promise<{ path: string; type: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/delete?path=${encodeURIComponent(path)}`;
	const headers: Record<string, string> = machineHeaders(target);

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
	target: MachineTarget,
	path: string
): Promise<{ cwd: string } | null> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/cwd`;
	const headers: Record<string, string> = {
		...machineHeaders(target),
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
	target: MachineTarget,
	source: string,
	destination: string
): Promise<{ source: string; destination: string } | { error: string }> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/files/move`;
	const headers: Record<string, string> = {
		...machineHeaders(target),
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

export const getListeningPorts = async (target: MachineTarget): Promise<ListeningPort[]> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/ports`;
	const res = await fetch(url, {
		headers: {
			...machineHeaders(target)
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
	target: MachineTarget,
	path: string
): Promise<{ id: string; kernel: string; status: string } | { error: string }> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/notebooks`;
	const res = await fetch(url, {
		method: 'POST',
		headers: {
			...machineHeaders(target),
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
	target: MachineTarget,
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
			...machineHeaders(target),
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
	target: MachineTarget,
	sessionId: string
): Promise<boolean> => {
	const url = `${target.baseUrl.replace(/\/$/, '')}/notebooks/${sessionId}`;
	const res = await fetch(url, {
		method: 'DELETE',
		headers: { ...machineHeaders(target) }
	}).catch(() => null);
	return res?.ok ?? false;
};

export type MachineDiffLine = {
	type: 'added' | 'removed' | 'context';
	oldNumber: number | null;
	newNumber: number | null;
	content: string;
	revisedContent?: string;
	segments: { text: string; changed: boolean }[];
};
export type MachineComparisonRequest = {
	original: string;
	revised: string;
	ignore_whitespace: boolean;
};
export type MachineComparison = {
	original: { name: string; path: string; notices: string[] };
	revised: { name: string; path: string; notices: string[] };
	additions: number;
	deletions: number;
	hunks: { header: string; lines: MachineDiffLine[] }[];
};

export const compareFiles = async (
	target: MachineTarget,
	request: MachineComparisonRequest,
	signal?: AbortSignal
): Promise<MachineComparison> => {
	const response = await fetch(`${target.baseUrl.replace(/\/$/, '')}/files/compare`, {
		method: 'POST',
		signal,
		headers: {
			...machineHeaders(target),
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
	const response = await fetch(`${WEBUI_API_BASE_URL}/machines/templates${path}`, {
		method,
		headers: {
			Authorization: `Bearer ${localStorage.token}`,
			...(body !== undefined ? { 'Content-Type': 'application/json' } : {})
		},
		...(body !== undefined ? { body: JSON.stringify(body) } : {})
	});
	const data = await response.json().catch(() => null);
	if (!response.ok)
		throw new Error(typeof data?.detail === 'string' ? data.detail : 'Machine request failed');
	return data;
}

// Managed machines: Open WebUI installs and runs Open Terminal on them, over SSH or on
// this computer (experimental).

export type SSHTarget = { host: string; port: number; username: string };

/** Install state shared by both kinds (`connection.ssh` or `connection.local`). */
export type ManagedMachineInfo = {
	root?: string;
	start_dir?: string; // where terminal sessions start; empty is home
	version?: string;
	requested_version?: string; // 'latest' or an exact version
	deps?: string[]; // installed with the machine by `open-terminal install-deps`, by name
	packages?: string[]; // and extra apt packages
	status?: 'installing' | 'ready' | 'error';
	error?: string | null;
	warning?: string | null; // the last install could not add the packages
};

export type SSHMachineInfo = ManagedMachineInfo &
	SSHTarget & {
		host_key: string;
		transport?: 'streamlocal' | 'stdio';
	};

/** Parse `ssh://user@host[:port]`. Returns null for anything else. */
export const parseSSHUrl = (value: string): SSHTarget | null => {
	const match = value
		.trim()
		.match(
			/^ssh:\/\/([a-z_][a-z0-9_.-]{0,31})@(\[[0-9a-f:.]+\]|[A-Za-z0-9.-]+)(?::(\d{1,5}))?\/?$/i
		);
	if (!match) return null;
	const port = match[3] ? Number(match[3]) : 22;
	if (port < 1 || port > 65535) return null;
	return { username: match[1], host: match[2].replace(/^\[|\]$/g, ''), port };
};

export const formatSSHUrl = ({ username, host, port }: SSHTarget) =>
	`ssh://${username}@${host.includes(':') ? `[${host}]` : host}${port === 22 ? '' : `:${port}`}`;

const managedMachineRequest = async <T>(
	token: string,
	path: string,
	method = 'GET',
	body?: unknown
): Promise<T> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/machines${path}`, {
		method,
		headers: {
			Authorization: `Bearer ${token}`,
			...(body !== undefined ? { 'Content-Type': 'application/json' } : {})
		},
		...(body !== undefined ? { body: JSON.stringify(body) } : {})
	});
	const data = await res.json().catch(() => null);
	if (!res.ok) {
		const detail = data?.detail;
		throw new Error(
			typeof detail === 'string'
				? detail
				: Array.isArray(detail)
					? detail.map((item) => item?.msg ?? String(item)).join('; ')
					: res.statusText
		);
	}
	return data as T;
};

const managedPath = (id: string, action = '') => `/managed/${encodeURIComponent(id)}${action}`;

/** Fetch the machine's host key without logging in, so the admin can confirm it. */
export const probeSSHMachine = (token: string, target: SSHTarget) =>
	managedMachineRequest<{ host_key: string; fingerprint: string }>(
		token,
		'/ssh/probe',
		'POST',
		target
	);

/** Create the machine's id and the key Open WebUI will log in with. */
export const createSSHKeypair = (token: string) =>
	managedMachineRequest<{ id: string; public_key: string }>(token, '/ssh/keypair', 'POST');

/** Log in once with a password or private key to add Open WebUI's key. Neither is stored. */
export const installSSHKey = (
	token: string,
	form: SSHTarget & {
		host_key: string;
		id: string;
		public_key: string;
		password?: string;
		private_key?: string;
		passphrase?: string;
	}
) => managedMachineRequest<{ status: boolean }>(token, '/ssh/authorize', 'POST', form);

/** Start installing Open Terminal. Progress arrives as `machines:progress` socket events. */
export const installSSHMachine = (
	token: string,
	form: SSHTarget & {
		host_key: string;
		id: string;
		name: string;
		version?: string;
		start_dir?: string;
		deps?: string[];
		packages?: string[];
	}
) => managedMachineRequest<{ id: string; status: string }>(token, '/ssh', 'POST', form);

/** Where sessions on this computer start by default, and whether it is already added. */
export const getLocalMachineDefaults = (token: string) =>
	managedMachineRequest<{ start_dir: string; added: boolean }>(token, '/local');

/** Install Open Terminal on the computer Open WebUI runs on (experimental). Empty start_dir: the project folder Open WebUI picks. */
export const installLocalMachine = (
	token: string,
	form: { id: string; name?: string; version?: string; start_dir?: string }
) => managedMachineRequest<{ id: string; status: string }>(token, '/local', 'POST', form);

/** Install the machine's Open Terminal again: `version` is 'latest' or an exact version. Omitted fields keep the current choice. */
export const upgradeMachine = (
	token: string,
	id: string,
	form?: { version?: string; deps?: string[]; packages?: string[] }
) =>
	managedMachineRequest<{ id: string; status: string }>(
		token,
		managedPath(id, '/upgrade'),
		'POST',
		form
	);

/** Install system packages on the machine now. Progress arrives as `machines:progress` socket events. */
export const installMachinePackages = (
	token: string,
	id: string,
	form: { deps: string[]; packages: string[] }
) =>
	managedMachineRequest<{ id: string; status: string }>(
		token,
		managedPath(id, '/install'),
		'POST',
		form
	);

/** Change where terminal sessions start, then restart Open Terminal there. */
export const setMachineStartDir = (token: string, id: string, startDir: string) =>
	managedMachineRequest<{ status: boolean }>(token, managedPath(id, '/directory'), 'POST', {
		start_dir: startDir
	});

export const restartMachine = (token: string, id: string) =>
	managedMachineRequest<{ status: boolean }>(token, managedPath(id, '/restart'), 'POST');

export const getMachineLogs = (token: string, id: string, lines = 200) =>
	managedMachineRequest<{ logs: string }>(token, managedPath(id, `/logs?lines=${lines}`));

/** Uninstall Open Terminal and remove the machine. `force` removes it even if it is unreachable. */
export const removeMachine = (token: string, id: string, force = false) =>
	managedMachineRequest<{ status: boolean }>(
		token,
		managedPath(id, force ? '?force=true' : ''),
		'DELETE'
	);
