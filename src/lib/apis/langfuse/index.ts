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
			error = err;
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
			error = err;
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
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
