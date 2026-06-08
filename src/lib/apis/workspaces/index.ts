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
	// Company custom: Team Workspaces V1 — current user's role in this workspace
	my_role?: 'manager' | 'member' | 'viewer' | null;
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
	// Company custom: Team Workspaces V1 — enriched from users table
	display_name?: string | null;
	email?: string | null;
};

export type WorkspaceChatResponse = {
	id: string;
	title: string;
	updated_at: number;
	created_at: number;
	last_read_at?: number | null;
	folder_id?: string | null;
};

export type WorkspaceFolderForm = {
	name?: string;
	data?: Record<string, any>;
	meta?: Record<string, any>;
	parent_id?: string | null;
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
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/`,
		{ method: 'POST', body: JSON.stringify(form) },
		token
	);

export const getWorkspaces = async (token: string): Promise<WorkspaceResponse[]> =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/`, { method: 'GET' }, token) ?? [];

export const getWorkspaceById = async (
	token: string,
	id: string
): Promise<WorkspaceResponse | null> =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/${id}`, { method: 'GET' }, token);

export const updateWorkspace = async (token: string, id: string, form: WorkspaceUpdateForm) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${id}`,
		{ method: 'PATCH', body: JSON.stringify(form) },
		token
	);

export const deleteWorkspace = async (token: string, id: string) =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/${id}`, { method: 'DELETE' }, token);

export const getWorkspaceDefaultModel = async (
	token: string,
	workspaceId: string
): Promise<{ model_id?: string | null }> =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/default-model`,
		{ method: 'GET' },
		token
	);

export const setWorkspaceDefaultModel = async (
	token: string,
	workspaceId: string,
	modelId: string | null
): Promise<{ model_id?: string | null }> =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/default-model`,
		{ method: 'PUT', body: JSON.stringify({ model_id: modelId }) },
		token
	);

// ── Members ──────────────────────────────────────────────────────────────────

export const getWorkspaceMembers = async (
	token: string,
	workspaceId: string
): Promise<WorkspaceMemberResponse[]> =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/members`, { method: 'GET' }, token) ??
	[];

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

export const getWorkspaceFolders = async (token: string, workspaceId: string) =>
	apiFetch(`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/folders`, { method: 'GET' }, token) ??
	[];

export const createWorkspaceFolder = async (
	token: string,
	workspaceId: string,
	folderForm: WorkspaceFolderForm
) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/folders`,
		{ method: 'POST', body: JSON.stringify(folderForm) },
		token
	);

export const getWorkspaceFolderById = async (
	token: string,
	workspaceId: string,
	folderId: string
) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/folders/${folderId}`,
		{ method: 'GET' },
		token
	);

export const updateWorkspaceFolderById = async (
	token: string,
	workspaceId: string,
	folderId: string,
	folderForm: WorkspaceFolderForm
) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/folders/${folderId}/update`,
		{ method: 'POST', body: JSON.stringify(folderForm) },
		token
	);

export const updateWorkspaceFolderParentIdById = async (
	token: string,
	workspaceId: string,
	folderId: string,
	parentId?: string | null
) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/folders/${folderId}/update/parent`,
		{ method: 'POST', body: JSON.stringify({ parent_id: parentId ?? null }) },
		token
	);

export const updateWorkspaceFolderIsExpandedById = async (
	token: string,
	workspaceId: string,
	folderId: string,
	isExpanded: boolean
) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/folders/${folderId}/update/expanded`,
		{ method: 'POST', body: JSON.stringify({ is_expanded: isExpanded }) },
		token
	);

export const getWorkspaceChatListByFolderId = async (
	token: string,
	workspaceId: string,
	folderId: string,
	page: number = 1
) =>
	apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/folders/${folderId}/chats?page=${page}`,
		{ method: 'GET' },
		token
	) ?? [];

export const deleteWorkspaceFolderById = async (
	token: string,
	workspaceId: string,
	folderId: string,
	deleteContents: boolean
) => {
	const searchParams = new URLSearchParams();
	searchParams.append('delete_contents', deleteContents ? 'true' : 'false');
	return apiFetch(
		`${WEBUI_API_BASE_URL}/workspaces/${workspaceId}/folders/${folderId}?${searchParams.toString()}`,
		{ method: 'DELETE' },
		token
	);
};
