import { AIFRED_API_BASE_URL, WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

export const getAifredConfig = async (token: string = '') => {
	let error = null;

	try {
		console.log("API BASE URL:", AIFRED_API_BASE_URL);
		console.log("Fetching from:", `${AIFRED_API_BASE_URL}/config`);

		const res = await fetch(`${AIFRED_API_BASE_URL}/config`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		});

		const text = await res.text();  // JSON 대신 원본 응답을 출력
		console.log("Response:", text);

		if (!res.ok) {
			throw new Error(`API Error: ${res.status} - ${text}`);
		}

		const json = JSON.parse(text);
		return json;

	} catch (err) {
		console.error("Fetch Error:", err);
		throw err;
	}
};

// export const getAifredConfig = async (token: string = '') => {debugger;
// 	let error = null;
	
// 	const res = await fetch(`${AIFRED_API_BASE_URL}/config`, {
// 		method: 'GET',
// 		headers: {
// 			Accept: 'application/json',
// 			'Content-Type': 'application/json',
// 			...(token && { authorization: `Bearer ${token}` })
// 		}
// 	})
// 	.then(async (res) => {
// 		if (!res.ok) throw await res.json();
// 		return res.json();
// 	})
// 	.catch((err) => {
// 		console.log(err);
// 		if ('detail' in err) {
// 			error = err.detail;
// 		} else {
// 			error = 'Server connection failed';
// 		}
// 		return null;
// 	});

// 	if (error) {
// 		throw error;
// 	}

// 	return res;
// };

type AifredConfig = {
	ENABLE_AIFRED_API: boolean;
	AIFRED_API_BASE_URLS: string[];
	AIFRED_API_KEYS: string[];
	AIFRED_API_CONFIGS: object;
};

export const updateAifredConfig = async (token: string = '', config: AifredConfig) => {
	let error = null;

	const res = await fetch(`${AIFRED_API_BASE_URL}/config/update`, {
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

export const getAifredUrls = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${AIFRED_API_BASE_URL}/urls`, {
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

	return res.AIFRED_API_BASE_URLS;
};

export const updateAifredUrls = async (token: string = '', urls: string[]) => {
	let error = null;

	const res = await fetch(`${AIFRED_API_BASE_URL}/urls/update`, {
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

	return res.AIFRED_API_BASE_URLS;
};

export const getAifredKeys = async (token: string = '') => {
	let error = null;

	const res = await fetch(`${AIFRED_API_BASE_URL}/keys`, {
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

	return res.AIFRED_API_KEYS;
};

export const updateAifredKeys = async (token: string = '', keys: string[]) => {
	let error = null;

	const res = await fetch(`${AIFRED_API_BASE_URL}/keys/update`, {
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

	return res.AIFRED_API_KEYS;
};

export const getOpenAIModelsDirect = async (url: string, key: string) => {
	let error = null;

	const res = await fetch(`${url}/models`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(key && { authorization: `Bearer ${key}` })
		}
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

	return res;
};

export const getAifredModels = async (token: string, urlIdx?: number) => {
	let error = null;

	const res = await fetch(
		`${AIFRED_API_BASE_URL}/models${typeof urlIdx === 'number' ? `/${urlIdx}` : ''}`,
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
			error = `Aifred: ${err?.error?.message ?? 'Network Problem'}`;
			return [];
		});

	if (error) {
		throw error;
	}

	return res;
};

export const verifyAifredConnection = async (
	token: string = '',
	url: string = 'https://api.aifred.com/v1',
	key: string = '',
	direct: boolean = false
) => {
	if (!url) {
		throw 'Aifred: URL is required';
	}

	let error = null;
	let res = null;

	if (direct) {
		res = await fetch(`${url}/models`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				Authorization: `Bearer ${key}`,
				'Content-Type': 'application/json'
			}
		})
			.then(async (res) => {
				if (!res.ok) throw await res.json();
				return res.json();
			})
			.catch((err) => {
				error = `Aifred: ${err?.error?.message ?? 'Network Problem'}`;
				return [];
			});

		if (error) {
			throw error;
		}
	} else {
		res = await fetch(`${AIFRED_API_BASE_URL}/verify`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				Authorization: `Bearer ${token}`,
				'Content-Type': 'application/json'
			},
			body: JSON.stringify({
				url,
				key
			})
		})
			.then(async (res) => {
				if (!res.ok) throw await res.json();
				return res.json();
			})
			.catch((err) => {
				error = `Aifred: ${err?.error?.message ?? 'Network Problem'}`;
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
		console.log(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return [res, controller];
};

export const generateAifredChatCompletion = async (
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

export const synthesizeAifredSpeech = async (
	token: string = '',
	speaker: string = 'alloy',
	text: string = '',
	model: string = 'tts-1'
) => {
	let error = null;

	const res = await fetch(`${AIFRED_API_BASE_URL}/audio/speech`, {
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
		console.log(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};
