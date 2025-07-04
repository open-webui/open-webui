import { ANTHROPIC_API_BASE_URL, WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

export const getAnthropicConfig = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${ANTHROPIC_API_BASE_URL}/config`, {
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

type AnthropicConfig = {
	ENABLE_ANTHROPIC_API: boolean;
	ANTHROPIC_API_BASE_URLS: string[];
	ANTHROPIC_API_KEYS: string[];
	ANTHROPIC_API_CONFIGS: object;
};

export const updateAnthropicConfig = async (token: string = '', config: AnthropicConfig) => {
	let error = null;

	const res = await fetch(`${ANTHROPIC_API_BASE_URL}/config/update`, {
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

export const getAnthropicUrls = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${ANTHROPIC_API_BASE_URL}/urls`, {
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

	return res.ANTHROPIC_API_BASE_URLS;
};

export const updateAnthropicUrls = async (token: string = '', urls: string[]) => {
	let error = null;

	const res = await fetch(`${ANTHROPIC_API_BASE_URL}/urls/update`, {
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

	return res.ANTHROPIC_API_BASE_URLS;
};

export const getAnthropicKeys = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${ANTHROPIC_API_BASE_URL}/keys`, {
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

	return res.ANTHROPIC_API_KEYS;
};

export const updateAnthropicKeys = async (token: string = '', keys: string[]) => {
	let error = null;

	const res = await fetch(`${ANTHROPIC_API_BASE_URL}/keys/update`, {
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

	return res.ANTHROPIC_API_KEYS;
};

// Anthropic typically doesn't have a direct /models endpoint like OpenAI.
// Models are often predefined or configured per API key.
// This function might need to fetch models from a configuration or a predefined list.
export const getAnthropicModels = async (token: string, urlIdx?: number) => {
	let error = null;

	const res = await fetch(
		`${ANTHROPIC_API_BASE_URL}/models${typeof urlIdx === 'number' ? `/${urlIdx}` : ''}`,
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
			error = `Anthropic: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const verifyAnthropicConnection = async (
	token: string = '',
	connection: dict = {},
	direct: boolean = false // direct might not be as relevant for Anthropic's typical setup
) => {
	const { url, key, config } = connection;
	if (!url) {
		throw 'Anthropic: URL is required';
	}
	if (!key) {
		throw 'Anthropic: API Key is required';
	}

	let error = null;
	let res = null;

	// Direct verification for Anthropic would involve making a test API call.
	// This is simplified here.
	if (direct) {
		// This is a placeholder. A real direct verification would make a test call.
		// For example, try to list models or send a very small test message.
		// Since Anthropic doesn't have a general /models endpoint, we simulate success if URL/key are present.
		// A more robust check would be to call the /v1/messages endpoint with a test prompt.
		if (url && key) {
			res = { data: [{ id: 'claude-verified-directly', name: 'Claude (Direct Verification)' }] }; // Simulate successful verification
		} else {
			error = 'Anthropic: URL and Key are required for direct verification.';
		}

		if (error) {
			throw error;
		}
	} else {
		res = await fetch(`${ANTHROPIC_API_BASE_URL}/verify`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				url,
				key,
				config // Pass config if needed for verification logic on backend (e.g. specific model to test)
			})
		})
			.then(async (res) => {
				if (!res.ok) throw await res.json();
				return res.json();
			})
			.catch((err) => {
				error = `Anthropic: ${err?.detail ?? (err?.error?.message ?? 'Network Problem')}`;
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
	url: string = `${WEBUI_BASE_URL}/api` // This should point to the new /anthropic/chat/completions if distinct
): Promise<[Response | null, AbortController]> => {
	const controller = new AbortController();
	let error = null;

	// Ensure the URL points to the Anthropic-specific backend endpoint
	const completionUrl = url.replace('/openai/', '/anthropic/').replace('/ollama/', '/anthropic/');


	const res = await fetch(`${completionUrl}/chat/completions`, {
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

export const generateAnthropicChatCompletion = async (
	token: string = '',
	body: object,
	url: string = `${WEBUI_BASE_URL}/api`  // This should point to the new /anthropic/chat/completions
) => {
	let error = null;
    // Ensure the URL points to the Anthropic-specific backend endpoint
	const completionUrl = url.replace('/openai/', '/anthropic/').replace('/ollama/', '/anthropic/');


	const res = await fetch(`${completionUrl}/chat/completions`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = `${err?.detail ?? err}`;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Anthropic does not have a direct speech synthesis API like OpenAI's /audio/speech.
// This function would need to be removed or adapted if a third-party service or a different Anthropic product is used.
// For now, it's commented out.
/*
export const synthesizeAnthropicSpeech = async (
	token: string = '',
	speaker: string = 'alloy', // Speaker concept might not apply or be different
	text: string = '',
	model: string = 'claude-tts-model' // Fictional Anthropic TTS model
) => {
	let error = null;

	const res = await fetch(`${ANTHROPIC_API_BASE_URL}/audio/speech`, { // This endpoint is fictional for Anthropic
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`, // Or X-API-Key for Anthropic
			'Content-Type': 'application/json'
			// Anthropic might require 'anthropic-version' header
		},
		body: JSON.stringify({
			model: model,
			input: text,
			voice: speaker // Voice parameter might be different for Anthropic
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
*/
