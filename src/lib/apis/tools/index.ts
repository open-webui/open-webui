import { WEBUI_API_BASE_URL } from '$lib/constants';

export const createNewTool = async (token: string, tool: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...tool
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

export const loadToolByUrl = async (token: string = '', url: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/load/url`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			url
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

export const getTools = async (token: string = '', query: string | null = null) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (query) searchParams.append('query', query);

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/?${searchParams.toString()}`, {
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

export const getToolSpecs = async (token: string, id: string) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${encodeURIComponent(id)}/specs`, {
		headers: { Accept: 'application/json', authorization: `Bearer ${token}` }
	});
	if (!res.ok) {
		throw { status: res.status };
	}
	return (await res.json()).specs;
};

export const getToolList = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/list`, {
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

export const exportTools = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/export`, {
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

export const getToolById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${id}`, {
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

export const updateToolById = async (token: string, id: string, tool: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...tool
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

export const updateToolAccessGrants = async (token: string, id: string, accessGrants: any[]) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${id}/access/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ access_grants: accessGrants })
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

export const deleteToolById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${id}/delete`, {
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

export const getToolValvesById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${id}/valves`, {
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

export const getToolValvesSpecById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${id}/valves/spec`, {
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

export const updateToolValvesById = async (token: string, id: string, valves: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${id}/valves/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...valves
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

export const getUserValvesById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${id}/valves/user`, {
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

export const getUserValvesSpecById = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${id}/valves/user/spec`, {
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

export const updateUserValvesById = async (token: string, id: string, valves: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/tools/id/${id}/valves/user/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...valves
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

export type ToolHistoryEntry = {
	id: string;
	tool_id: string;
	parent_id: string | null;
	user_id: string;
	commit_message: string | null;
	created_at: number;
	user?: { name: string } | null;
};

export type ToolSnapshot = {
	name: string;
	content: string;
	meta: Record<string, any>;
};

export const getToolHistory = async (
	token: string,
	id: string,
	page = 1
): Promise<ToolHistoryEntry[]> => {
	const response = await fetch(
		`${WEBUI_API_BASE_URL}/tools/id/${encodeURIComponent(id)}/history?page=${page}`,
		{
			method: 'GET',
			headers: { authorization: `Bearer ${token}` }
		}
	);
	if (!response.ok) throw await response.json();
	return response.json();
};

export const getToolHistoryEntry = async (
	token: string,
	id: string,
	versionId: string
): Promise<ToolHistoryEntry & { snapshot: ToolSnapshot }> => {
	const response = await fetch(
		`${WEBUI_API_BASE_URL}/tools/id/${encodeURIComponent(id)}/history/${encodeURIComponent(versionId)}`,
		{
			method: 'GET',
			headers: { authorization: `Bearer ${token}` }
		}
	);
	if (!response.ok) throw await response.json();
	return response.json();
};

export const getToolHistoryDiff = async (
	token: string,
	id: string,
	fromId: string,
	toId: string
) => {
	const response = await fetch(
		`${WEBUI_API_BASE_URL}/tools/id/${encodeURIComponent(id)}/history/diff?${new URLSearchParams({ from_id: fromId, to_id: toId })}`,
		{
			method: 'GET',
			headers: { authorization: `Bearer ${token}` }
		}
	);
	if (!response.ok) throw await response.json();
	return response.json();
};

export const deleteToolHistoryVersion = async (token: string, id: string, versionId: string) => {
	const response = await fetch(
		`${WEBUI_API_BASE_URL}/tools/id/${encodeURIComponent(id)}/history/${encodeURIComponent(versionId)}`,
		{
			method: 'DELETE',
			headers: { authorization: `Bearer ${token}` }
		}
	);
	if (!response.ok) throw await response.json();
	return response.json();
};

export const setProductionToolVersion = async (token: string, id: string, versionId: string) => {
	const response = await fetch(
		`${WEBUI_API_BASE_URL}/tools/id/${encodeURIComponent(id)}/update/version`,
		{
			method: 'POST',
			headers: { authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
			body: JSON.stringify({ version_id: versionId })
		}
	);
	if (!response.ok) throw await response.json();
	return response.json();
};
