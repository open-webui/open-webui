import canchatAPI from '$lib/apis/canchatAPI';
import { OLLAMA_API_BASE_PATH } from '$lib/constants';

export const verifyOllamaConnection = async (
	token: string = '',
	url: string = '',
	key: string = ''
) => {
	let error = null;

	const res = await canchatAPI(`${OLLAMA_API_BASE_PATH}/verify`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		data: {
			url,
			key
		}
	})
		.then(async (res) => {
			return res.data;
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

	const res = await canchatAPI(`${OLLAMA_API_BASE_PATH}/config`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

	return res;
};

type OllamaConfig = {
	ENABLE_OLLAMA_API: boolean;
	OLLAMA_BASE_URLS: string[];
	OLLAMA_API_CONFIGS: object;
};

export const updateOllamaConfig = async (token: string = '', config: OllamaConfig) => {
	let error = null;

	const res = await canchatAPI(`${OLLAMA_API_BASE_PATH}/config/update`, {
		method: 'POST',

		data: {
			...config
		}
	})
		.then(async (res) => {
			return res.data;
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

	return res;
};

export const getOllamaUrls = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${OLLAMA_API_BASE_PATH}/urls`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

	const res = await canchatAPI(`${OLLAMA_API_BASE_PATH}/urls/update`, {
		method: 'POST',

		data: {
			urls: urls
		}
	})
		.then(async (res) => {
			return res.data;
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

export const getOllamaVersion = async (token: string, urlIdx?: number) => {
	let error = null;

	const res = await canchatAPI(`${OLLAMA_API_BASE_PATH}/api/version${urlIdx ? `/${urlIdx}` : ''}`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
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

	return res?.version ?? false;
};

export const getOllamaModels = async (token: string = '', urlIdx: null | number = null) => {
	let error = null;

	const res = await canchatAPI(
		`${OLLAMA_API_BASE_PATH}/api/tags${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'GET'
		}
	)
		.then(async (res) => {
			return res.data;
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

export const generatePrompt = async (token: string = '', model: string, conversation: string) => {
	let error = null;

	if (conversation === '') {
		conversation = '[no existing conversation]';
	}

	const res = await canchatAPI(`${OLLAMA_API_BASE_PATH}/api/generate`, {
		method: 'POST',
		data: {
			model: model,
			prompt: `Conversation:
			${conversation}

			As USER in the conversation above, your task is to continue the conversation. Remember, Your responses should be crafted as if you're a human conversing in a natural, realistic manner, keeping in mind the context and flow of the dialogue. Please generate a fitting response to the last message in the conversation, or if there is no existing conversation, initiate one as a normal person would.

			Response:
			`
		}
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

export const generateEmbeddings = async (token: string = '', model: string, text: string) => {
	let error = null;

	const res = await canchatAPI(`${OLLAMA_API_BASE_PATH}/api/embeddings`, {
		method: 'POST',
		data: {
			model: model,
			prompt: text
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

export const generateTextCompletion = async (token: string = '', model: string, text: string) => {
	let error = null;

	const res = await canchatAPI(`${OLLAMA_API_BASE_PATH}/api/generate`, {
		method: 'POST',
		data: {
			model: model,
			prompt: text,
			stream: true
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

export const generateChatCompletion = async (token: string = '', body: object) => {
	let controller = new AbortController();
	let error = null;

	const res = await canchatAPI(`${OLLAMA_API_BASE_PATH}/api/chat`, {
		signal: controller.signal,
		method: 'POST',
		data: body
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

	const res = await canchatAPI(
		`${OLLAMA_API_BASE_PATH}/api/create${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			data: payload
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

	const res = await canchatAPI(
		`${OLLAMA_API_BASE_PATH}/api/delete${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'DELETE',
			data: {
				name: tagName
			}
		}
	)
		.then(async (res) => {
			return res.data;
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

export const pullModel = async (token: string, tagName: string, urlIdx: number | null = null) => {
	let error = null;
	const controller = new AbortController();

	const res = await canchatAPI(
		`${OLLAMA_API_BASE_PATH}/api/pull${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			signal: controller.signal,
			method: 'POST',
			data: {
				name: tagName
			}
		}
	).catch((err) => {
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
	return [res, controller];
};

export const downloadModel = async (
	token: string,
	download_url: string,
	urlIdx: string | null = null
) => {
	let error = null;

	const res = await canchatAPI(
		`${OLLAMA_API_BASE_PATH}/models/download${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			data: {
				url: download_url
			}
		}
	).catch((err) => {
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

export const uploadModel = async (token: string, file: File, urlIdx: string | null = null) => {
	let error = null;

	const formData = new FormData();
	formData.append('file', file);

	const res = await canchatAPI(
		`${OLLAMA_API_BASE_PATH}/models/upload${urlIdx !== null ? `/${urlIdx}` : ''}`,
		{
			method: 'POST',
			data: formData
		}
	).catch((err) => {
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
// 	return await axiosInstance(`${OLLAMA_API_BASE_URL}/pull`, {
// 		method: 'POST',
// 		headers: {
// 			'Content-Type': 'text/event-stream',
// 			Authorization: `Bearer ${token}`
// 		},
// 		data: {
// 			name: tagName
// 		})
// 	});
// };
