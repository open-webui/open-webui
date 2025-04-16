import { AUDIO_API_BASE_URL } from '$lib/constants';

export const getAudioConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${AUDIO_API_BASE_URL}/config`, {
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
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type OpenAIConfigForm = {
	url: string;
	key: string;
	model: string;
	speaker: string;
};

export const updateAudioConfig = async (token: string, payload: OpenAIConfigForm) => {
	let error = null;

	const res = await fetch(`${AUDIO_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...payload
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

export const transcribeAudio = async (token: string, file: File) => {
	const data = new FormData();
	data.append('file', file);

	let error = null;
	const res = await fetch(`${AUDIO_API_BASE_URL}/transcriptions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			authorization: `Bearer ${token}`
		},
		body: data
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
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
	model?: string
) => {
	let error = null;

	const res = await fetch(`${AUDIO_API_BASE_URL}/speech`, {
		method: 'POST',
		headers: {
			Authorization: `Bearer ${token}`,
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			input: text,
			voice: speaker,
			...(model && { model })
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);

			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

interface AvailableModelsResponse {
	models: { name: string; id: string }[] | { id: string }[];
}

export const getModels = async (token: string = ''): Promise<AvailableModelsResponse> => {
	let error = null;

	const res = await fetch(`${AUDIO_API_BASE_URL}/models`, {
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
			error = err.detail;
			console.log(err);

			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

const _fetchVoicesFromAPI = async (apiPath: string, token: string = '') => {
    let error: string | null = null; // Changed to string or null for simplicity

    const url = `${AUDIO_API_BASE_URL}${apiPath}`;
    console.log(`API: Fetching voices from URL: ${url}`);

    try {
        const response = await fetch(url, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
                ...(token && { Authorization: `Bearer ${token}` }) // Include Auth only if token exists
            }
        });

        if (!response.ok) {
            let errorData: any = { detail: `Request failed with status: ${response.status} ${response.statusText}` };
            try {
                errorData = await response.json(); // Try to parse JSON error body
            } catch (parseError) {
                // Ignore parsing error, use the status text error
            }
            throw errorData; // Throw the error object (could be parsed JSON or the fallback)
        }
        return await response.json(); // Return parsed successful JSON response
    } catch (err: any) {
        console.error(`API Fetch Error from ${url}:`, err);
        // Extract detail or use a generic message; re-throw a consistent error
        error = err?.detail || (typeof err === 'string' ? err : `Failed to fetch from ${apiPath}`);
        throw new Error(error); // Always throw an actual Error object
    }
};


// --- The SINGLE Exported Function for Getting Voices ---
// It now accepts engineType to decide the path
export const getVoices = async (token: string = '', engineType: string = '') => {
    let apiPath = '/voices'; // Default endpoint

    // *** The core logic change is here ***
    if (engineType === 'customtts') {
        apiPath = '/audio/voices'; // Use the custom endpoint path
        console.log(`API: Engine is CustomTTS, using path: ${apiPath}`);
    } else {
         console.log(`API: Engine is '${engineType}', using default path: ${apiPath}`);
    }
    // Add more 'else if' conditions here if other engines ever need different paths

    // Call the internal helper with the chosen path
    return await _fetchVoicesFromAPI(apiPath, token);
};