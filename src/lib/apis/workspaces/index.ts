// Company custom: Team Workspaces V1
import { WEBUI_API_BASE_URL } from '$lib/constants';

// ── Types ────────────────────────────────────────────────────────────────────

export type WorkspaceForm = {
	name: string;
	description?: string | null;
	meta?: Record<string, any> | null;
};

export type WorkspaceUpdateForm = {
	name?: string;
	description?: string | null;
	meta?: Record<string, any> | null;
};

export type WorkspaceResponse = {
	id: string;
	user_id: string;
	name: string;
	description?: string | null;
	meta?: Record<string, any> | null;
	created_at: number;
	updated_at: number;
};

export type WorkspaceMemberForm = {
	user_id: string;
	role: 'manager' | 'member' | 'viewer';
};

export type WorkspaceMemberUpdateForm = {
	role: 'manager' | 'member' | 'viewer';
};

export type WorkspaceMemberResponse = {
	id: string;
	workspace_id: string;
	user_id: string;
	role: 'manager' | 'member' | 'viewer';
	created_at: number;
	updated_at: number;
};

export type WorkspaceChatResponse = {
	id: string;
	title: string;
	updated_at: number;
	created_at: number;
	last_read_at?: number | null;
};

// ── Helpers ──────────────────────────────────────────────────────────────────

const apiFetch = async (url: string, options: RequestInit, token: string) => {
	let error = null;

	const res = await fetch(url, {
		...options,
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`,
			...(options.headers ?? {})
		}
	})
		.then(async (r) => {
			if (!r.ok) throw await r.json();
			return r.json();
		})
		.catch((err) => {
			error = err?.detail ?? err?.message ?? String(err);
			console.error(err);
			return null;
		});

	if (error) throw error;
	return res;
};

// ── Workspace CRUD ────────────────────────────────────────────────────────────

export const createWorkspace = async (token: string, form: WorkspaceForm) =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/`, { method: 'POST', body: JSON.stringify(form) }, token);

export const getWorkspaces = async (token: string): Promise<WorkspaceResponse[]> =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/`, { method: 'GET' }, token) ?? [];

export const getWorkspaceById = async (token: string, id: string): Promise<WorkspaceResponse | null> =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/${id}`, { method: 'GET' }, token);

export const updateWorkspace = async (token: string, id: string, form: WorkspaceUpdateForm) =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/${id}`, { method: 'PATCH', body: JSON.stringify(form) }, token);

export const deleteWorkspace = async (token: string, id: string) =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/${id}`, { method: 'DELETE' }, token);

// ── Members ──────────────────────────────────────────────────────────────────

export const getWorkspaceMembers = async (
	token: string,
	workspaceId: string
): Promise<WorkspaceMemberResponse[]> =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/members`, { method: 'GET' }, token) ?? [];

export const addWorkspaceMember = async (
	token: string,
	workspaceId: string,
	form: WorkspaceMemberForm
) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/members`,
		{ method: 'POST', body: JSON.stringify(form) },
		token
	);

export const updateWorkspaceMember = async (
	token: string,
	workspaceId: string,
	userId: string,
	form: WorkspaceMemberUpdateForm
) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/members/${userId}`,
		{ method: 'PATCH', body: JSON.stringify(form) },
		token
	);

export const removeWorkspaceMember = async (token: string, workspaceId: string, userId: string) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/members/${userId}`,
		{ method: 'DELETE' },
		token
	);

// ── Chats ────────────────────────────────────────────────────────────────────

export const getWorkspaceChats = async (
	token: string,
	workspaceId: string,
	page?: number
): Promise<WorkspaceChatResponse[]> => {
	const params = page != null ? `?page=${page}` : '';
	return (
		apiFetch(
			`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/chats${params}`,
			{ method: 'GET' },
			token
		) ?? []
	);
};

export const createWorkspaceChat = async (token: string, workspaceId: string, chat: object) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/chats`,
		{ method: 'POST', body: JSON.stringify({ chat }) },
		token
	);
