
export type OpenRouterConfig = {
	OPENROUTER_API_KEY_SET: boolean;
	OPENROUTER_ANONYMOUS_ENABLED: boolean;
	OPENROUTER_API_BASE_URL: string;
	OPENROUTER_DEFAULT_MODEL_ID: string;
};

export const getOpenRouterConfig = async (token: string): Promise<OpenRouterConfig> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/openrouter/config`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return (await res.json()) as OpenRouterConfig;
		})
		.catch((err) => {
			error = err?.detail ?? `${err}`;
			return null;
		});

	if (error) throw error;
	return res!;
};

export const updateOpenRouterConfig = async (
	token: string,
	body: { OPENROUTER_API_KEY?: string; OPENROUTER_ANONYMOUS_ENABLED?: boolean }
): Promise<OpenRouterConfig> => {
	let error: string | null = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/openrouter/config/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return (await res.json()) as OpenRouterConfig;
		})
		.catch((err) => {
			error = err?.detail ?? `${err}`;
			return null;
		});

	if (error) throw error;
	return res!;
};

