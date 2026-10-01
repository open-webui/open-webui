import { WEBUI_BASE_URL } from '$lib/constants';
import { apiJson, apiRequest, type ApiRequestOptions } from '$lib/apis/client';
import type { Config, Model } from '$lib/stores';

const BACKEND_CONFIG_REQUEST_TIMEOUT_MS = 10_000;

const webUiApi = async <T = unknown>(path: string, options: ApiRequestOptions = {}) => {
	return apiJson<T>(`${WEBUI_BASE_URL}${path}`, {
		...options,
		headers: {
			Accept: 'application/json',
			...(options.headers ?? {})
		}
	});
};

type CompletionResponse = {
	choices?: Array<{
		message?: {
			content?: string;
		};
	}>;
};

const getChoiceContent = (response: CompletionResponse | null | undefined) => {
	return response?.choices?.[0]?.message?.content ?? '';
};

type TaskMessage = {
	role: string;
	content: string;
	[key: string]: unknown;
};

export const getModels = async (token: string = '', base: boolean = false): Promise<Model[]> => {
	const res = (await webUiApi<{ data?: unknown[] }>(`/api/models${base ? '/base' : ''}`, {
		method: 'GET',
		token
	})) ?? { data: [] };

	return (res?.data ?? []) as Model[];
};

type ChatCompletedForm = {
	model: string;
	messages: string[];
	chat_id: string;
	session_id: string;
};

export const chatCompleted = async (token: string, body: ChatCompletedForm) => {
	return webUiApi('/api/chat/completed', {
		method: 'POST',
		token,
		body: JSON.stringify(body)
	});
};

type ChatActionForm = {
	model: string;
	messages: {
		id: string;
		role: string;
		content: unknown;
		info?: unknown;
		timestamp: number;
		sources?: unknown;
	}[];
	chat_id: string;
	id: string;
	session_id?: string;
	event?: unknown;
};

export const chatAction = async (token: string, action_id: string, body: ChatActionForm) => {
	return webUiApi(`/api/chat/actions/${action_id}`, {
		method: 'POST',
		token,
		body: JSON.stringify(body)
	});
};

export const stopTask = async (token: string, id: string) => {
	return webUiApi(`/api/tasks/stop/${id}`, {
		method: 'POST',
		token
	});
};

export const getTaskConfig = async (token: string = '') => {
	return webUiApi('/api/v1/tasks/config', {
		method: 'GET',
		token
	});
};

export const updateTaskConfig = async (token: string, config: object) => {
	return webUiApi('/api/v1/tasks/config/update', {
		method: 'POST',
		token,
		body: JSON.stringify(config)
	});
};

export const generateTitle = async (
	token: string = '',
	model: string,
	messages: string[],
	chat_id?: string
) => {
	const res = await webUiApi<CompletionResponse>('/api/v1/tasks/title/completions', {
		method: 'POST',
		token,
		body: JSON.stringify({
			model: model,
			messages: messages,
			...(chat_id && { chat_id: chat_id })
		})
	});

	return getChoiceContent(res).replace(/["']/g, '') || 'New Chat';
};

export const generateTags = async (
	token: string = '',
	model: string,
	messages: TaskMessage[],
	chat_id?: string
) => {
	const res = await webUiApi<CompletionResponse>('/api/v1/tasks/tags/completions', {
		method: 'POST',
		token,
		body: JSON.stringify({
			model: model,
			messages: messages,
			...(chat_id && { chat_id: chat_id })
		})
	});

	try {
		const response = getChoiceContent(res);
		const sanitizedResponse = response.replace(/['‘’`]/g, '"');
		const jsonStartIndex = sanitizedResponse.indexOf('{');
		const jsonEndIndex = sanitizedResponse.lastIndexOf('}');

		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = sanitizedResponse.substring(jsonStartIndex, jsonEndIndex + 1);
			const parsed = JSON.parse(jsonResponse);

			if (parsed && parsed.tags) {
				return Array.isArray(parsed.tags) ? parsed.tags : [];
			}
		}

		return [];
	} catch (e) {
		console.error('Failed to parse response: ', e);
		return [];
	}
};

export const generateEmoji = async (
	token: string = '',
	model: string,
	prompt: string,
	chat_id?: string
) => {
	const res = await webUiApi<CompletionResponse>('/api/v1/tasks/emoji/completions', {
		method: 'POST',
		token,
		body: JSON.stringify({
			model: model,
			prompt: prompt,
			...(chat_id && { chat_id: chat_id })
		})
	});

	const response = getChoiceContent(res).replace(/["']/g, '') || null;

	if (response && /\p{Extended_Pictographic}/u.test(response)) {
		return response.match(/\p{Extended_Pictographic}/gu)?.[0] ?? null;
	}

	return null;
};

export const generateQueries = async (
	token: string = '',
	model: string,
	messages: object[],
	prompt: string,
	type: string = 'web_search'
) => {
	const res = await webUiApi<CompletionResponse>('/api/v1/tasks/queries/completions', {
		method: 'POST',
		token,
		body: JSON.stringify({
			model: model,
			messages: messages,
			prompt: prompt,
			type: type
		})
	});

	const response = getChoiceContent(res);

	try {
		const jsonStartIndex = response.indexOf('{');
		const jsonEndIndex = response.lastIndexOf('}');

		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);
			const parsed = JSON.parse(jsonResponse);

			if (parsed && parsed.queries) {
				return Array.isArray(parsed.queries) ? parsed.queries : [];
			}

			return [];
		}

		return [response];
	} catch (e) {
		console.error('Failed to parse response: ', e);
		return [response];
	}
};

export const generateAutoCompletion = async (
	token: string = '',
	model: string,
	prompt: string,
	messages?: object[],
	type: string = 'search query'
) => {
	const res = await webUiApi<CompletionResponse>('/api/v1/tasks/auto/completions', {
		method: 'POST',
		token,
		body: JSON.stringify({
			model: model,
			prompt: prompt,
			...(messages && { messages: messages }),
			type: type,
			stream: false
		})
	});

	const response = getChoiceContent(res);

	try {
		const jsonStartIndex = response.indexOf('{');
		const jsonEndIndex = response.lastIndexOf('}');

		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);
			const parsed = JSON.parse(jsonResponse);

			if (parsed && parsed.text) {
				return parsed.text;
			}

			return '';
		}

		return response;
	} catch (e) {
		console.error('Failed to parse response: ', e);
		return response;
	}
};

export const generateMoACompletion = async (
	token: string = '',
	model: string,
	prompt: string,
	responses: string[]
): Promise<[Response, AbortController]> => {
	const controller = new AbortController();

	const res = await apiRequest(`${WEBUI_BASE_URL}/api/v1/tasks/moa/completions`, {
		signal: controller.signal,
		method: 'POST',
		token,
		headers: {
			Accept: 'application/json'
		},
		body: JSON.stringify({
			model: model,
			prompt: prompt,
			responses: responses,
			stream: true
		})
	});

	return [res as Response, controller];
};

export const getPipelinesList = async (token: string = '') => {
	const res = await webUiApi<{ data?: unknown[] }>('/api/v1/pipelines/list', {
		method: 'GET',
		token
	});

	return res?.data ?? [];
};

export const uploadPipeline = async (token: string, file: File, urlIdx: string) => {
	const formData = new FormData();
	formData.append('file', file);
	formData.append('urlIdx', urlIdx);

	return webUiApi('/api/v1/pipelines/upload', {
		method: 'POST',
		token,
		body: formData
	});
};

export const downloadPipeline = async (token: string, url: string, urlIdx: string) => {
	return webUiApi('/api/v1/pipelines/add', {
		method: 'POST',
		token,
		body: JSON.stringify({
			url: url,
			urlIdx: urlIdx
		})
	});
};

export const deletePipeline = async (token: string, id: string, urlIdx: string) => {
	return webUiApi('/api/v1/pipelines/delete', {
		method: 'DELETE',
		token,
		body: JSON.stringify({
			id: id,
			urlIdx: urlIdx
		})
	});
};

export const getPipelines = async (token: string, urlIdx?: string) => {
	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	const res = await webUiApi<{ data?: unknown[] }>(
		`/api/v1/pipelines/?${searchParams.toString()}`,
		{
			method: 'GET',
			token
		}
	);

	return res?.data ?? [];
};

export const getPipelineValves = async (token: string, pipeline_id: string, urlIdx: string) => {
	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	return webUiApi(`/api/v1/pipelines/${pipeline_id}/valves?${searchParams.toString()}`, {
		method: 'GET',
		token
	});
};

export const getPipelineValvesSpec = async (token: string, pipeline_id: string, urlIdx: string) => {
	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	return webUiApi(`/api/v1/pipelines/${pipeline_id}/valves/spec?${searchParams.toString()}`, {
		method: 'GET',
		token
	});
};

export const updatePipelineValves = async (
	token: string = '',
	pipeline_id: string,
	valves: object,
	urlIdx: string
) => {
	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	return webUiApi(`/api/v1/pipelines/${pipeline_id}/valves/update?${searchParams.toString()}`, {
		method: 'POST',
		token,
		body: JSON.stringify(valves)
	});
};

export const getBackendConfig = async (token?: string): Promise<Config | null> => {
	const controller = new AbortController();
	const timeoutId = setTimeout(() => controller.abort(), BACKEND_CONFIG_REQUEST_TIMEOUT_MS);

	try {
		return await webUiApi<Config>('/api/config', {
			method: 'GET',
			credentials: 'include',
			signal: controller.signal,
			...(token !== undefined
				? {
						includeAuth: true,
						token
					}
				: {
						includeAuth: false
					})
		});
	} finally {
		clearTimeout(timeoutId);
	}
};

export const getChangelog = async (locale: string = 'en') => {
	return webUiApi(`/api/changelog?locale=${encodeURIComponent(locale)}`, {
		method: 'GET'
	});
};

export const getModelFilterConfig = async (token: string) => {
	return webUiApi('/api/config/model/filter', {
		method: 'GET',
		token
	});
};

export const updateModelFilterConfig = async (
	token: string,
	enabled: boolean,
	models: string[]
) => {
	return webUiApi('/api/config/model/filter', {
		method: 'POST',
		token,
		body: JSON.stringify({
			enabled: enabled,
			models: models
		})
	});
};

export const getWebhookUrl = async (token: string) => {
	const res = await webUiApi<{ url?: string }>('/api/webhook', {
		method: 'GET',
		token
	});

	return res?.url ?? '';
};

export const updateWebhookUrl = async (token: string, url: string) => {
	const res = await webUiApi<{ url?: string }>('/api/webhook', {
		method: 'POST',
		token,
		body: JSON.stringify({
			url: url
		})
	});

	return res?.url ?? '';
};

export const getCommunitySharingEnabledStatus = async (token: string) => {
	return webUiApi('/api/community_sharing', {
		method: 'GET',
		token
	});
};

export const toggleCommunitySharingEnabledStatus = async (token: string) => {
	return webUiApi('/api/community_sharing/toggle', {
		method: 'GET',
		token
	});
};

export const getModelConfig = async (token: string): Promise<GlobalModelConfig> => {
	const res = await webUiApi<{ models?: GlobalModelConfig }>('/api/config/models', {
		method: 'GET',
		token
	});

	return res?.models ?? [];
};

export interface ModelConfig {
	id: string;
	name: string;
	name_fr?: string;
	meta: ModelMeta;
	base_model_id?: string;
	params: ModelParams;
}

export interface ModelMeta {
	description?: string;
	description_fr?: string;
	capabilities?: {
		vision?: boolean;
		usage?: boolean;
		[key: string]: unknown;
	};
	profile_image_url?: string;
	toolIds?: string[];
	filterIds?: string[];
	actionIds?: string[];
	knowledge?: unknown[];
	hidden?: boolean;
	tags?: string[];
	tags_fr?: string[];
}

export interface ModelParams {
	stream_response?: boolean;
	stop?: string[];
	system?: string;
	[key: string]: unknown;
}

export type GlobalModelConfig = ModelConfig[];

export const updateModelConfig = async (token: string, config: GlobalModelConfig) => {
	return webUiApi('/api/config/models', {
		method: 'POST',
		token,
		body: JSON.stringify({
			models: config
		})
	});
};
