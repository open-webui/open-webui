import { OPENAI_API_BASE_URL } from '$lib/constants';

const MODEL_NAME_MAPPING: Record<string, string> = {
    'arthrod/cicerollamatry8': 'CiceroPT-BR'
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
