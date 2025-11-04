import { WEBUI_API_BASE_URL } from '$lib/constants';

type SystemHealth = {
	mode: {
		enterprise_mode: boolean;
		local_features_enabled: boolean;
	};
	engines: {
		embeddings: string | null;
		stt: string | null;
		tts: string | null;
		vectordb: string | null;
		ocr: string | null;
	};
	vector_db: {
		status: string;
		detail?: string;
		code?: number;
	};
};

export const getSystemHealth = async (token: string | null = null): Promise<SystemHealth> => {
	let error: unknown = null;

	const headers: Record<string, string> = {
		'Content-Type': 'application/json'
	};

	if (token) {
		headers.Authorization = `Bearer ${token}`;
	}

	const res = await fetch(`${WEBUI_API_BASE_URL}/system/health`, {
		method: 'GET',
		headers
	})
		.then(async (response) => {
			if (!response.ok) throw await response.json();
			return response.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
			return null;
		});

	if (error) {
		throw error;
	}

	return (res ?? {}) as SystemHealth;
};
