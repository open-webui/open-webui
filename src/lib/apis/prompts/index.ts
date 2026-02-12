import { WEBUI_API_BASE_URL } from '$lib/constants';

type PromptItem = {
	id?: string; // Prompt ID
	command: string;
	name: string; // Changed from title
	content: string;
	data?: object | null;
	meta?: object | null;
	access_grants?: object[];
	version_id?: string | null; // Active version
	commit_message?: string | null; // For history tracking
	is_production?: boolean; // Whether to set new version as production
};

type PromptHistoryItem = {
	id: string;
	prompt_id: string;
	parent_id: string | null;
	snapshot: {
		name: string;
		content: string;
		command: string;
		data: object;
		meta: object;
		access_grants: object[];
	};
	user_id: string;
	commit_message: string | null;
	created_at: number;
	user?: {
		id: string;
		name: string;
		email: string;
	};
};

type PromptDiff = {
	from_id: string;
	to_id: string;
	from_snapshot: object;
	to_snapshot: object;
	content_diff: string[];
	name_changed: boolean;
	access_grants_changed: boolean;
};

export const createNewPrompt = async (token: string, prompt: PromptItem) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...prompt,
			command: prompt.command.startsWith('/') ? prompt.command.slice(1) : prompt.command
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

export const getPrompts = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/`, {
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

export const getPromptTags = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/tags`, {
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
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPromptItems = async (
	token: string = '',
	query: string | null,
	viewOption: string | null,
	selectedTag: string | null,
	orderBy: string | null,
	direction: string | null,
	page: number
) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (query) {
		searchParams.append('query', query);
	}
	if (viewOption) {
		searchParams.append('view_option', viewOption);
	}
	if (selectedTag) {
		searchParams.append('tag', selectedTag);
	}
	if (orderBy) {
		searchParams.append('order_by', orderBy);
	}
	if (direction) {
		searchParams.append('direction', direction);
	}
	if (page) {
		searchParams.append('page', page.toString());
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/list?${searchParams.toString()}`, {
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
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPromptList = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/list`, {
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

export const getPromptByCommand = async (token: string, command: string) => {
	let error = null;

	command = command.charAt(0) === '/' ? command.slice(1) : command;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/command/${command}`, {
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

export const getPromptById = async (token: string, promptId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/id/${promptId}`, {
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

export const updatePromptById = async (token: string, prompt: PromptItem) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/id/${prompt.id}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify(prompt)
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

export const updatePromptMetadata = async (
	token: string,
	promptId: string,
	name: string,
	command: string,
	tags: string[] = []
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/id/${promptId}/update/meta`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({ name, command, tags })
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

export const setProductionPromptVersion = async (
	token: string,
	promptId: string,
	version_id: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/id/${promptId}/update/version`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			version_id: version_id
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deletePromptById = async (token: string, promptId: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/id/${promptId}/delete`, {
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

export const updatePromptAccessGrants = async (
	token: string,
	promptId: string,
	accessGrants: any[]
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/id/${promptId}/access/update`, {
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

////////////////////////////
// Prompt History APIs
////////////////////////////

export const getPromptHistory = async (
	token: string,
	promptId: string,
	page: number = 0
): Promise<PromptHistoryItem[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/id/${promptId}/history?page=${page}`, {
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
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deletePromptHistoryVersion = async (
	token: string,
	promptId: string,
	historyId: string
): Promise<boolean> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/id/${promptId}/history/${historyId}`, {
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
		.catch((err) => {
			error = err.detail;
			console.error(err);
			return false;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPromptHistoryEntry = async (
	token: string,
	promptId: string,
	historyId: string
): Promise<PromptHistoryItem> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/id/${promptId}/history/${historyId}`, {
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
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const restorePromptFromHistory = async (
	token: string,
	promptId: string,
	historyId: string,
	commitMessage?: string
) => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/prompts/id/${promptId}/history/${historyId}/restore`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				commit_message: commitMessage
			})
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

export const getPromptDiff = async (
	token: string,
	promptId: string,
	fromId: string,
	toId: string
): Promise<PromptDiff> => {
	let error = null;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/prompts/id/${promptId}/history/diff?from_id=${fromId}&to_id=${toId}`,
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
