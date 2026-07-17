import { WEBUI_API_BASE_URL } from '$lib/constants';

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
};

export type PatchModelSystemPromptBindingForm = {
	source?: ModelSystemPromptSource;
	connection_id?: string | null;
	external_name?: string | null;
	external_label?: string | null;
	external_version?: string | null;
	cache_ttl_seconds?: number | null;
};

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
	modelId: string
): Promise<ModelSystemPromptBinding | null> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/binding?${searchParams.toString()}`,
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
			error = err;
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
	page: number = 0
): Promise<ModelSystemPromptVersion[]> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);
	searchParams.append('page', page.toString());

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/history?${searchParams.toString()}`,
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
			error = err;
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
		`${WEBUI_API_BASE_URL}/models/system-prompt/history/${versionId}?${searchParams.toString()}`,
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
			error = err;
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
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/versions?${searchParams.toString()}`,
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
			error = err;
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
	versionId: string
): Promise<ModelSystemPromptBinding> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/active?${searchParams.toString()}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				authorization: `Bearer ${token}`
			},
			body: JSON.stringify({ version_id: versionId })
		}
	)
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

export const deleteModelSystemPromptHistoryEntry = async (
	token: string,
	modelId: string,
	versionId: string
): Promise<boolean> => {
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/history/${versionId}?${searchParams.toString()}`,
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
			error = err;
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
	let error = null;

	const searchParams = new URLSearchParams();
	searchParams.append('id', modelId);

	const res = await fetch(
		`${WEBUI_API_BASE_URL}/models/system-prompt/binding?${searchParams.toString()}`,
		{
			method: 'PATCH',
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
			error = err;
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
			error = err;
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
			error = err;
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
			error = err;
			console.error(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
