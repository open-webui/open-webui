import { get } from 'svelte/store';
import { config } from '$lib/stores';
import type { TerminalConnection } from './index';

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
