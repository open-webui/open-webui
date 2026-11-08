import { get } from 'svelte/store';
import { config } from '$lib/stores';
import {
	joinTerminalPath,
	terminalRequest,
	type TerminalConnection,
	type TerminalProcessOutput
} from './index';

export type GitFile = {
	path: string;
	original_path?: string;
	status: string;
	staged: boolean;
	unstaged: boolean;
	additions: number;
	deletions: number;
	binary?: boolean;
};
export type GitStatus = {
	is_repo: boolean;
	root?: string;
	branch: string;
	head?: string;
	upstream?: string;
	remote_url?: string;
	ahead: number;
	behind: number;
	files: GitFile[];
};
export type GitCommit = {
	hash: string;
	short_hash: string;
	author: string;
	date: string;
	message: string;
};
export type GitBranch = { name: string; current: boolean; upstream: string; is_local?: boolean };

export function gitRemoteWebUrl(remote = ''): string {
	const scp = remote.match(/^[^/@:\s]+@([^/:\s]+):(.+)$/);
	try {
		const url = new URL(scp ? `https://${scp[1]}/${scp[2]}` : remote);
		if (url.protocol === 'ssh:') {
			return new URL(`https://${url.hostname}${url.pathname.replace(/\.git\/?$/, '')}`).href;
		}
		if (!['http:', 'https:'].includes(url.protocol)) return '';
		url.username = url.password = url.search = url.hash = '';
		url.pathname = url.pathname.replace(/\.git\/?$/, '');
		return url.href;
	} catch {
		return '';
	}
}

export async function gitRequest<T>(
	connection: TerminalConnection,
	chatId: string | null,
	directory: string,
	operation: string,
	params: Record<string, string> = {},
	body?: Record<string, unknown>,
	method = body ? 'POST' : 'GET'
): Promise<T> {
	if (!get(config)?.features?.enable_tool_servers) throw new Error('Tool servers are disabled');
	const query = new URLSearchParams({ root: directory, ...params });
	const response = await fetch(`${connection.baseUrl}/git/${operation}?${query}`, {
		method,
		headers: {
			Authorization: `Bearer ${connection.key.trim()}`,
			...(chatId ? { 'X-Session-Id': chatId } : {}),
			...(body ? { 'Content-Type': 'application/json' } : {})
		},
		...(body ? { body: JSON.stringify({ root: directory, ...body }) } : {})
	});
	if (!response.ok) {
		const error = await response.json().catch(() => null);
		if (response.status === 404 && error?.detail === 'Not Found') {
			throw new Error(
				'Git support is unavailable on this connection. Update and restart Open Terminal.'
			);
		}
		throw new Error(
			typeof error?.detail === 'string'
				? error.detail
				: typeof error?.error === 'string'
					? error.error
					: `Git request failed (${response.status})`
		);
	}
	return response.json();
}

export function gitAction<T>(
	connection: TerminalConnection,
	chatId: string | null,
	directory: string,
	action: string,
	fields: Record<string, unknown>
) {
	let operation = action;
	let method = 'POST';
	let body: Record<string, unknown> = { ...fields };
	if (['stage', 'unstage', 'discard'].includes(action)) body = { files: fields.paths };
	if (action === 'branch') body = { name: fields.branch };
	if (action === 'worktree') {
		operation = 'worktrees';
		body = { branch: fields.branch, path: fields.target };
	}
	if (action === 'publish') {
		operation = 'push';
		body = { set_upstream: true };
	}
	if (action === 'rename_branch') {
		operation = 'branch';
		method = 'PATCH';
		body = { old_name: fields.branch, new_name: fields.target };
	}
	if (action === 'delete_branch') {
		operation = 'branch';
		method = 'DELETE';
		body = { name: fields.branch };
	}
	return gitRequest<T>(connection, chatId, directory, operation, {}, body, method);
}

const repositoryFolderName = (url: string) =>
	url
		.trim()
		.replace(/\/+$/, '')
		.split(/[/:]/)
		.pop()
		?.replace(/\.git$/, '') ?? '';

export async function cloneRepository(
	connection: Pick<TerminalConnection, 'baseUrl' | 'key'>,
	chatId: string | null,
	directory: string,
	url: string,
	signal?: AbortSignal
): Promise<string> {
	url = url.trim();
	const name = repositoryFolderName(url);
	if (
		/[\s\x00-\x1f\x7f]/.test(url) ||
		!(/^(https?|ssh):\/\/[^/]+\/.+/.test(url) || /^[\w.-]+@[\w.-]+:.+/.test(url))
	)
		throw new Error('Enter an HTTP(S) or SSH repository URL');
	if (!name || name === '.' || name === '..' || /[/\\\x00-\x1f\x7f]/.test(name))
		throw new Error('Repository URL must include a valid repository name');
	if (!directory) throw new Error('Choose a destination directory');

	const quote = (value: string) => `'${value.replaceAll("'", "'\\''")}'`;
	let result = await terminalRequest<TerminalProcessOutput>(
		connection,
		chatId,
		'/execute?wait=1&tail=20',
		{
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				command: `git clone -- ${quote(url)} ${quote(`./${name}`)}`,
				cwd: directory,
				env: {
					GIT_TERMINAL_PROMPT: '0',
					GIT_SSH_COMMAND: 'ssh -oBatchMode=yes -oStrictHostKeyChecking=yes -oConnectTimeout=15'
				}
			}),
			signal
		}
	);
	while (result.status === 'running') {
		result = await terminalRequest<TerminalProcessOutput>(
			connection,
			chatId,
			`/execute/${encodeURIComponent(result.id)}/status?wait=1&tail=20`,
			{ signal }
		);
	}
	if (result.status !== 'done' || result.exit_code !== 0) {
		throw new Error(
			result.output
				?.map((entry) => entry.data)
				.join('')
				.trim() || 'Failed to clone repository'
		);
	}
	return joinTerminalPath(directory, name);
}
