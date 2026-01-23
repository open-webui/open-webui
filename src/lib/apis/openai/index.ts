import { OPENAI_API_BASE_URL, WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

export const getOpenAIConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/config`, {
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

type OpenAIConfig = {
	ENABLE_OPENAI_API: boolean;
	OPENAI_API_BASE_URLS: string[];
	OPENAI_API_KEYS: string[];
	OPENAI_API_CONFIGS: object;
};

export const updateOpenAIConfig = async (token: string = '', config: OpenAIConfig) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/config/update`, {
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

export const getOpenAIUrls = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/urls`, {
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

	return res?.OPENAI_API_BASE_URLS ?? [];
};

export const updateOpenAIUrls = async (token: string = '', urls: string[]) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/urls/update`, {
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

	return res.OPENAI_API_BASE_URLS;
};

export const getOpenAIKeys = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/keys`, {
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

	return res?.OPENAI_API_KEYS ?? [];
};

export const updateOpenAIKeys = async (token: string = '', keys: string[]) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/keys/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			keys: keys
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

	return res.OPENAI_API_KEYS;
};

/**
 * Generate a list of possible model list endpoint URLs based on the base URL.
 * Different API providers use different endpoint patterns.
 */
const generateModelListUrls = (baseUrl: string): string[] => {
	const urls: string[] = [];
	baseUrl = baseUrl.replace(/\/+$/, ''); // Remove trailing slashes

	// Primary: append /models to the configured base URL
	urls.push(`${baseUrl}/models`);

	// Parse the URL to understand its structure
	try {
		const parsed = new URL(baseUrl);
		const path = parsed.pathname.replace(/\/+$/, '');

		// If the path ends with a version prefix, try other versions
		if (path.endsWith('/v1') || path === '/v1') {
			const baseWithoutVersion = baseUrl.replace(/\/v1\/?$/, '');
			urls.push(`${baseWithoutVersion}/v1beta/models`);
			urls.push(`${baseWithoutVersion}/models`);
		} else if (path.endsWith('/v1beta') || path === '/v1beta') {
			const baseWithoutVersion = baseUrl.replace(/\/v1beta\/?$/, '');
			urls.push(`${baseWithoutVersion}/v1/models`);
			urls.push(`${baseWithoutVersion}/models`);
		} else if (!['/v1', '/v1beta', '/v2'].some((v) => path.endsWith(v))) {
			// No version in path, try adding version prefixes
			urls.push(`${baseUrl}/v1/models`);
			urls.push(`${baseUrl}/v1beta/models`);
		}
	} catch {
		// If URL parsing fails, just use the primary URL
	}

	// Remove duplicates while preserving order
	return [...new Set(urls)];
};

export const getOpenAIModelsDirect = async (url: string, key: string) => {
	let error = null;
	const urlsToTry = generateModelListUrls(url);

	for (const modelUrl of urlsToTry) {
		try {
			const res = await fetch(modelUrl, {
				method: 'GET',
				headers: {
					Accept: 'application/json',
					'Content-Type': 'application/json',
					...(key && { authorization: `Bearer ${key}` })
				}
			});

			if (res.ok) {
				const data = await res.json();
				// Validate response format
				if (data && (Array.isArray(data) || data.data || data.models)) {
					console.debug(`Successfully fetched models from ${modelUrl}`);
					// Normalize response format
					if (Array.isArray(data)) {
						return { data, object: 'list' };
					} else if (data.models && !data.data) {
						return { data: data.models, object: 'list' };
					}
					return data;
				}
			}
			console.debug(`Model list request to ${modelUrl} returned HTTP ${res.status}`);
		} catch (err) {
			console.debug(`Error fetching models from ${modelUrl}:`, err);
			error = `OpenAI: ${(err as any)?.error?.message ?? 'Network Problem'}`;
		}
	}

	if (error) {
		throw error;
	}

	return [];
};

export const getOpenAIModels = async (token: string, urlIdx?: number) => {
	let error = null;

	const res = await fetch(
		`${OPENAI_API_BASE_URL}/models${typeof urlIdx === 'number' ? `/${urlIdx}` : ''}`,
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
			error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const verifyOpenAIConnection = async (
	token: string = '',
	connection: { url?: string; key?: string; config?: Record<string, unknown> } = {},
	direct: boolean = false
) => {
	const { url, key, config } = connection;
	if (!url) {
		throw 'OpenAI: URL is required';
	}

	let error = null;
	let res = null;

	if (direct) {
		// Use fallback mechanism to try multiple endpoint patterns
		const urlsToTry = generateModelListUrls(url);

		for (const modelUrl of urlsToTry) {
			try {
				const response = await fetch(modelUrl, {
					method: 'GET',
					headers: {
						Accept: 'application/json',
						Authorization: `Bearer ${key}`,
						'Content-Type': 'application/json'
					}
				});

				if (response.ok) {
					const data = await response.json();
					// Validate response format
					if (data && (Array.isArray(data) || data.data || data.models)) {
						console.debug(`Successfully verified connection via ${modelUrl}`);
						// Normalize response format
						if (Array.isArray(data)) {
							res = { data, object: 'list' };
						} else if (data.models && !data.data) {
							res = { data: data.models, object: 'list' };
						} else {
							res = data;
						}
						break;
					}
				}
				console.debug(`Verify request to ${modelUrl} returned HTTP ${response.status}`);
			} catch (err) {
				console.debug(`Error verifying connection via ${modelUrl}:`, err);
				error = `OpenAI: ${(err as any)?.error?.message ?? 'Network Problem'}`;
			}
		}

		// If all /models endpoints failed, try chat/completions as fallback
		// Many API providers only implement chat endpoints without /models
		if (!res) {
			console.debug('All /models endpoints failed, trying chat/completions fallback');
			try {
				const chatUrl = `${url.replace(/\/+$/, '')}/chat/completions`;
				const response = await fetch(chatUrl, {
					method: 'POST',
					headers: {
						Accept: 'application/json',
						Authorization: `Bearer ${key}`,
						'Content-Type': 'application/json'
					},
					body: JSON.stringify({
						model: 'gpt-3.5-turbo',
						messages: [{ role: 'user', content: 'hi' }],
						max_tokens: 1,
						stream: false
					})
				});

				const data = await response.json().catch(() => ({}));

				if (response.ok) {
					// Some APIs return HTTP 200 even for errors, with custom error format
					// e.g., {"code": -1, "msg": "apikey error"} or {"error": {...}}
					// If we got a JSON response, the API is reachable
					const hasErrorCode = data?.code !== undefined && data?.code !== 0;
					const hasErrorField = 'error' in data || 'msg' in data;
					const hasChoices = 'choices' in data;

					if (hasChoices || hasErrorCode || hasErrorField || Object.keys(data).length > 0) {
						console.debug('Successfully verified connection via chat/completions (got JSON response)');
						res = {
							data: [],
							object: 'list',
							verified_via: 'chat_completions',
							message: 'Connection verified via chat/completions. Please add model IDs manually.'
						};
					}
				} else if ([400, 404, 422].includes(response.status)) {
					// These status codes indicate the API is reachable but model not found
					// This means the API is working!
					const errorMsg = data?.error?.message?.toLowerCase() || '';
					const modelNotFoundKeywords = [
						'model',
						'not found',
						'does not exist',
						'invalid',
						'unknown',
						'unsupported'
					];
					const isModelError = modelNotFoundKeywords.some((kw) => errorMsg.includes(kw));

					if (isModelError || [400, 404, 422].includes(response.status)) {
						console.debug('Connection verified via chat/completions (model error response)');
						res = {
							data: [],
							object: 'list',
							verified_via: 'chat_completions',
							message:
								'Connection verified. The /models endpoint is not available, please add model IDs manually.'
						};
					}
				} else if ([401, 403].includes(response.status)) {
					// Auth error - throw the error
					error = `OpenAI: ${data?.error?.message ?? 'Authentication failed'}`;
				}
			} catch (err) {
				console.debug('Error verifying connection via chat/completions:', err);
			}
		}

		if (!res && error) {
			throw error;
		}
		if (!res) {
			res = [];
		}
	} else {
		res = await fetch(`${OPENAI_API_BASE_URL}/verify`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				url,
				key,
				config
			})
		})
			.then(async (res) => {
				if (!res.ok) throw await res.json();
				return res.json();
			})
			.catch((err) => {
				error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
				return [];
			});

		if (error) {
			throw error;
		}
	}

	return res;
};

export const chatCompletion = async (
	token: string = '',
	body: object,
	url: string = `${WEBUI_BASE_URL}/api`
): Promise<[Response | null, AbortController]> => {
	const controller = new AbortController();
	let error = null;

	const res = await fetch(`${url}/chat/completions`, {
		signal: controller.signal,
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(body)
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

export const generateOpenAIChatCompletion = async (
	token: string = '',
	body: object,
	url: string = `${WEBUI_BASE_URL}/api`
) => {
	let error = null;

	const res = await fetch(`${url}/chat/completions`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		credentials: 'include',
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const synthesizeOpenAISpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model: string = 'tts-1'
) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/audio/speech`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			model: model,
			input: text,
			voice: speaker
		})
	}).catch((err) => {
		console.error(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};
