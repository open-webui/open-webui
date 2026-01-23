import { WEBUI_API_BASE_URL } from '$lib/constants';

type PromptItem = {
	command: string;
	name: string;  // Changed from title
	content: string;
	data?: object | null;
	meta?: object | null;
	access_control?: null | object;
	version_id?: string | null;  // Active version
	commit_message?: string | null;  // For history tracking
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
		access_control: object | null;
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
	access_control_changed: boolean;
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

export const updatePromptByCommand = async (token: string, prompt: PromptItem) => {
	let error = null;

	const command = prompt.command.charAt(0) === '/' ? prompt.command.slice(1) : prompt.command;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/command/${command}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...prompt,
			command: command
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

export const setProductionPromptVersion = async (
	token: string,
	command: string,
	version_id: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/command/${command}/set/version`, {
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

export const deletePromptByCommand = async (token: string, command: string) => {
	let error = null;

	command = command.charAt(0) === '/' ? command.slice(1) : command;

	const res = await fetch(`${WEBUI_API_BASE_URL}/prompts/command/${command}/delete`, {
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

////////////////////////////
// Prompt History APIs
////////////////////////////

export const getPromptHistory = async (
	token: string,
	command: string,
	limit: number = 50,
	offset: number = 0
): Promise<PromptHistoryItem[]> => {
	let error = null;

	command = command.charAt(0) === '/' ? command.slice(1) : command;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/prompts/command/${command}/history?limit=${limit}&offset=${offset}`,
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

export const deletePromptHistoryVersion = async (
	token: string,
	command: string,
	historyId: string
): Promise<boolean> => {
	let error = null;

	command = command.charAt(0) === '/' ? command.slice(1) : command;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/prompts/command/${command}/history/${historyId}`,
		{
			method: 'DELETE',
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
			return false;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPromptHistoryEntry = async (
	token: string,
	command: string,
	historyId: string
): Promise<PromptHistoryItem> => {
	let error = null;

	command = command.charAt(0) === '/' ? command.slice(1) : command;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/prompts/command/${command}/history/${historyId}`,
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

export const restorePromptFromHistory = async (
	token: string,
	command: string,
	historyId: string,
	commitMessage?: string
) => {
	let error = null;

	command = command.charAt(0) === '/' ? command.slice(1) : command;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/prompts/command/${command}/history/${historyId}/restore`,
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
	command: string,
	fromId: string,
	toId: string
): Promise<PromptDiff> => {
	let error = null;

	command = command.charAt(0) === '/' ? command.slice(1) : command;

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/prompts/command/${command}/history/diff?from_id=${fromId}&to_id=${toId}`,
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


