import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
import type { Banner } from '$lib/types';

export const importConfig = async (token: string, config: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/import`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			config: config
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const exportConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/export`, {
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
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getConnectionsConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/connections`, {
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
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setConnectionsConfig = async (token: string, config: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/connections`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
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
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getToolServerConnections = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/tool_servers`, {
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
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setToolServerConnections = async (token: string, connections: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/tool_servers`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...connections
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getTerminalServerConnections = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/terminal_servers`, {
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
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setTerminalServerConnections = async (token: string, connections: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/terminal_servers`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...connections
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * Detect whether a terminal server URL points to an Orchestrator or a direct
 * Open Terminal instance.
 *
 * - GET {url}/api/v1/policies → 200 → "orchestrator"
 * - GET {url}/api/config      → 200 → "terminal"
 * - Neither                         → null
 */
export const detectTerminalServerType = async (
	url: string,
	key: string
): Promise<'orchestrator' | 'terminal' | null> => {
	const baseUrl = url.replace(/\/$/, '');
	const headers: Record<string, string> = {};
	if (key) {
		headers['Authorization'] = `Bearer ${key}`;
	}

	// Orchestrators expose a policies API; plain terminals don't.
	try {
		const res = await fetch(`${baseUrl}/api/v1/policies`, { headers });
		if (res.ok) return 'orchestrator';
	} catch {
		// ignore
	}

	// Fall back to open-terminal config endpoint.
	try {
		const res = await fetch(`${baseUrl}/api/config`, { headers });
		if (res.ok) return 'terminal';
	} catch {
		// ignore
	}

	return null;
};

/**
 * Create or update a policy on the orchestrator.
 * Proxied through the Open WebUI backend to keep API keys server-side.
 */
export const putOrchestratorPolicy = async (
	token: string,
	url: string,
	key: string,
	policyId: string,
	policyData: object,
	authType: string = 'bearer'
): Promise<object | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/terminal_servers/policy`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			url: url.replace(/\/$/, ''),
			key,
			auth_type: authType,
			policy_id: policyId,
			policy_data: policyData
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOrchestratorPolicy = async (
	token: string,
	url: string,
	key: string,
	policyId: string,
	authType: string = 'bearer'
): Promise<any> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/terminal_servers/policy`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			url: url.replace(/\/$/, ''),
			key,
			auth_type: authType,
			policy_id: policyId
		})
	});
	if (!res.ok) {
		const body = await res.json();
		throw Object.assign(new Error(body.detail || 'Failed to read policy'), { status: res.status });
	}
	return res.json();
};

export const putOrchestratorLifecycle = async (
	token: string,
	url: string,
	key: string,
	policyId: string,
	lifecycleData: object,
	authType: string = 'bearer'
): Promise<object | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/terminal_servers/lifecycle`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			url: url.replace(/\/$/, ''),
			key,
			auth_type: authType,
			policy_id: policyId,
			lifecycle_data: lifecycleData
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOrchestratorLifecycle = async (
	token: string,
	url: string,
	key: string,
	policyId: string,
	authType: string = 'bearer'
): Promise<any> => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/terminal_servers/lifecycle`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			url: url.replace(/\/$/, ''),
			key,
			auth_type: authType,
			policy_id: policyId
		})
	});
	if (!res.ok) {
		const body = await res.json();
		throw Object.assign(new Error(body.detail || 'Failed to read lifecycle'), {
			status: res.status
		});
	}
	return res.json();
};

export const refreshOrchestratorTerminals = async (
	token: string,
	url: string,
	key: string,
	body: {
		user_id?: string;
		policy_id?: string;
		only_idle?: boolean;
		reset?: boolean;
	},
	authType: string = 'bearer'
): Promise<object | null> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/terminal_servers/refresh`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			url: url.replace(/\/$/, ''),
			key,
			auth_type: authType,
			...body
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

/**
 * Verify a terminal server connection via the backend proxy.
 * Used for system/admin connections to avoid CORS issues and API key exposure.
 */
export const verifyTerminalServerConnection = async (token: string, connection: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/terminal_servers/verify`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...connection
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const verifyToolServerConnection = async (token: string, connection: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/tool_servers/verify`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...connection
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type RegisterOAuthClientForm = {
	url: string;
	client_id: string;
	client_name?: string;
	client_secret?: string;
	oauth_server_url?: string;
	oauth_scope?: string;
};

export const registerOAuthClient = async (
	token: string,
	formData: RegisterOAuthClientForm,
	type: null | string = null
) => {
	let error = null;

	const searchParams = type ? `?type=${type}` : '';
	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/oauth/clients/register${searchParams}`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...formData
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getOAuthClientAuthorizationUrl = (clientId: string, type: null | string = null) => {
	const oauthClientId = type ? `${type}:${clientId}` : clientId;
	return `${WEBUI_BASE_URL}/oauth/clients/${oauthClientId}/authorize`;
};

// Restore reads this to reject snapshots written by an older, incompatible client.
export const PENDING_OAUTH_CHAT_STATE_VERSION = 1;

export type PendingOAuthChatState = {
	selectedModels?: string[];
	selectedToolIds?: string[];
	selectedSkillIds?: string[];
	selectedFilterIds?: string[];
	webSearchEnabled?: boolean;
	imageGenerationEnabled?: boolean;
	codeInterpreterEnabled?: boolean;
	prompt?: string;
	returnTo?: string;
};

// Rejects absolute and protocol-relative ("//host") paths to prevent open redirects.
export const isSafeOAuthReturnPath = (path: unknown): path is string => {
	return typeof path === 'string' && path.startsWith('/') && !path.startsWith('//');
};

export const initiateOAuthRedirect = (
	tool: {
		id: string;
		serverId: string;
		authType?: string | null;
	},
	chatState: PendingOAuthChatState = {}
) => {
	sessionStorage.setItem('pendingOAuthToolId', tool.id);
	sessionStorage.setItem('oauthRedirectInProgressToolId', tool.id);

	// The OAuth callback always redirects to the site root, discarding the active
	// chat. Snapshot the chat config here so it survives the round-trip.
	try {
		// Models ride the existing one-shot sessionStorage.selectedModels channel
		// (consumed by new-chat init) rather than the snapshot, so restoring them
		// does not re-trigger the model-change reactive that wipes tool selection.
		const models = chatState.selectedModels?.filter(
			(id): id is string => typeof id === 'string' && id !== ''
		);
		if (models?.length) {
			sessionStorage.setItem('selectedModels', JSON.stringify(models));
		}

		sessionStorage.setItem(
			'pendingOAuthChatState',
			JSON.stringify({
				version: PENDING_OAUTH_CHAT_STATE_VERSION,
				pendingOAuthToolId: tool.id,
				selectedToolIds: chatState.selectedToolIds ?? [],
				selectedSkillIds: chatState.selectedSkillIds ?? [],
				selectedFilterIds: chatState.selectedFilterIds ?? [],
				webSearchEnabled: chatState.webSearchEnabled ?? false,
				imageGenerationEnabled: chatState.imageGenerationEnabled ?? false,
				codeInterpreterEnabled: chatState.codeInterpreterEnabled ?? false,
				prompt: chatState.prompt ?? '',
				returnTo: chatState.returnTo ?? ''
			})
		);
	} catch (err) {
		console.error('Failed to persist chat state before OAuth redirect:', err);
	}

	const authUrl = getOAuthClientAuthorizationUrl(tool.serverId, tool.authType ?? 'mcp');
	window.open(authUrl, '_self', 'noopener');
};

export const getCodeExecutionConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/code_execution`, {
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
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setCodeExecutionConfig = async (token: string, config: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/code_execution`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
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
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getModelsDefaults = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/models/defaults`, {
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
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getModelsConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/models`, {
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
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setModelsConfig = async (token: string, config: object) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/models`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
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
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getSubagentsConfig = async (token: string) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/subagents`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const setSubagentsConfig = async (token: string, config: object) => {
	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/subagents`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify(config)
	});
	if (!res.ok) throw await res.json();
	return res.json();
};

export const setDefaultPromptSuggestions = async (token: string, promptSuggestions: string) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/suggestions`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			suggestions: promptSuggestions
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getBanners = async (token: string): Promise<Banner[]> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/banners`, {
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
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const setBanners = async (token: string, banners: Banner[]) => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/configs/banners`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			banners: banners
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			console.error(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
