import { WEBUI_API_BASE_URL } from '$lib/constants';

const MODEL_NAME_MAPPING: Record<string, string> = {
    'arthrod/cicerollamatry8': 'CiceroPT-BR'
};

export const getCiceroModels = async (token: string) => {
    const res = await fetch(`${WEBUI_API_BASE_URL}/models`, {
        method: 'GET',
        headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            ...(token && { authorization: `Bearer ${token}` })
        }
    });

    if (!res.ok) {
        throw new Error('Failed to fetch Cicero models');
    }

    return await res.json();
};

export const generateCiceroChatCompletion = async (
	token: string,
	body: {
		messages: { role: string; content: string }[];
		model: string;
		stream?: boolean;
	}
) => {
	const controller = new AbortController();
	const res = await fetch(`${WEBUI_API_BASE_URL}/chat/completions`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify(body),
		signal: controller.signal
	});

	return [res, controller] as const;
};
