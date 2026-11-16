import { get } from 'svelte/store';
import { selectedTerminalId, selectedFolder, chatId } from '$lib/stores';
import { WEBUI_BASE_URL } from '$lib/constants';

// Let every request reach its destination,
// and let those who wait receive an answer worthy of their patience.
export const getModels = async (
	token: string = '',
	base: boolean = false,
	refresh: boolean = false,
	context?: { terminalId: string | null; chatId?: string | null; cwd?: string | null }
) => {
	const searchParams = new URLSearchParams();
	if (context === undefined) {
		const terminalId = get(selectedTerminalId);
		const currentChatId = get(chatId);
		const folder = get(selectedFolder);
		context = {
			terminalId,
			chatId: currentChatId,
			cwd:
				!currentChatId && folder?.data?.terminal_id === terminalId
					? folder?.data?.working_directory
					: null
		};
	}
	if (!base && context.terminalId) {
		searchParams.set('terminal_id', context.terminalId);
		if (context.chatId) searchParams.set('chat_id', context.chatId);
		if (context.cwd) searchParams.set('cwd', context.cwd);
	}
	if (refresh) {
		searchParams.append('refresh', 'true');
	}

	let error = null;
	const res = await fetch(
		`${WEBUI_BASE_URL}/api/models${base ? '/base' : ''}?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.data ?? [];
};

export const unloadModel = async (token: string, model: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/models/unload`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({ model })
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type ChatCompletedForm = {
	model: string;
	messages: Record<string, unknown>[];
	chat_id: string;
	session_id: string | undefined;
	id: string;
	filter_ids?: string[];
};

export const chatCompleted = async (token: string, body: ChatCompletedForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/chat/completed`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type ChatActionForm = {
	model: string;
	messages: string[];
	chat_id: string;
};

export const chatAction = async (token: string, action_id: string, body: ChatActionForm) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/chat/actions/${action_id}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const stopTask = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/tasks/stop/${id}`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const stopTasksByChatId = async (token: string, chat_id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/tasks/chat/${encodeURIComponent(chat_id)}/stop`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getTaskIdsByChatId = async (token: string, chat_id: string, signal?: AbortSignal) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/tasks/chat/${encodeURIComponent(chat_id)}`, {
		signal,
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			if (signal?.aborted) return null;
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const resumeTemporaryChat = async (token: string, chatId: string, sessionId: string) => {
	const res = await fetch(`${WEBUI_BASE_URL}/api/tasks/chat/${encodeURIComponent(chatId)}/resume`, {
		method: 'POST',
		headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
		body: JSON.stringify({ session_id: sessionId })
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const getTaskConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateTaskConfig = async (token: string, config: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(config)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const generateTitle = async (
	token: string = '',
	model: string,
	messages: object[],
	chat_id?: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/title/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			messages: messages,
			...(chat_id && { chat_id: chat_id })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	try {
		// Step 1: Safely extract the response string
		const response = res?.choices[0]?.message?.content ?? '';

		// Step 2: Attempt to fix common JSON format issues like single quotes
		const sanitizedResponse = response.replace(/['‘’`]/g, '"'); // Convert single quotes to double quotes for valid JSON

		// Step 3: Find the relevant JSON block within the response
		const jsonStartIndex = sanitizedResponse.indexOf('{');
		const jsonEndIndex = sanitizedResponse.lastIndexOf('}');

		// Step 4: Check if we found a valid JSON block (with both `{` and `}`)
		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = sanitizedResponse.substring(jsonStartIndex, jsonEndIndex + 1);

			// Step 5: Parse the JSON block
			const parsed = JSON.parse(jsonResponse);

			// Step 6: If there's a "tags" key, return the tags array; otherwise, return an empty array
			if (parsed && parsed.title) {
				return parsed.title;
			} else {
				return null;
			}
		}

		// If no valid JSON block found, return an empty array
		return null;
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
		console.error('Failed to parse response: ', e);
		return null;
	}
};

export const generateTags = async (
	token: string = '',
	model: string,
	messages: object[],
	chat_id?: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/tags/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			messages: messages,
			...(chat_id && { chat_id: chat_id })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	try {
		// Step 1: Safely extract the response string
		const response = res?.choices[0]?.message?.content ?? '';

		// Step 2: Attempt to fix common JSON format issues like single quotes
		const sanitizedResponse = response.replace(/['‘’`]/g, '"'); // Convert single quotes to double quotes for valid JSON

		// Step 3: Find the relevant JSON block within the response
		const jsonStartIndex = sanitizedResponse.indexOf('{');
		const jsonEndIndex = sanitizedResponse.lastIndexOf('}');

		// Step 4: Check if we found a valid JSON block (with both `{` and `}`)
		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = sanitizedResponse.substring(jsonStartIndex, jsonEndIndex + 1);

			// Step 5: Parse the JSON block
			const parsed = JSON.parse(jsonResponse);

			// Step 6: If there's a "tags" key, return the tags array; otherwise, return an empty array
			if (parsed && parsed.tags) {
				return Array.isArray(parsed.tags) ? parsed.tags : [];
			} else {
				return [];
			}
		}

		// If no valid JSON block found, return an empty array
		return [];
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
		console.error('Failed to parse response: ', e);
		return [];
	}
};

export const generateEmoji = async (
	token: string = '',
	model: string,
	prompt: string,
	chat_id?: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/emoji/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			prompt: prompt,
			...(chat_id && { chat_id: chat_id })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	const response = res?.choices[0]?.message?.content?.replace(/["']/g, '') ?? null;

	if (response) {
		if (/\p{Extended_Pictographic}/u.test(response)) {
			return response.match(/\p{Extended_Pictographic}/gu)[0];
		}
	}

	return null;
};

export const generateQueries = async (
	token: string = '',
	model: string,
	messages: object[],
	prompt: string,
	type: string = 'web_search',
	chat_id?: string
) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/queries/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			messages: messages,
			prompt: prompt,
			type: type,
			...(chat_id && { chat_id: chat_id })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	// Step 1: Safely extract the response string
	const response = res?.choices[0]?.message?.content ?? '';

	try {
		const jsonStartIndex = response.indexOf('{');
		const jsonEndIndex = response.lastIndexOf('}');

		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);

			// Step 5: Parse the JSON block
			const parsed = JSON.parse(jsonResponse);

			// Step 6: If there's a "queries" key, return the queries array; otherwise, return an empty array
			if (parsed && parsed.queries) {
				return Array.isArray(parsed.queries) ? parsed.queries : [];
			} else {
				return [];
			}
		}

		// If no valid JSON block found, return response as is
		return [response];
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
		console.error('Failed to parse response: ', e);
		return [response];
	}
};

export const generateAutoCompletion = async (
	token: string = '',
	model: string,
	prompt: string,
	messages?: object[],
	type: string = 'search query',
	chat_id?: string
) => {
	const controller = new AbortController();
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/auto/completions`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			prompt: prompt,
			...(messages && { messages: messages }),
			type: type,
			stream: false,
			...(chat_id && { chat_id: chat_id })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	const response = res?.choices?.[0]?.message?.content ?? '';

	try {
		const jsonStartIndex = response.indexOf('{');
		const jsonEndIndex = response.lastIndexOf('}');

		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);

			// Step 5: Parse the JSON block
			const parsed = JSON.parse(jsonResponse);

			// Step 6: If there's a "queries" key, return the queries array; otherwise, return an empty array
			if (parsed && parsed.text) {
				return parsed.text;
			} else {
				return '';
			}
		}

		// If no valid JSON block found, return response as is
		return response;
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
		console.error('Failed to parse response: ', e);
		return response;
	}
};

export const generateMoACompletion = async (
	token: string = '',
	model: string,
	prompt: string,
	responses: string[]
) => {
	const controller = new AbortController();
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/tasks/moa/completions`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			prompt: prompt,
			responses: responses,
			stream: true
		})
	}).catch((err) => {
		console.error(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return [res, controller];
};

export const getPipelinesList = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/list`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	const pipelines = res?.data ?? [];
	return pipelines;
};

export const uploadPipeline = async (token: string, file: File, urlIdx: string) => {
	let error = null;

	// Create a new FormData object to handle the file upload
	const formData = new FormData();
	formData.append('file', file);
	formData.append('urlIdx', urlIdx);

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/upload`, {
		method: 'POST',
		headers: {
			...(token && { authorization: `Bearer ${token}` })
			// 'Content-Type': 'multipart/form-data' is not needed as Fetch API will set it automatically
		},
		body: formData
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const downloadPipeline = async (token: string, url: string, urlIdx: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/add`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			url: url,
			urlIdx: urlIdx
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deletePipeline = async (token: string, id: string, urlIdx: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/delete`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			id: id,
			urlIdx: urlIdx
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPipelines = async (token: string, urlIdx?: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	const res = await fetch(`${WEBUI_BASE_URL}/api/v1/pipelines/?${searchParams.toString()}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	const pipelines = res?.data ?? [];
	return pipelines;
};

export const getPipelineValves = async (token: string, pipeline_id: string, urlIdx: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	const res = await fetch(
		`${WEBUI_BASE_URL}/api/v1/pipelines/${pipeline_id}/valves?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPipelineValvesSpec = async (token: string, pipeline_id: string, urlIdx: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	const res = await fetch(
		`${WEBUI_BASE_URL}/api/v1/pipelines/${pipeline_id}/valves/spec?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updatePipelineValves = async (
	token: string = '',
	pipeline_id: string,
	valves: object,
	urlIdx: string
) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	const res = await fetch(
		`${WEBUI_BASE_URL}/api/v1/pipelines/${pipeline_id}/valves/update?${searchParams.toString()}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			},
			body: JSON.stringify(valves)
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);

			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getUsage = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/usage`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			...(token && { Authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getBackendConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/config`, {
		method: 'GET',
		credentials: 'include',
		headers: {
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		// When a forward-auth proxy (e.g. Authentik/Traefik) intercepts the
		// request and redirects to an external login page, the browser blocks
		// the cross-origin redirect for fetch() and throws a TypeError.
		// Detect this by re-fetching with redirect:"manual" — if the server
		// responded with a redirect, the probe returns an opaque redirect
		// response instead of throwing, confirming the backend is alive but
		// an auth proxy is intercepting.
		if (error instanceof TypeError) {
			try {
				const probeRes = await fetch(`${WEBUI_BASE_URL}/api/config`, {
					method: 'GET',
					credentials: 'include',
					redirect: 'manual',
					headers: { 'Content-Type': 'application/json' }
				});
				if (
					probeRes.type === 'opaqueredirect' ||
					(probeRes.status >= 300 && probeRes.status < 400)
				) {
					throw { authRedirect: true };
				}
			} catch (probeErr: any) {
				if (probeErr?.authRedirect) throw probeErr;
				// Probe also failed — genuine network/backend issue
			}
		}
		throw error;
	}

	return res;
};

export const getChangelog = async () => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/changelog`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getVersion = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/version`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getVersionUpdates = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/version/updates`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export type EventCatalogItem = {
	event: string;
	description: string;
	message: string;
};

export type EventWebhookTarget = {
	type: 'user' | 'group';
	id: string;
};

export type EventWebhook = {
	id: string;
	name: string;
	url: string;
	enabled: boolean;
	events: string[];
	targets: EventWebhookTarget[] | null;
	created_at?: number;
	updated_at?: number;
};

export const getEvents = async (
	token: string
): Promise<{ schema: string; events: EventCatalogItem[] }> => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/events`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getEventWebhooks = async (token: string): Promise<EventWebhook[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/events/webhooks`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const createEventWebhook = async (
	token: string,
	webhook: Partial<EventWebhook>
): Promise<EventWebhook> => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/events/webhooks`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(webhook)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateEventWebhook = async (
	token: string,
	id: string,
	webhook: Partial<EventWebhook>
): Promise<EventWebhook> => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/events/webhooks/${id}`, {
		method: 'PUT',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(webhook)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteEventWebhook = async (token: string, id: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_BASE_URL}/api/events/webhooks/${id}`, {
		method: 'DELETE',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export interface ModelConfig {
	id: string;
	name: string;
	meta: ModelMeta;
	base_model_id?: string;
	params: ModelParams;
}

export interface ModelMeta {
	voice_avatar?: import('$lib/utils/voice-avatar').VoiceAvatarConfig | null;
	voice?: { voice?: string };
	toolIds: never[];
	description?: string;
	i18n?: Record<string, Record<string, any>>;
	hidden?: boolean;
	capabilities?: object;
	profile_image_url?: string;
	background_image_url?: string | null;
}

export interface ModelControl {
	display?: 'menu' | 'slider';
	label: string;
	description?: string;
	default?: string | null;
	options: Record<string, { label: string; params?: Record<string, any> }>;
}

export interface ModelParams {
	model_controls?: Record<string, ModelControl>;
}
