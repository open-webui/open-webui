import { GEMINI_API_BASE_URL } from '$lib/constants';

export const getGeminiConfig = async (token: string = '') => {
    let error = null;

    const res = await fetch(`${GEMINI_API_BASE_URL}/config`, {
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

type GeminiConfig = {
    ENABLE_GEMINI_API: boolean;
    GEMINI_API_BASE_URLS: string[];
    GEMINI_API_KEYS: string[];
    GEMINI_API_CONFIGS: object;
};

export const updateGeminiConfig = async (token: string = '', config: GeminiConfig) => {
    let error = null;

    const res = await fetch(`${GEMINI_API_BASE_URL}/config/update`, {
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

export const getGeminiModels = async (token: string, urlIdx?: number) => {
    let error = null;

    const res = await fetch(
        `${GEMINI_API_BASE_URL}/models${typeof urlIdx === 'number' ? `/${urlIdx}` : ''}`,
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
            error = `Gemini: ${err?.error?.message ?? 'Network Problem'}`;
            return [];
        });

    if (error) {
        throw error;
    }

    return res;
};

export const verifyGeminiConnection = async (
    token: string = '',
    connection: { url: string; key: string; config?: object }
) => {
    const { url, key, config } = connection;
    if (!url) {
        throw 'Gemini: URL is required';
    }

    let error = null;

    const res = await fetch(`${GEMINI_API_BASE_URL}/verify`, {
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
            error = `Gemini: ${err?.error?.message ?? 'Network Problem'}`;
            return [];
        });

    if (error) {
        throw error;
    }

    return res;
};
