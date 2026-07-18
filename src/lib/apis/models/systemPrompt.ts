import { WEBUI_API_BASE_URL } from '$lib/constants';
import {
	formatApiError,
	type LangfuseConnection,
	type LangfusePromptOptions,
	type LangfusePromptResponse,
	type LangfusePromptsOptions,
	type LangfusePromptsResponse
} from '$lib/apis/langfuse';

export type ModelSystemPromptSource = 'local' | 'langfuse';

export type ModelSystemPromptBinding = {
	model_id: string;
	source: ModelSystemPromptSource;
	active_version_id?: string | null;
	connection_id?: string | null;
	external_name?: string | null;
	external_label?: string | null;
	external_version?: string | null;
	cached_content?: string | null;
	cached_version?: string | null;
	cached_at?: number | null;
	cache_ttl_seconds?: number | null;
	updated_at?: number | null;
};

export type ModelSystemPromptVersionUser = {
	id: string;
	name: string;
	email: string;
	profile_image_url?: string;
};

export type ModelSystemPromptVersion = {
	id: string;
	model_id: string;
	content: string;
	commit_message?: string | null;
	user_id: string;
	created_at: number;
	user?: ModelSystemPromptVersionUser | null;
};

export type CreateModelSystemPromptVersionForm = {
	content: string;
	commit_message?: string;
	set_active?: boolean;
	expected_updated_at?: number | null;
};

export type SetActiveModelSystemPromptVersionForm = {
	version_id: string;
	expected_updated_at?: number | null;
};

export type PatchModelSystemPromptBindingForm = {
	source?: ModelSystemPromptSource;
	connection_id?: string | null;
	external_name?: string | null;
	external_label?: string | null;
	external_version?: string | null;
	cache_ttl_seconds?: number | null;
	expected_updated_at?: number | null;
};

export type ModelSystemPromptBindingConflictDetail = {
	message?: string;
	current_updated_at?: number | null;
};

export class ModelSystemPromptBindingConflictError extends Error {
	status = 409;
	current_updated_at?: number | null;

	constructor(detail: ModelSystemPromptBindingConflictDetail) {
		super(detail.message ?? 'System prompt binding was modified by another request');
		this.name = 'ModelSystemPromptBindingConflictError';
		this.current_updated_at = detail.current_updated_at;
	}
}

export type LangfusePromptPreviewForm = {
	connection_id?: string | null;
	external_name?: string | null;
	external_label?: string | null;
	external_version?: string | null;
};

export type LangfusePromptActionResponse = {
	content: string;
	prompt_name?: string | null;
	prompt_version?: string | null;
	source: 'langfuse';
};

export type DetachSystemPromptResponse = {
	binding: ModelSystemPromptBinding;
	version: ModelSystemPromptVersion;
};

export const getModelSystemPromptBinding = async (
	token: string,
	modelId: string,
	signal?: AbortSignal
): Promise<ModelSystemPromptBinding | null> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/binding?${searchParams.toString()}`,
		{
			method: 'GET',
			signal,
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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

export const getModelSystemPromptHistory = async (
	token: string,
	modelId: string,
	page: number = 0,
	signal?: AbortSignal
): Promise<ModelSystemPromptVersion[]> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);
	searchParams.append('page', page.toString());

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/history?${searchParams.toString()}`,
		{
			method: 'GET',
			signal,
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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

export const getModelSystemPromptHistoryEntry = async (
	token: string,
	modelId: string,
	versionId: string
): Promise<ModelSystemPromptVersion> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/history/${encodeURIComponent(versionId)}?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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

export const createModelSystemPromptVersion = async (
	token: string,
	modelId: string,
	form: CreateModelSystemPromptVersionForm
): Promise<ModelSystemPromptVersion> => {
	let error: unknown = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const headers: Record<string, string> = {
		Accept: 'application/json',
		'Content-Type': 'application/json',
		authorization: `Bearer ${token}`
	};

	if (form.expected_updated_at != null) {
		headers['If-Match'] = `"${form.expected_updated_at}"`;
	}

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/versions?${searchParams.toString()}`,
		{
			method: 'POST',
			headers,
			body: JSON.stringify(form)
		}
	)
		.then(async (res) => {
			if (!res.ok) {
				const err = await res.json();
				if (res.status === 409) {
					const detail: ModelSystemPromptBindingConflictDetail =
						typeof err.detail === 'object' && err.detail !== null
							? err.detail
							: { message: String(err.detail ?? 'Conflict') };
					throw new ModelSystemPromptBindingConflictError(detail);
				}
				throw err.detail ?? err;
			}
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

export const setActiveModelSystemPromptVersion = async (
	token: string,
	modelId: string,
	form: SetActiveModelSystemPromptVersionForm
): Promise<ModelSystemPromptBinding> => {
	let error: unknown = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const headers: Record<string, string> = {
		Accept: 'application/json',
		'Content-Type': 'application/json',
		authorization: `Bearer ${token}`
	};

	if (form.expected_updated_at != null) {
		headers['If-Match'] = `"${form.expected_updated_at}"`;
	}

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/active?${searchParams.toString()}`,
		{
			method: 'POST',
			headers,
			body: JSON.stringify(form)
		}
	)
		.then(async (res) => {
			if (!res.ok) {
				const err = await res.json();
				if (res.status === 409) {
					const detail: ModelSystemPromptBindingConflictDetail =
						typeof err.detail === 'object' && err.detail !== null
							? err.detail
							: { message: String(err.detail ?? 'Conflict') };
					throw new ModelSystemPromptBindingConflictError(detail);
				}
				throw err.detail ?? err;
			}
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

export const deleteModelSystemPromptHistoryEntry = async (
	token: string,
	modelId: string,
	versionId: string
): Promise<boolean> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/history/${encodeURIComponent(versionId)}?${searchParams.toString()}`,
		{
			method: 'DELETE',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
		})
		.catch((err) => {
			error = formatApiError(err);
			console.error(err);
			return false;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const patchModelSystemPromptBinding = async (
	token: string,
	modelId: string,
	form: PatchModelSystemPromptBindingForm
): Promise<ModelSystemPromptBinding> => {
	let error: unknown = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const headers: Record<string, string> = {
		Accept: 'application/json',
		'Content-Type': 'application/json',
		authorization: `Bearer ${token}`
	};

	if (form.expected_updated_at != null) {
		headers['If-Match'] = `"${form.expected_updated_at}"`;
	}

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/binding?${searchParams.toString()}`,
		{
			method: 'PATCH',
			headers,
			body: JSON.stringify(form)
		}
	)
		.then(async (res) => {
			if (!res.ok) {
				const err = await res.json();
				if (res.status === 409) {
					const detail: ModelSystemPromptBindingConflictDetail =
						typeof err.detail === 'object' && err.detail !== null
							? err.detail
							: { message: String(err.detail ?? 'Conflict') };
					throw new ModelSystemPromptBindingConflictError(detail);
				}
				throw err.detail ?? err;
			}
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

export const syncModelSystemPromptFromLangfuse = async (
	token: string,
	modelId: string
): Promise<LangfusePromptActionResponse> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/langfuse/sync?${searchParams.toString()}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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

export const previewModelSystemPromptFromLangfuse = async (
	token: string,
	modelId: string,
	form: LangfusePromptPreviewForm = {}
): Promise<LangfusePromptActionResponse> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/langfuse/preview?${searchParams.toString()}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify(form)
		}
	)
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

export const getModelLangfuseConnections = async (
	token: string,
	modelId: string,
	signal?: AbortSignal
): Promise<{ connections: LangfuseConnection[] }> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/langfuse/connections?${searchParams.toString()}`,
		{
			method: 'GET',
			signal,
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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

export const getModelLangfusePrompts = async (
	token: string,
	modelId: string,
	connectionId: string,
	opts: LangfusePromptsOptions = {},
	signal?: AbortSignal
): Promise<LangfusePromptsResponse> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);
	searchParams.append('connection_id', connectionId);
	if (opts.page != null) searchParams.append('page', String(opts.page));
	if (opts.limit != null) searchParams.append('limit', String(opts.limit));
	if (opts.name) searchParams.append('name', opts.name);
	if (opts.label) searchParams.append('label', opts.label);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/langfuse/prompts?${searchParams.toString()}`,
		{
			method: 'GET',
			signal,
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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

export const getModelLangfusePrompt = async (
	token: string,
	modelId: string,
	connectionId: string,
	name: string,
	opts: LangfusePromptOptions = {}
): Promise<LangfusePromptResponse> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);
	searchParams.append('connection_id', connectionId);
	if (opts.label) searchParams.append('label', opts.label);
	if (opts.version) searchParams.append('version', opts.version);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/langfuse/prompts/${encodeURIComponent(name)}?${searchParams.toString()}`,
		{
			method: 'GET',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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

export const detachModelSystemPromptToLocal = async (
	token: string,
	modelId: string
): Promise<DetachSystemPromptResponse> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/detach?${searchParams.toString()}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			}
		}
	)
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
