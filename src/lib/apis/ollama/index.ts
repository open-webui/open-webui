import { OLLAMA_API_BASE_URL } from '$lib/constants';
import { handleApiUnauthorized } from '$lib/utils/auth'; // Assuming location

export const verifyOllamaConnection = async (
    token: string = '',
    url: string = '',
    key: string = ''
) => {
    let error = null;

    const res = await fetch(`${OLLAMA_API_BASE_URL}/verify`, {
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
            if (res.status === 401 && token) { handleApiUnauthorized(); } // Check added here
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
            if (res.status === 401 && token) { handleApiUnauthorized(); }
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
            if (res.status === 401 && token) { handleApiUnauthorized(); }
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
            if (res.status === 401 && token) { handleApiUnauthorized(); }
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

    return res?.OLLAMA_BASE_URLS ?? []; // Ensure return is always an array
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
            if (res.status === 401 && token) { handleApiUnauthorized(); }
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

    return res?.OLLAMA_BASE_URLS ?? []; // Ensure return is always an array
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
            if (res.status === 401 && token) { handleApiUnauthorized(); }
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
            if (res.status === 401 && token) { handleApiUnauthorized(); }
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
    })
    .then(async (res) => { // Added .then() here
        if (res.status === 401 && token) { handleApiUnauthorized(); }
        if (!res.ok) throw await res.json(); // Throw if not ok to trigger catch
        return res; // Return the response object if ok
    })
    .catch((err) => {
        console.log(err);
        if ('detail' in err) {
            error = err.detail; // Keep existing error assignment logic
        } else if (err instanceof Response) { // If throw from .then()
            error = `HTTP error! status: ${err.status}`;
        } else {
            error = 'Network error or failed request';
        }
        return null;
    });

    if (error && res === null) { // Only throw if catch actually set error and res is null
        throw error;
    }

    return res; // Return the result (Response object or null)
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
    })
    .then(async (res) => { // Added .then() here
        if (res.status === 401 && token) { handleApiUnauthorized(); }
        if (!res.ok) throw await res.json(); // Throw if not ok to trigger catch
        return res; // Return the response object if ok
    })
    .catch((err) => {
        error = err;
        console.error('Fetch error in generateEmbeddings:', err); // Log error
        return null;
    });

    if (error && res === null) {
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
    })
    .then(res => { // Added .then() here
        // Note: Cannot read res.json() for streaming response here
        if (res.status === 401 && token) { handleApiUnauthorized(); throw new Error('Unauthorized'); } // Throw to prevent further processing on 401
        if (!res.ok) { throw new Error(`HTTP error! status: ${res.status}`); } // Throw for other errors
        return res; // Return response for streaming
    })
    .catch((err) => {
        error = err;
        console.error('Fetch error in generateTextCompletion:', err);
        return null;
    });

    if (error && res === null) {
        throw error;
    }

    return res;
};

export const generateChatCompletion = async (token: string = '', body: object) => {
    let controller = new AbortController();
    let error = null;
    let response: Response | null = null;

    try {
        response = await fetch(`${OLLAMA_API_BASE_URL}/api/chat`, {
            signal: controller.signal,
            method: 'POST',
            headers: {
                Accept: 'application/json',
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify(body)
        });

        if (response.status === 401 && token) {
            handleApiUnauthorized();
            throw new Error('Unauthorized'); // Throw to abort further processing
        }
        if (!response.ok) {
             // Try to get error detail, but might fail for streams
            let errorDetail = `HTTP error! status: ${response.status}`;
            try {
                const errJson = await response.json();
                errorDetail = errJson.detail ?? errorDetail;
            } catch (e) { /* Ignore if reading json fails */ }
            throw new Error(errorDetail);
        }
    } catch (err) {
        error = err;
        console.error('Fetch error in generateChatCompletion:', err);
        response = null; // Ensure response is null on error
        controller.abort(); // Abort ongoing request if error occurred
    }


    if (error && response === null) {
        throw error; // Re-throw captured error if fetch failed entirely or was aborted due to error
    }

    // Return potentially null response and controller
    return [response, controller];
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
    )
    .then(res => { // Added .then() here
        if (res.status === 401 && token) { handleApiUnauthorized(); throw new Error('Unauthorized'); }
        if (!res.ok) { throw new Error(`HTTP error! status: ${res.status}`); }
        return res; // Return response for streaming/progress
    })
    .catch((err) => {
        error = err;
        console.error('Fetch error in createModel:', err);
        return null;
    });

    if (error && res === null) {
        throw error;
    }

    return res;
};

export const deleteModel = async (token: string, tagName: string, urlIdx: string | null = null) => {
    let error = null;
    let successResult = null;

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
            if (res.status === 401 && token) { handleApiUnauthorized(); }
            if (!res.ok) throw await res.json();
            return res.json(); // Assuming success returns JSON? Original code returns true later. Let's keep JSON for now.
        })
        .then((json) => {
            console.log(json); // Original console log
            successResult = true; // Set success flag
            return json; // Pass JSON along if needed, or return true directly
        })
        .catch((err) => {
            console.log(err); // Original console log
            error = err;
            if ('detail' in err) {
                error = err.detail; // Use detail if available
            } else if (err instanceof Error) {
                error = err.message; // Use message from Error objects
            }
            // Keep error as the caught object if it's neither
            return null;
        });

    if (error && successResult === null ) { // Throw only if catch happened and success not reached
        throw error;
    }

    return successResult; // Return true on success, null on handled error
};


export const pullModel = async (token: string, tagName: string, urlIdx: number | null = null) => {
    let error = null;
    const controller = new AbortController();
    let response: Response | null = null;

    try {
        response = await fetch(`${OLLAMA_API_BASE_URL}/api/pull${urlIdx !== null ? `/${urlIdx}` : ''}`, {
            signal: controller.signal,
            method: 'POST',
            headers: {
                Accept: 'application/json', // Server sends JSON stream
                'Content-Type': 'application/json',
                Authorization: `Bearer ${token}`
            },
            body: JSON.stringify({
                name: tagName
            })
        });

        if (response.status === 401 && token) {
            handleApiUnauthorized();
            throw new Error('Unauthorized'); // Abort
        }
        if (!response.ok) {
            let errorDetail = `HTTP error! status: ${response.status}`;
             try { // Attempt to parse error json even from potential stream error start
                const errJson = await response.json();
                errorDetail = errJson.detail ?? errorDetail;
            } catch (e) { /* Ignore if reading json fails */ }
            throw new Error(errorDetail);
        }

    } catch (err) {
        console.log(err); // Original log
        error = err;
        if ('detail' in err) { // Keep original detail check if err is object
            error = err.detail;
        } else if (err instanceof Error) {
            error = err.message;
        }
        response = null; // Nullify response on error
        controller.abort(); // Abort request
    }


    if (error && response === null) {
        throw error; // Throw if error occurred and response is null
    }

    return [response, controller]; // Return response (potentially null) and controller
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
    )
    .then(res => { // Added .then() here
        if (res.status === 401 && token) { handleApiUnauthorized(); throw new Error('Unauthorized'); }
        if (!res.ok) { throw new Error(`HTTP error! status: ${res.status}`); }
        return res; // Return response
    })
    .catch((err) => {
        console.log(err); // Original log
        error = err;
        if ('detail' in err) { // Keep original detail check
            error = err.detail;
        } else if (err instanceof Error) {
            error = err.message;
        }
        return null;
    });

    if (error && res === null) {
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
                // Content-Type is set automatically for FormData
                Authorization: `Bearer ${token}`
            },
            body: formData
        }
    )
    .then(res => { // Added .then() here
        if (res.status === 401 && token) { handleApiUnauthorized(); throw new Error('Unauthorized'); }
        if (!res.ok) { throw new Error(`HTTP error! status: ${res.status}`); }
        return res; // Return response
    })
    .catch((err) => {
        console.log(err); // Original log
        error = err;
        if ('detail' in err) { // Keep original detail check
            error = err.detail;
        } else if (err instanceof Error) {
            error = err.message;
        }
        return null;
    });

    if (error && res === null) {
        throw error;
    }

    return res;
};

// Commented out original pullModel remains commented out
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
