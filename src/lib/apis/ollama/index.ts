import { OLLAMA_API_BASE_URL } from '$lib/constants';

export const verifyOllamaConnection = async (token: string = '', connection: dict = {}) => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/verify`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			...connection
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `Ollama: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOllamaConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/config`, {
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
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type OllamaConfig = {
	ENABLE_OLLAMA_API: boolean;
	OLLAMA_BASE_URLS: string[];
	OLLAMA_API_CONFIGS: object;
};

export const updateOllamaConfig = async (token: string = '', config: OllamaConfig) => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			...config
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
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOllamaUrls = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/urls`, {
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
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res.OLLAMA_BASE_URLS;
};

export const updateOllamaUrls = async (token: string = '', urls: string[]) => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/urls/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			urls: urls
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
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res.OLLAMA_BASE_URLS;
};

export const getOllamaVersion = async (token: string, urlIdx?: number) => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/version${urlIdx ? `/${urlIdx}` : ''}`, {
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
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.version ?? false;
};

export const getOllamaModels = async (token: string = '', urlIdx: null | number = null) => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/tags${urlIdx !== null ? `/${urlIdx}` : ''}`, {
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
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = 'Server connection failed';
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return (res?.models ?? [])
		.map((model) => ({ id: model.model, name: model.name ?? model.model, ...model }))
		.sort((a, b) => {
			return a.name.localeCompare(b.name);
		});
};

export const generatePrompt = async (token: string = '', model: string, conversation: string) => {
	let error = null;

	if (conversation === '') {
		conversation = '[no existing conversation]';
	}

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/generate`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			prompt: `Conversation:
			${conversation}

			As USER in the conversation above, your task is to continue the conversation. Remember, Your responses should be crafted as if you're a human conversing in a natural, realistic manner, keeping in mind the context and flow of the dialogue. Please generate a fitting response to the last message in the conversation, or if there is no existing conversation, initiate one as a normal person would.
			
			Response:
			`
		})
	}).catch((err) => {
		console.error(err);
		if ('detail' in err) {
			error = err.detail;
		}
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};

export const generateEmbeddings = async (token: string = '', model: string, text: string) => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/embeddings`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			prompt: text
		})
	}).catch((err) => {
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};

export const generateTextCompletion = async (token: string = '', model: string, text: string) => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/generate`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			prompt: text,
			stream: true
		})
	}).catch((err) => {
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};

export const generateChatCompletion = async (token: string = '', body: object) => {
	let controller = new AbortController();
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/chat`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	}).catch((err) => {
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return [res, controller];
};

export const createModel = async (token: string, payload: object, urlIdx: string | null = null) => {
	let error = null;

	const res = await fetch(
		`${OLLAMA_API_BASE_URL}/api/create${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify(payload)
		}
	).catch((err) => {
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};

export const deleteModel = async (token: string, tagName: string, urlIdx: string | null = null) => {
	let error = null;

	const res = await fetch(
		`${OLLAMA_API_BASE_URL}/api/delete${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'DELETE',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				name: tagName
			})
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.then((json) => {
			console.debug(json);
			return true;
		})
		.catch((err) => {
			console.error(err);
			error = err;

			if ('detail' in err) {
				error = err.detail;
			}

			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const pullModel = async (token: string, tagName: string, urlIdx: number | null = null) => {
	let error = null;
	const controller = new AbortController();

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/pull${urlIdx !== null ? `/${urlIdx}` : ''}`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			name: tagName
		})
	}).catch((err) => {
		console.error(err);
		error = err;

		if ('detail' in err) {
			error = err.detail;
		}

		return null;
	});
	if (error) {
		throw error;
	}
	return [res, controller];
};

export const downloadModel = async (
	token: string,
	download_url: string,
	urlIdx: string | null = null
) => {
	let error = null;

	const res = await fetch(
		`${OLLAMA_API_BASE_URL}/models/download${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				Authorization: `Bearer ${token}`
			},
			body: JSON.stringify({
				url: download_url
			})
		}
	).catch((err) => {
		console.error(err);
		error = err;

		if ('detail' in err) {
			error = err.detail;
		}

		return null;
	});
	if (error) {
		throw error;
	}
	return res;
};

export const uploadModel = async (token: string, file: File, urlIdx: string | null = null) => {
	let error = null;

	const formData = new FormData();
	formData.append('file', file);

	const res = await fetch(
		`${OLLAMA_API_BASE_URL}/models/upload${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			headers: {
				Authorization: `Bearer ${token}`
			},
			body: formData
		}
	).catch((err) => {
		console.error(err);
		error = err;

		if ('detail' in err) {
			error = err.detail;
		}

		return null;
	});
	if (error) {
		throw error;
	}
	return res;
};

// export const pullModel = async (token: string, tagName: string) => {
// 	return await fetch(`${OLLAMA_API_BASE_URL}/pull`, {
// 		method: 'POST',
// 		headers: {
// 			'Content-Type': 'text/event-stream',
// 			Authorization: `Bearer ${token}`
// 		},
// 		body: JSON.stringify({
// 			name: tagName
// 		})
// 	});
// };
