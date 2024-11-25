import { OPENAI_API_BASE_URL } from '$lib/constants';

const MODEL_NAME_MAPPING: Record<string, string> = {
    'arthrod/cicerollamatry8': 'CiceroPT-BR'
};


export const getCiceroConfig = async (token: string = '') => {
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

export const updateCiceroConfig = async (token: string = '', enable_openai_api: boolean) => {
	let error = null;

	const res = await fetch(`${OPENAI_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			enable_cicero_api: enable_openai_api
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

export const getCiceroUrls = async (token: string = '') => {
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

	return res.OPENAI_API_BASE_URLS;
};

export const updateCiceroUrls = async (token: string = '', urls: string[]) => {
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

	return res.OPENAI_API_BASE_URLS;
};

export const getCiceroKeys = async (token: string = '') => {
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

	return res.OPENAI_API_KEYS;
};

export const updateCiceroKeys = async (token: string = '', keys: string[]) => {
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

	return res.OPENAI_API_KEYS;
};

export const getCiceroModels = async (token: string, base_url: string) => {

    try {
        const response = await fetch(`${base_url}/models`, {
            method: 'GET',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                ...(token && { authorization: `Bearer ${token}` })
            }
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw errorData;
        }

      // If we got any response, return our model
        return [{
            id: 'arthrod/cicerollamatry8',
            name: MODEL_NAME_MAPPING['arthrod/cicerollamatry8'],
            external: true
        }];
    } catch (err) {
        console.error('Error fetching Cicero models:', err);
        // On error, return our model
        return [{
            id: 'arthrod/cicerollamatry8',
            name: MODEL_NAME_MAPPING['arthrod/cicerollamatry8'],
            external: true
        }];
    }
};

export const getCiceroModelsDirect = async (
    base_url: string = 'https://api.runpod.ai/v2/arthrod-cicerollamatry8/openai/v1',
    api_key: string = ''
) => {
    try {
        const response = await fetch(`${base_url}/models`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${api_key}`
            }
        });

        if (!response.ok) throw await response.json();
        
        // Always return our single model, regardless of API response
        return [{
            id: 'arthrod/cicerollamatry8',
            name: MODEL_NAME_MAPPING['arthrod/cicerollamatry8'],
            external: true
        }];
    } catch (err) {
        console.error('Error fetching Cicero models directly:', err);
        // Even on error, return our model
        return [{
            id: 'arthrod/cicerollamatry8',
            name: MODEL_NAME_MAPPING['arthrod/cicerollamatry8'],
            external: true
        }];
    }
};

export const generateCiceroChatCompletion = async (
    token: string = '',
    body: object,
    url: string = OPENAI_API_BASE_URL
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

export const synthesizeCiceroSpeech = async (
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
        console.log(err);
        error = err;
        return null;
    });

    if (error) {
        throw error;
    }

    return res;
};
