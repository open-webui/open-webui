import { OLLAMA_API_BASE_URL } from '$lib/constants';

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
			console.log(err);
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
			console.log(err);
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

export const getOllamaVersion = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/version`, {
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
			console.log(err);
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

	return res?.version ?? '';
};

export const getOllamaModels = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/tags`, {
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
			console.log(err);
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

// TODO: migrate to backend
export const generateTitle = async (
	token: string = '',
	template: string,
	model: string,
	prompt: string
) => {
	let error = null;

	template = template.replace(/{{prompt}}/g, prompt);

	console.log(template);

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/generate`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			model: model,
			prompt: template,
			stream: false
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.response ?? 'New Chat';
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
		console.log(err);
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

export const cancelChatCompletion = async (token: string = '', requestId: string) => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/cancel/${requestId}`, {
		method: 'GET',
		headers: {
			'Content-Type': 'text/event-stream',
			Authorization: `Bearer ${token}`
		}
	}).catch((err) => {
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};

export const createModel = async (token: string, tagName: string, content: string) => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			name: tagName,
			modelfile: content
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
			console.log(json);
			return true;
		})
		.catch((err) => {
			console.log(err);
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

export const pullModel = async (token: string, tagName: string, urlIdx: string | null = null) => {
	let error = null;

	const res = await fetch(`${OLLAMA_API_BASE_URL}/api/pull${urlIdx !== null ? `/${urlIdx}` : ''}`, {
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
		console.log(err);
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
