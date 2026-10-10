import { WEBUI_API_BASE_URL } from '$lib/constants';

export const createNewSkill = async (token: string, skill: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/skills/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...skill
		})
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

export const getSkills = async (token: string = '', query: string | null = null) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (query) searchParams.append('query', query);

	const res = await fetch(`${WEBUI_API_BASE_URL}/skills/?${searchParams.toString()}`, {
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

export const getSkillList = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/skills/list`, {
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

export const getSkillItems = async (
	token: string = '',
	query: string | null = null,
	viewOption: string | null = null,
	page: number | null = null,
	orderBy: string | null = null,
	direction: string | null = null,
	signal?: AbortSignal
) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (query) searchParams.append('query', query);
	if (viewOption) searchParams.append('view_option', viewOption);
	if (page) searchParams.append('page', page.toString());
	if (orderBy) searchParams.append('order_by', orderBy);
	if (direction) searchParams.append('direction', direction);

	const res = await fetch(`${WEBUI_API_BASE_URL}/skills/list?${searchParams.toString()}`, {
		method: 'GET',
		signal,
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
			if (signal?.aborted) return null;
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const exportSkills = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/skills/export`, {
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

export const getSkillById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/skills/id/${id}`, {
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

export const updateSkillById = async (token: string, id: string, skill: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/skills/id/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...skill
		})
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

export const updateSkillAccessGrants = async (token: string, id: string, accessGrants: any[]) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/skills/id/${id}/access/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			access_grants: accessGrants
		})
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

export const toggleSkillById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/skills/id/${id}/toggle`, {
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

export const deleteSkillById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/skills/id/${id}/delete`, {
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

export type SkillFile = { path: string; content: string; encoding?: 'base64' };
export type SkillFileSummary = { path: string; size: number; encoding?: 'base64' | null };
export type SkillFileOperation = {
	op: 'put' | 'move' | 'delete';
	path: string;
	content?: string;
	encoding?: 'base64';
	destination?: string;
};

export const skillRequest = async (token: string, path: string, options: RequestInit = {}) => {
	const response = await fetch(`${WEBUI_API_BASE_URL}/skills${path}`, {
		...options,
		headers: {
			authorization: `Bearer ${token}`,
			...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
			...options.headers
		}
	});
	if (!response.ok) {
		const body = await response.json();
		throw body.detail ?? body;
	}
	return response;
};
export const getSkillFiles = async (token: string, id: string, versionId: string) =>
	(
		await skillRequest(token, `/id/${id}/files?${new URLSearchParams({ version_id: versionId })}`)
	).json();
export const getSkillFile = async (token: string, id: string, versionId: string, path: string) =>
	(
		await skillRequest(
			token,
			`/id/${id}/files/content?${new URLSearchParams({ version_id: versionId, path })}`
		)
	).blob();
export const getSkillHistory = async (token: string, id: string, page = 1) =>
	(await skillRequest(token, `/id/${id}/history?page=${page}`)).json();
export const getSkillVersion = async (token: string, id: string, versionId: string) =>
	(await skillRequest(token, `/id/${id}/history/${versionId}`)).json();
export const deleteSkillHistoryVersion = async (token: string, id: string, versionId: string) =>
	(await skillRequest(token, `/id/${id}/history/${versionId}`, { method: 'DELETE' })).json();
export const setProductionSkillVersion = async (
	token: string,
	id: string,
	versionId: string,
	expectedVersionId: string
) =>
	(
		await skillRequest(token, `/id/${id}/update/version`, {
			method: 'POST',
			body: JSON.stringify({ version_id: versionId, expected_version_id: expectedVersionId })
		})
	).json();
export const cloneSkill = async (
	token: string,
	id: string,
	name: string,
	newId: string,
	versionId?: string
) =>
	(
		await skillRequest(token, `/id/${id}/clone`, {
			method: 'POST',
			body: JSON.stringify({ id: newId, name, version_id: versionId })
		})
	).json();
export const exportSkillBundle = async (
	token: string,
	format: 'json' | 'zip',
	ids: string[] = [],
	versionId?: string
) => {
	const query = new URLSearchParams({ format });
	ids.forEach((id) => query.append('ids', id));
	if (versionId) query.set('version_id', versionId);
	return (await skillRequest(token, `/export?${query}`)).blob();
};
export const importSkillBundles = async (token: string, files: File[], decisions?: object[]) => {
	const body = new FormData();
	files.forEach((file) => body.append('files', file, file.webkitRelativePath || file.name));
	if (decisions) body.append('decisions', JSON.stringify(decisions));
	return (
		await skillRequest(token, decisions ? '/import' : '/import/preview', { method: 'POST', body })
	).json();
};
export const loadSkillByUrl = async (token: string, url: string) =>
	(
		await skillRequest(token, '/load/url', {
			method: 'POST',
			body: JSON.stringify({ url })
		})
	).json();
export const skillError = (error: unknown): string =>
	error instanceof Error
		? error.message
		: typeof error === 'string'
			? error
			: JSON.stringify(error);

export const downloadSkillBlob = (blob: Blob, filename: string) => {
	const url = URL.createObjectURL(blob);
	const anchor = document.createElement('a');
	anchor.href = url;
	anchor.download = filename;
	document.body.appendChild(anchor);
	anchor.click();
	anchor.remove();
	setTimeout(() => URL.revokeObjectURL(url), 1000);
};
