import { WEBUI_API_BASE_URL } from '$lib/constants';

type FolderForm = {
	name?: string;
	data?: Record<string, any>;
	meta?: Record<string, any>;
	parent_id?: string | null;
};

export const createNewFolder = async (token: string, folderForm: FolderForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(folderForm)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFolders = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFolderById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				throw Object.assign(new Error(body.detail ?? res.statusText), { status: res.status });
			}
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFolderById = async (token: string, id: string, folderForm: FolderForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(folderForm)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFolderIsExpandedById = async (
	token: string,
	id: string,
	isExpanded: boolean
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}/update/expanded`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			is_expanded: isExpanded
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFolderParentIdById = async (token: string, id: string, parentId?: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}/update/parent`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			parent_id: parentId
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteFolderById = async (token: string, id: string, deleteContents: boolean) => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('delete_contents', deleteContents ? 'true' : 'false');

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}?${searchParams.toString()}`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const markFolderChatsReadById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}/read`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFolderAccessById = async (
	token: string,
	id: string,
	accessGrants: any[],
	shareMode?: 'continue' | null
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${id}/access/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ access_grants: accessGrants, share_mode: shareMode })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSharedFolders = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/shared`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export type ChatParticipant = {
	id: string;
	name: string | null;
};

export const getSharedFolderChats = async (
	token: string,
	folderId: string,
	params: Omit<import('$lib/stores/folderStates').FolderChatQuery, 'page'> & {
		page?: number | null;
	} = {}
) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (params.page !== undefined && params.page !== null) {
		searchParams.append('page', `${params.page}`);
	}
	if (params.sortBy) {
		searchParams.append('sort_by', params.sortBy);
	}
	if (params.sortDir) {
		searchParams.append('sort_dir', params.sortDir);
	}
	if (params.workspace) searchParams.set('workspace', 'true');
	if (params.search?.trim()) searchParams.set('search', params.search.trim());
	for (const tag of params.tagIds ?? []) searchParams.append('tag_ids', tag);
	for (const id of params.userIds ?? []) searchParams.append('user_ids', id);
	for (const status of [params.status ?? []].flat()) searchParams.append('status', status);
	if (params.activity) searchParams.set('activity', params.activity);
	if (params.updatedAtGte !== undefined)
		searchParams.set('updated_at_gte', String(params.updatedAtGte));
	const query = searchParams.toString();

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/folders/${folderId}/shared/chats${query ? `?${query}` : ''}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) {
				const body = await res.json().catch(() => ({}));
				throw Object.assign(new Error(body.detail ?? res.statusText), { status: res.status });
			}
			return res.json();
		})
		.catch((err) => {
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFolderUsers = async (token: string, id: string, signal?: AbortSignal) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${encodeURIComponent(id)}/users`, {
		signal,
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			if (signal?.aborted) return null;
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getFolderTags = async (token: string, id: string, signal?: AbortSignal) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/folders/${encodeURIComponent(id)}/tags`, {
		signal,
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			if (signal?.aborted) return null;
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateFolderChatStatus = async (
	token: string,
	folderId: string,
	chatId: string,
	status: string | null
) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/folders/${encodeURIComponent(folderId)}/chats/${encodeURIComponent(chatId)}/status`,
		{
			method: 'PATCH',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ status })
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
