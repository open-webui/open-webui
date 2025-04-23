import { OPENAI_API_BASE_URL, WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
import { handleApiUnauthorized } from '$lib/stores';

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

    return res?.OPENAI_API_BASE_URLS ?? []; // Ensure array return
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

    return res?.OPENAI_API_BASE_URLS ?? []; // Ensure array return
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

    return res?.OPENAI_API_KEYS ?? []; // Ensure array return
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

    return res?.OPENAI_API_KEYS ?? []; // Ensure array return
};

// No internal token used, direct key usage - no 401 check needed here
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
            if (res.status === 401 && token) { handleApiUnauthorized(); }
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
    url: string = 'https://api.openai.com/v1',
    key: string = '',
    direct: boolean = false
) => {
    if (!url) {
        throw 'OpenAI: URL is required';
    }

    let error = null;
    let res = null;

    if (direct) {
        // Direct call uses key, no internal token, no 401 check here
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
                error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
                return [];
            });

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
                key
            })
        })
            .then(async (res) => {
                if (res.status === 401 && token) { handleApiUnauthorized(); }
                if (!res.ok) throw await res.json();
                return res.json();
            })
            .catch((err) => {
                error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
                return [];
            });
    }

    // Throw error after the relevant branch has executed
    if (error) {
        throw error;
    }

    return res;
};

export const chatCompletion = async (
    token: string = '',
    body: object,
    url: string = `${WEBUI_BASE_URL}/api`
): Promise<[Response | null, AbortController]> => {
    const controller = new AbortController();
    let error: Error | null = null;
    let response: Response | null = null;

    try {
        response = await fetch(`${url}/chat/completions`, {
            signal: controller.signal,
            method: 'POST',
            headers: {
                Authorization: `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(body)
        });

        if (response.status === 401 && token) {
            handleApiUnauthorized();
            throw new Error('Unauthorized'); // Ensures catch block runs, response remains null
        }

        if (!response.ok) {
             // Attempt to get error details, might partially work for streams
             let errorDetail = `HTTP error! status: ${response.status}`;
             try {
                 const errJson = await response.json(); // This might fail if stream already started writing
                 errorDetail = errJson.detail ?? errorDetail;
             } catch (e) { /* Ignore JSON parsing errors on non-JSON or partial stream errors */ }
             throw new Error(errorDetail);
        }
    } catch (err) {
        console.log(err); // Original log
        error = err instanceof Error ? err : new Error(String(err)); // Ensure error is an Error object
        response = null; // Set response to null in case of any fetch/status error
        if (!controller.signal.aborted) {
             controller.abort(); // Abort if fetch failed or status was bad
        }
    }

    if (error && response === null) {
        // Throw the captured error only if the fetch operation failed entirely or was aborted due to an error status
        throw error;
    }

    return [response, controller]; // Return potentially null response and controller
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
        body: JSON.stringify(body)
    })
        .then(async (res) => {
            if (res.status === 401 && token) { handleApiUnauthorized(); }
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
    })
    .then(res => { // Added .then() here
        if (res.status === 401 && token) { handleApiUnauthorized(); throw new Error('Unauthorized'); }
        if (!res.ok) { throw new Error(`HTTP error! status: ${res.status}`); } // Throw basic error for non-ok status
        return res; // Return the Response object for potentially binary data
    })
    .catch((err) => {
        console.log(err); // Original log
        error = err instanceof Error ? err : new Error(String(err)); // Ensure error is an Error object
        return null;
    });

    if (error && res === null) { // Throw only if catch occurred and res is null
        throw error;
    }

    return res; // Return Response or null
};
