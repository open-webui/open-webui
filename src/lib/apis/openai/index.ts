import { OPENAI_API_BASE_URL, WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

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

type OpenAIConfig = {
	ENABLE_OPENAI_API: boolean;
	OPENAI_API_BASE_URLS: string[];
	OPENAI_API_KEYS: string[];
	OPENAI_API_CONFIGS: object;
};

export const OPENAI_WEB_AUTH_API_BASE_URL = 'https://api.openai.com/v1';
export const OPENAI_CODEX_WEB_AUTH_API_BASE_URL = 'https://chatgpt.com/backend-api/codex';
export const OPENAI_CODEX_WEB_AUTH_TYPE = 'openai_codex_web_auth';
export const OPENAI_CODEX_WEB_AUTH_LEGACY_TYPE = 'openai_web_auth';

export const getSupportedOpenAIConnectionAuthTypes = ({
	direct = false,
	ollama = false,
	azure = false
}: {
	direct?: boolean;
	ollama?: boolean;
	azure?: boolean;
} = {}) => {
	const authTypes = [
		{ value: 'none', label: 'None' },
		{ value: 'bearer', label: 'Bearer' }
	];

	if (ollama) {
		return authTypes;
	}

	authTypes.push({ value: 'session', label: 'Session' });

	if (!direct) {
		authTypes.push({ value: 'system_oauth', label: 'OAuth' });
		if (azure) {
			authTypes.push({ value: 'microsoft_entra_id', label: 'Entra ID' });
		}
	}

	return authTypes;
};

export const isOpenAICodexWebAuthConfig = (config: Record<string, unknown> = {}) =>
	config.auth_type === OPENAI_CODEX_WEB_AUTH_TYPE ||
	config.auth_type === OPENAI_CODEX_WEB_AUTH_LEGACY_TYPE;

export const isEmptyNativeOpenAIBearerConnection = (
	url: string,
	key = '',
	config: Record<string, unknown> = {}
) =>
	url.replace(/\/$/, '') === OPENAI_WEB_AUTH_API_BASE_URL &&
	!key &&
	(!config.auth_type || config.auth_type === 'bearer');

export const createOpenAIWebAuthConnectionConfig = (
	existingConfig: Record<string, unknown> = {}
) => ({
	...existingConfig,
	enable: true,
	auth_type: OPENAI_CODEX_WEB_AUTH_TYPE,
	connection_type: existingConfig.connection_type ?? 'external'
});

export const applyOpenAIWebAuthConnection = (
	urls: string[],
	keys: string[],
	configs: Record<string, Record<string, unknown>>
) => {
	const normalizedUrls = urls.map((url) => url.replace(/\/$/, ''));
	const normalizedKeys = [...keys];
	while (normalizedKeys.length < normalizedUrls.length) {
		normalizedKeys.push('');
	}

	const nextUrls: string[] = [];
	const nextKeys: string[] = [];
	const nextConfigs: Record<string, Record<string, unknown>> = {};
	let webAuthIdx = -1;
	let emptyBearerIdx = -1;

	for (const [idx, url] of normalizedUrls.entries()) {
		const config = configs[idx] ?? {};
		const key = normalizedKeys[idx] ?? '';
		const webAuth = isOpenAICodexWebAuthConfig(config);
		const emptyBearer = isEmptyNativeOpenAIBearerConnection(url, key, config);

		if (
			(url === OPENAI_WEB_AUTH_API_BASE_URL || url === OPENAI_CODEX_WEB_AUTH_API_BASE_URL) &&
			!key &&
			webAuth
		) {
			if (webAuthIdx === -1) {
				webAuthIdx = nextUrls.length;
			} else {
				continue;
			}
		}

		if (emptyBearer && emptyBearerIdx === -1) {
			emptyBearerIdx = nextUrls.length;
		}

		nextUrls.push(url);
		nextKeys.push(key);
		nextConfigs[nextUrls.length - 1] = config;
	}

	const targetIdx = webAuthIdx >= 0 ? webAuthIdx : emptyBearerIdx;
	if (targetIdx >= 0) {
		nextUrls[targetIdx] = OPENAI_CODEX_WEB_AUTH_API_BASE_URL;
		nextKeys[targetIdx] = '';
		nextConfigs[targetIdx] = createOpenAIWebAuthConnectionConfig(nextConfigs[targetIdx] ?? {});
	} else {
		nextUrls.push(OPENAI_CODEX_WEB_AUTH_API_BASE_URL);
		nextKeys.push('');
		nextConfigs[nextUrls.length - 1] = createOpenAIWebAuthConnectionConfig();
	}

	const finalUrls: string[] = [];
	const finalKeys: string[] = [];
	const finalConfigs: Record<string, Record<string, unknown>> = {};

	for (const [idx, url] of nextUrls.entries()) {
		const config = nextConfigs[idx] ?? {};
		const key = nextKeys[idx] ?? '';
		if (isEmptyNativeOpenAIBearerConnection(url, key, config)) {
			continue;
		}

		finalUrls.push(url);
		finalKeys.push(key);
		finalConfigs[finalUrls.length - 1] = config;
	}

	return {
		urls: finalUrls,
		keys: finalKeys,
		configs: finalConfigs
	};
};

export const createOpenAIWebAuthConfigUpdate = (config: OpenAIConfig): OpenAIConfig => {
	const next = applyOpenAIWebAuthConnection(
		config.OPENAI_API_BASE_URLS,
		config.OPENAI_API_KEYS,
		config.OPENAI_API_CONFIGS as Record<string, Record<string, unknown>>
	);

	return {
		...config,
		ENABLE_OPENAI_API: true,
		OPENAI_API_BASE_URLS: next.urls,
		OPENAI_API_KEYS: next.keys,
		OPENAI_API_CONFIGS: next.configs
	};
};

export type OpenAIWebAuthStatus = {
	credential_type: 'none' | 'web_auth' | string;
	connected: boolean;
	has_credential: boolean;
	status: 'not_configured' | 'connected' | 'reconnect_required' | string;
	expires_at?: number | null;
};

export type OpenAIWebAuthStart = {
	verification_url: string;
	user_code: string;
	session_id: string;
	interval: number;
	expires_at: number;
};

const normalizeOpenAIWebAuthNumber = (value: unknown): number | null => {
	if (typeof value !== 'number' || !Number.isFinite(value)) {
		return null;
	}
	return value;
};

const normalizeOpenAIWebAuthString = (value: unknown): string => {
	return typeof value === 'string' ? value : '';
};

const normalizeOpenAIWebAuthStatus = (body: unknown): OpenAIWebAuthStatus => {
	const source = body && typeof body === 'object' ? (body as Record<string, unknown>) : {};
	const expiresAt = normalizeOpenAIWebAuthNumber(source.expires_at);

	return {
		credential_type: normalizeOpenAIWebAuthString(source.credential_type) || 'none',
		connected: source.connected === true,
		has_credential: source.has_credential === true,
		status: normalizeOpenAIWebAuthString(source.status) || 'not_configured',
		...(expiresAt !== null ? { expires_at: expiresAt } : {})
	};
};

const normalizeOpenAIWebAuthStart = (body: unknown): OpenAIWebAuthStart => {
	const source = body && typeof body === 'object' ? (body as Record<string, unknown>) : {};

	return {
		verification_url: normalizeOpenAIWebAuthString(source.verification_url),
		user_code: normalizeOpenAIWebAuthString(source.user_code),
		session_id: normalizeOpenAIWebAuthString(source.session_id),
		interval: normalizeOpenAIWebAuthNumber(source.interval) ?? 0,
		expires_at: normalizeOpenAIWebAuthNumber(source.expires_at) ?? 0
	};
};

const handleOpenAIWebAuthResponse = async <T>(
	response: Response,
	normalize: (body: unknown) => T
): Promise<T> => {
	const body = await response.json().catch(() => ({}));
	if (!response.ok) {
		throw body;
	}
	return normalize(body);
};

const normalizeOpenAIWebAuthError = (err: unknown) => {
	console.error(err);
	if (err && typeof err === 'object' && 'detail' in err) {
		return (err as { detail: string }).detail;
	}
	return 'Server connection failed';
};

export const getOpenAIWebAuthStatus = async (token: string = ''): Promise<OpenAIWebAuthStatus> => {
	try {
		return await fetch(`${OPENAI_API_BASE_URL}/web-auth/status`, {
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}).then((res) => handleOpenAIWebAuthResponse(res, normalizeOpenAIWebAuthStatus));
	} catch (err) {
		throw normalizeOpenAIWebAuthError(err);
	}
};

export const startOpenAIWebAuth = async (token: string = ''): Promise<OpenAIWebAuthStart> => {
	try {
		return await fetch(`${OPENAI_API_BASE_URL}/web-auth/start`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}).then((res) => handleOpenAIWebAuthResponse(res, normalizeOpenAIWebAuthStart));
	} catch (err) {
		throw normalizeOpenAIWebAuthError(err);
	}
};

export const completeOpenAIWebAuth = async (
	token: string = '',
	sessionId: string
): Promise<OpenAIWebAuthStatus> => {
	try {
		return await fetch(`${OPENAI_API_BASE_URL}/web-auth/complete`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			},
			body: JSON.stringify({ session_id: sessionId })
		}).then((res) => handleOpenAIWebAuthResponse(res, normalizeOpenAIWebAuthStatus));
	} catch (err) {
		throw normalizeOpenAIWebAuthError(err);
	}
};

export const disconnectOpenAIWebAuth = async (token: string = ''): Promise<OpenAIWebAuthStatus> => {
	try {
		return await fetch(`${OPENAI_API_BASE_URL}/web-auth/disconnect`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			}
		}).then((res) => handleOpenAIWebAuthResponse(res, normalizeOpenAIWebAuthStatus));
	} catch (err) {
		throw normalizeOpenAIWebAuthError(err);
	}
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
	connection: Record<string, unknown> = {},
	direct: boolean = false
) => {
	const { url, key, config } = connection as {
		url?: string;
		key?: string;
		config?: Record<string, unknown>;
	};
	if (!url) {
		throw 'OpenAI: URL is required';
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
				error = `OpenAI: ${err?.error?.message ?? 'Network Problem'}`;
				return [];
			});

		if (error) {
			throw error;
		}
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
				key,
				config
			})
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
		console.error(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return [res, controller];
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
		credentials: 'include',
		body: JSON.stringify(body)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = err?.detail ?? err;
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
	}).catch((err) => {
		console.error(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return res;
};
