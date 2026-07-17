import { WEBUI_API_BASE_URL } from '$lib/constants';

export type LangfuseConnection = {
	id: string;
	name?: string;
	url?: string;
	public_key?: string;
	secret_key?: string;
	secret_key_set?: boolean;
	enabled?: boolean;
};

export type LangfusePromptSummary = {
	name: string;
	type?: string;
	version?: number | string;
	labels?: string[];
};

export type LangfusePromptsResponse = {
	data?: LangfusePromptSummary[];
	meta?: {
		page?: number;
		limit?: number;
		totalItems?: number;
		totalPages?: number;
	};
};

export type LangfusePromptResponse = {
	name: string;
	content: string;
	version?: number | string | null;
	type?: string;
	labels?: string[];
};

export type LangfusePromptsOptions = {
	page?: number;
	limit?: number;
	name?: string;
	label?: string;
};

export type LangfusePromptOptions = {
	label?: string;
	version?: string;
};

const authHeaders = (token: string): Record<string, string> => ({
	Accept: 'application/json',
	'Content-Type': 'application/json',
	authorization: `Bearer ${token}`
});

export type LangfuseBlockedConnection = {
	connection_id: string;
	action?: string;
	bound_models: number;
};

export type LangfuseOrphanErrorDetail = {
	message: string;
	blocked_connections: LangfuseBlockedConnection[];
};

export type LangfuseConfigSaveErrorToast = {
	title: string;
	description?: string;
};

type TranslateFn = (key: string, options?: Record<string, string | number>) => string;

export const isLangfuseOrphanErrorDetail = (
	value: unknown
): value is LangfuseOrphanErrorDetail => {
	if (!value || typeof value !== 'object') {
		return false;
	}

	const detail = value as Record<string, unknown>;
	if (typeof detail.message !== 'string' || !Array.isArray(detail.blocked_connections)) {
		return false;
	}

	return detail.blocked_connections.every((item) => {
		if (!item || typeof item !== 'object') {
			return false;
		}

		const blocked = item as LangfuseBlockedConnection;
		return (
			typeof blocked.connection_id === 'string' &&
			typeof blocked.bound_models === 'number'
		);
	});
};

export const formatApiError = (err: unknown): unknown => {
	if (err === null || typeof err !== 'object' || !('detail' in err)) {
		return err;
	}

	const detail = (err as { detail?: unknown }).detail;
	if (detail === undefined || detail === null) {
		return err;
	}

	if (Array.isArray(detail)) {
		return detail
			.map((item: { msg?: string }) => item?.msg || JSON.stringify(item))
			.join(', ');
	}

	return detail;
};

export const formatLangfuseConfigSaveError = (
	err: unknown,
	t: TranslateFn,
	options: { connectionLabel?: (connectionId: string) => string | undefined } = {}
): LangfuseConfigSaveErrorToast => {
	const detail = isLangfuseOrphanErrorDetail(err)
		? err
		: isLangfuseOrphanErrorDetail(
					err && typeof err === 'object' && 'detail' in err
						? (err as { detail?: unknown }).detail
						: null
				)
			? ((err as { detail?: unknown }).detail as LangfuseOrphanErrorDetail)
			: null;

	if (detail) {
		const title = t(
			'Cannot remove or disable Langfuse connections that are bound to models. Detach or rebind affected models first.'
		);
		const description = detail.blocked_connections
			.map((item) => {
				const connectionId =
					options.connectionLabel?.(item.connection_id) ?? item.connection_id;
				return t('{{connectionId}}: {{count}} bound models', {
					connectionId,
					count: item.bound_models
				});
			})
			.join('\n');

		return { title, description };
	}

	if (typeof err === 'string' && err.trim()) {
		return { title: err };
	}

	return { title: t('Failed to save Langfuse configuration') };
};

/** Admin-only global browse — use model-scoped helpers in `$lib/apis/models/systemPrompt` for model editors. */
export const getLangfuseConnections = async (
	token: string
): Promise<{ connections: LangfuseConnection[] }> => {
	let error = null;

	const res = await fetch(`${WEBUI_API_BASE_URL}/langfuse/connections`, {
		method: 'GET',
		headers: authHeaders(token)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = formatApiError(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res ?? { connections: [] };
};

export const getLangfusePrompts = async (
	token: string,
	connectionId: string,
	opts: LangfusePromptsOptions = {}
): Promise<LangfusePromptsResponse> => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (opts.page != null) searchParams.append('page', String(opts.page));
	if (opts.limit != null) searchParams.append('limit', String(opts.limit));
	if (opts.name) searchParams.append('name', opts.name);
	if (opts.label) searchParams.append('label', opts.label);

	const query = searchParams.toString();
	const url = `${WEBUI_API_BASE_URL}/langfuse/connections/${encodeURIComponent(connectionId)}/prompts${query ? `?${query}` : ''}`;

	const res = await fetch(url, {
		method: 'GET',
		headers: authHeaders(token)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = formatApiError(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res ?? { data: [] };
};

export const getLangfusePrompt = async (
	token: string,
	connectionId: string,
	name: string,
	opts: LangfusePromptOptions = {}
): Promise<LangfusePromptResponse> => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (opts.label) searchParams.append('label', opts.label);
	if (opts.version) searchParams.append('version', opts.version);

	const query = searchParams.toString();
	const url = `${WEBUI_API_BASE_URL}/langfuse/connections/${encodeURIComponent(connectionId)}/prompts/${encodeURIComponent(name)}${query ? `?${query}` : ''}`;

	const res = await fetch(url, {
		method: 'GET',
		headers: authHeaders(token)
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = formatApiError(err);
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
