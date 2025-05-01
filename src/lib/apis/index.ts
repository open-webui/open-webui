import { convertOpenApiToToolPayload } from '$lib/utils';
import { getOpenAIModelsDirect } from './openai';
import { parse } from 'yaml';
import { toast } from 'svelte-sonner';
import type { OpenAIConnection, Model, ServerConfig, I18n, GlobalModelConfig } from './types';
import { webuiApiClient, webuiClient } from './clients';

// API Types
type ChatCompletedForm = {
	model: string;
	messages: string[];
	chat_id: string;
	session_id: string;
};

type ChatActionForm = {
	model: string;
	messages: string[];
	chat_id: string;
};

interface ApiResponse<T> {
	data: T;
}

interface TitleResponse {
	choices: Array<{
		message: {
			content: string;
		};
	}>;
}

interface WebhookResponse {
	url: string;
}

interface ModelConfigResponse {
	models: GlobalModelConfig;
}

// Refactored API endpoints using webuiApiClient
export const chatCompleted = async (token: string, body: ChatCompletedForm) =>
	webuiApiClient.post('/chat/completed', body, { token });

export const chatAction = async (token: string, action_id: string, body: ChatActionForm) =>
	webuiApiClient.post(`/chat/actions/${action_id}`, body, { token });

export const stopTask = async (token: string, id: string) =>
	webuiApiClient.post(`/tasks/stop/${id}`, null, { token });

export const getTaskIdsByChatId = async (token: string, chat_id: string) =>
	webuiApiClient.get(`/tasks/chat/${chat_id}`, { token });

export const getToolServerData = async (token: string, url: string) => {
	const response = await webuiApiClient.get<string | Record<string, unknown>>(url, { token });

	if (
		typeof response === 'string' ||
		url.toLowerCase().endsWith('.yaml') ||
		url.toLowerCase().endsWith('.yml')
	) {
		const text = typeof response === 'string' ? response : JSON.stringify(response);
		const parsed = parse(text);
		return {
			openapi: parsed,
			info: parsed.info,
			specs: convertOpenApiToToolPayload(parsed)
		};
	}

	return {
		openapi: response,
		info: response.info,
		specs: convertOpenApiToToolPayload(response)
	};
};

export const getTaskConfig = async (token: string = '') =>
	webuiApiClient.get('/tasks/config', { token });

export const updateTaskConfig = async (token: string, config: object) =>
	webuiApiClient.post('/tasks/config/update', config, { token });

export const generateTitle = async (
	token: string = '',
	model: string,
	messages: string[],
	chat_id?: string
) => {
	const response = await webuiApiClient.post<ApiResponse<TitleResponse>>(
		'/tasks/title/completions',
		{
			model,
			messages,
			...(chat_id && { chat_id })
		},
		{ token }
	);
	return response.data?.choices[0]?.message?.content.replace(/["']/g, '') ?? 'New Chat';
};

// Public endpoints using webuiClient
export const getBackendConfig = async () => webuiClient.get('/config', { withCredentials: true });

export const getChangelog = async () => webuiClient.get('/changelog');

export const getVersionUpdates = async (token: string) =>
	webuiClient.get('/version/updates', { token });

export const getModelFilterConfig = async (token: string) =>
	webuiApiClient.get('/config/model/filter', { token });

export const updateModelFilterConfig = async (token: string, enabled: boolean, models: string[]) =>
	webuiApiClient.post('/config/model/filter', { enabled, models }, { token });

export const getWebhookUrl = async (token: string) => {
	const response = await webuiApiClient.get<ApiResponse<WebhookResponse>>('/webhook', { token });
	return response.data.url;
};

export const updateWebhookUrl = async (token: string, url: string) => {
	const response = await webuiApiClient.post<ApiResponse<WebhookResponse>>(
		'/webhook',
		{ url },
		{ token }
	);
	return response.data.url;
};

export const getCommunitySharingEnabledStatus = async (token: string) =>
	webuiApiClient.get('/community_sharing', { token });

export const toggleCommunitySharingEnabledStatus = async (token: string) =>
	webuiApiClient.get('/community_sharing/toggle', { token });

export const getModelConfig = async (token: string): Promise<GlobalModelConfig> => {
	const response = await webuiApiClient.get<ApiResponse<ModelConfigResponse>>('/config/models', {
		token
	});
	return response.data.models;
};

export const updateModelConfig = async (token: string, config: GlobalModelConfig) =>
	webuiApiClient.post('/config/models', { models: config }, { token });

export const getModels = async (
	token: string = '',
	connections: OpenAIConnection | null = null,
	base: boolean = false
): Promise<Model[]> => {
	try {
		const response = await webuiApiClient.get<Model[]>(`/models${base ? '/base' : ''}`, {
			token
		});
		let models = response;
		console.log('---getModels', base, models);
		if (connections && !base) {
			let localModels: Model[] = [];

			const requests = [];
			for (const idx in connections.OPENAI_API_BASE_URLS) {
				const url = connections.OPENAI_API_BASE_URLS[idx];

				if (idx.toString() in connections.OPENAI_API_CONFIGS) {
					const apiConfig = connections.OPENAI_API_CONFIGS[idx.toString()] ?? {};

					const enable = apiConfig?.enable ?? true;
					const modelIds: string[] = apiConfig?.model_ids ?? [];

					if (enable) {
						if (modelIds.length > 0) {
							const modelList = {
								object: 'list',
								data: modelIds.map(
									(modelId) =>
										({
											id: modelId,
											name: modelId,
											owned_by: 'openai',
											openai: { id: modelId },
											urlIdx: idx,
											tags: [],
											direct: true
										}) as Model
								)
							};

							requests.push(Promise.resolve(modelList));
						} else {
							requests.push(
								getOpenAIModelsDirect(url, connections.OPENAI_API_KEYS[idx]).catch((error) => {
									console.error('Failed to get OpenAI models:', error);
									return {
										object: 'list',
										data: [],
										urlIdx: idx
									};
								})
							);
						}
					} else {
						requests.push(
							Promise.resolve({
								object: 'list',
								data: [],
								urlIdx: idx
							})
						);
					}
				}
			}

			const responses = await Promise.all(requests);

			for (const idx in responses) {
				const response = responses[idx];
				const apiConfig = connections.OPENAI_API_CONFIGS[idx.toString()] ?? {};

				let responseModels = Array.isArray(response) ? response : (response?.data ?? []);
				responseModels = responseModels.map((model: Partial<Model>) => ({
					id: model.id!,
					name: model.name!,
					owned_by: model.owned_by!,
					openai: { id: model.id! },
					urlIdx: idx,
					tags: model.tags ?? [],
					direct: true
				}));

				const prefixId = apiConfig.prefix_id;
				if (prefixId) {
					for (const model of responseModels) {
						model.id = `${prefixId}.${model.id}`;
					}
				}

				const tags = apiConfig.tags;
				if (tags) {
					for (const model of responseModels) {
						model.tags = tags;
					}
				}

				localModels = localModels.concat(responseModels);
			}

			models = models.concat(
				localModels.map((model) => ({
					...model,
					name: model?.name ?? model?.id,
					direct: true
				}))
			);

			// Remove duplicates
			const modelsMap: Record<string, Model> = {};
			for (const model of models) {
				modelsMap[model.id] = model;
			}

			models = Object.values(modelsMap);
		}

		return models;
	} catch (error) {
		console.error('Failed to get models:', error);
		throw error;
	}
};

export const getToolServersData = async (i18n: I18n, servers: ServerConfig[]) => {
	return (
		await Promise.all(
			servers
				.filter((server) => server.config.enable)
				.map(async (server) => {
					const data = await getToolServerData(
						(server.auth_type ?? 'bearer') === 'bearer' ? server.key : localStorage.token,
						server.url + '/' + (server.path ?? 'openapi.json')
					).catch((error) => {
						console.error('Failed to connect to tool server:', error);
						toast.error(
							i18n.t(`Failed to connect to {{URL}} OpenAPI tool server`, {
								URL: server.url + '/' + (server.path ?? 'openapi.json')
							})
						);
						return null;
					});

					if (data) {
						const { openapi, info, specs } = data;
						return {
							url: server.url,
							openapi: openapi,
							info: info,
							specs: specs
						};
					}
					return null;
				})
		)
	).filter((server): server is NonNullable<typeof server> => server !== null);
};

interface OpenAPIOperation {
	operationId: string;
	parameters?: Array<{
		name: string;
		in: string;
	}>;
	requestBody?: {
		content: Record<string, unknown>;
	};
}

interface OpenAPISpec {
	paths: Record<string, Record<string, OpenAPIOperation>>;
}

interface ServerData {
	openapi: OpenAPISpec;
	info: unknown;
	specs: unknown;
}

export const executeToolServer = async (
	token: string,
	url: string,
	name: string,
	params: Record<string, unknown>,
	serverData: ServerData
) => {
	try {
		// Find the matching operationId in the OpenAPI spec
		const matchingRoute = Object.entries(serverData.openapi.paths).find(([, methods]) =>
			Object.entries(methods).some(([, operation]) => operation.operationId === name)
		);

		if (!matchingRoute) {
			throw new Error(`No matching route found for operationId: ${name}`);
		}

		const [routePath, methods] = matchingRoute;

		const methodEntry = Object.entries(methods).find(
			([, operation]) => operation.operationId === name
		);

		if (!methodEntry) {
			throw new Error(`No matching method found for operationId: ${name}`);
		}

		const [httpMethod, operation] = methodEntry;

		// Split parameters by type
		const pathParams: Record<string, unknown> = {};
		const queryParams: Record<string, unknown> = {};
		let bodyParams = {};

		if (operation.parameters) {
			operation.parameters.forEach((param) => {
				const paramName = param.name;
				const paramIn = param.in;
				if (Object.prototype.hasOwnProperty.call(params, paramName)) {
					if (paramIn === 'path') {
						pathParams[paramName] = params[paramName];
					} else if (paramIn === 'query') {
						queryParams[paramName] = params[paramName];
					}
				}
			});
		}

		let finalUrl = `${url}${routePath}`;

		// Replace path parameters
		Object.entries(pathParams).forEach(([key, value]) => {
			finalUrl = finalUrl.replace(new RegExp(`{${key}}`, 'g'), encodeURIComponent(String(value)));
		});

		// Append query parameters to URL if any
		if (Object.keys(queryParams).length > 0) {
			const queryString = new URLSearchParams(
				Object.entries(queryParams).map(([k, v]) => [k, String(v)])
			).toString();
			finalUrl += `?${queryString}`;
		}

		// Handle requestBody
		if (operation.requestBody?.content) {
			if (params !== undefined) {
				bodyParams = params;
			} else {
				throw new Error(`Request body expected for operation '${name}' but none found.`);
			}
		}

		// Make the request using webuiApiClient
		const requestOptions = {
			token,
			headers: { 'Content-Type': 'application/json' }
		};

		if (['post', 'put', 'patch'].includes(httpMethod.toLowerCase())) {
			return await webuiApiClient.post(finalUrl, bodyParams, requestOptions);
		} else if (httpMethod.toLowerCase() === 'delete') {
			return await webuiApiClient.del(finalUrl, bodyParams, requestOptions);
		} else {
			return await webuiApiClient.get(finalUrl, requestOptions);
		}
	} catch (error) {
		console.error('API Request Error:', error);
		return { error: error instanceof Error ? error.message : String(error) };
	}
};

export const getPipelinesList = async (token: string = '') => {
	try {
		const response = await webuiApiClient.get('/pipelines/list', { token });
		return response ?? [];
	} catch (error) {
		console.error(error);
		throw error;
	}
};

export const uploadPipeline = async (token: string, file: File, urlIdx: string) => {
	try {
		const formData = new FormData();
		formData.append('file', file);
		formData.append('urlIdx', urlIdx);

		return await webuiApiClient.post('/pipelines/upload', formData, {
			token,
			headers: { 'Content-Type': 'multipart/form-data' }
		});
	} catch (error) {
		console.error('Failed to upload pipeline:', error);
		throw error;
	}
};

export const downloadPipeline = async (token: string, url: string, urlIdx: string) => {
	try {
		return await webuiApiClient.post('/pipelines/add', { url, urlIdx }, { token });
	} catch (error) {
		console.error('Failed to download pipeline:', error);
		throw error;
	}
};

export const deletePipeline = async (token: string, id: string, urlIdx: string) => {
	try {
		return await webuiApiClient.del('/pipelines/delete', { id, urlIdx }, { token });
	} catch (error) {
		console.error('Failed to delete pipeline:', error);
		throw error;
	}
};

export const getPipelines = async (token: string, urlIdx?: string) => {
	try {
		const searchParams = new URLSearchParams();
		if (urlIdx !== undefined) {
			searchParams.append('urlIdx', urlIdx);
		}

		const response = await webuiApiClient.get(`/pipelines/?${searchParams.toString()}`, { token });
		return response ?? [];
	} catch (error) {
		console.error(error);
		throw error;
	}
};

export const getPipelineValves = async (token: string, pipeline_id: string, urlIdx: string) => {
	try {
		const searchParams = new URLSearchParams();
		if (urlIdx !== undefined) {
			searchParams.append('urlIdx', urlIdx);
		}

		return await webuiApiClient.get(`/pipelines/${pipeline_id}/valves?${searchParams.toString()}`, {
			token
		});
	} catch (error) {
		console.error('Failed to get pipeline valves:', error);
		throw error;
	}
};

export const getPipelineValvesSpec = async (token: string, pipeline_id: string, urlIdx: string) => {
	try {
		const searchParams = new URLSearchParams();
		if (urlIdx !== undefined) {
			searchParams.append('urlIdx', urlIdx);
		}

		return await webuiApiClient.get(
			`/pipelines/${pipeline_id}/valves/spec?${searchParams.toString()}`,
			{ token }
		);
	} catch (error) {
		console.error('Failed to get pipeline valves spec:', error);
		throw error;
	}
};

export const updatePipelineValves = async (
	token: string = '',
	pipeline_id: string,
	valves: object,
	urlIdx: string
) => {
	try {
		const searchParams = new URLSearchParams();
		if (urlIdx !== undefined) {
			searchParams.append('urlIdx', urlIdx);
		}

		return await webuiApiClient.post(
			`/pipelines/${pipeline_id}/valves/update?${searchParams.toString()}`,
			valves,
			{ token }
		);
	} catch (error) {
		console.error('Failed to update pipeline valves:', error);
		throw error;
	}
};

interface TagsResponse {
	choices: Array<{
		message: {
			content: string;
		};
	}>;
}

export const generateTags = async (
	token: string = '',
	model: string,
	messages: string,
	chat_id?: string
) => {
	try {
		const data = await webuiApiClient.post<TagsResponse>(
			'/tasks/tags/completions',
			{
				model: model,
				messages: messages,
				...(chat_id && { chat_id: chat_id })
			},
			{ token }
		);

		try {
			// Step 1: Safely extract the response string
			const response = data?.choices[0]?.message?.content ?? '';

			// Step 2: Attempt to fix common JSON format issues like single quotes
			const sanitizedResponse = response.replace(/['''`]/g, '"'); // Convert single quotes to double quotes for valid JSON

			// Step 3: Find the relevant JSON block within the response
			const jsonStartIndex = sanitizedResponse.indexOf('{');
			const jsonEndIndex = sanitizedResponse.lastIndexOf('}');

			// Step 4: Check if we found a valid JSON block (with both `{` and `}`)
			if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
				const jsonResponse = sanitizedResponse.substring(jsonStartIndex, jsonEndIndex + 1);

				// Step 5: Parse the JSON block
				const parsed = JSON.parse(jsonResponse);

				// Step 6: If there's a "tags" key, return the tags array; otherwise, return an empty array
				if (parsed && parsed.tags) {
					return Array.isArray(parsed.tags) ? parsed.tags : [];
				}
			}

			// If no valid JSON block found, return an empty array
			return [];
		} catch (e) {
			// Catch and safely return empty array on any parsing errors
			console.error('Failed to parse response: ', e);
			return [];
		}
	} catch (error) {
		console.error('Failed to generate tags:', error);
		throw error;
	}
};

interface EmojiResponse {
	choices: Array<{
		message: {
			content: string;
		};
	}>;
}

export const generateEmoji = async (
	token: string = '',
	model: string,
	prompt: string,
	chat_id?: string
) => {
	try {
		const data = await webuiApiClient.post<EmojiResponse>(
			'/tasks/emoji/completions',
			{
				model: model,
				prompt: prompt,
				...(chat_id && { chat_id: chat_id })
			},
			{ token }
		);

		const response = data?.choices[0]?.message?.content.replace(/["']/g, '') ?? null;

		if (response && /\p{Extended_Pictographic}/u.test(response)) {
			const matches = response.match(/\p{Extended_Pictographic}/gu);
			return matches ? matches[0] : null;
		}

		return null;
	} catch (error) {
		console.error('Failed to generate emoji:', error);
		throw error;
	}
};

interface QueriesResponse {
	choices: Array<{
		message: {
			content: string;
		};
	}>;
}

export const generateQueries = async (
	token: string = '',
	model: string,
	messages: object[],
	prompt: string,
	type: string = 'web_search'
) => {
	try {
		const data = await webuiApiClient.post<QueriesResponse>(
			'/tasks/queries/completions',
			{
				model: model,
				messages: messages,
				prompt: prompt,
				type: type
			},
			{ token }
		);

		// Step 1: Safely extract the response string
		const response = data?.choices[0]?.message?.content ?? '';

		try {
			const jsonStartIndex = response.indexOf('{');
			const jsonEndIndex = response.lastIndexOf('}');

			if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
				const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);

				// Step 5: Parse the JSON block
				const parsed = JSON.parse(jsonResponse);

				// Step 6: If there's a "queries" key, return the queries array; otherwise, return an empty array
				if (parsed && parsed.queries) {
					return Array.isArray(parsed.queries) ? parsed.queries : [];
				}
			}

			// If no valid JSON block found, return response as is
			return [response];
		} catch (e) {
			// Catch and safely return empty array on any parsing errors
			console.error('Failed to parse response: ', e);
			return [response];
		}
	} catch (error) {
		console.error('Failed to generate queries:', error);
		throw error;
	}
};

interface AutoCompletionResponse {
	choices: Array<{
		message: {
			content: string;
		};
	}>;
}

export const generateAutoCompletion = async (
	token: string = '',
	model: string,
	prompt: string,
	messages?: object[],
	type: string = 'search query'
) => {
	try {
		const data = await webuiApiClient.post<AutoCompletionResponse>(
			'/tasks/auto/completions',
			{
				model: model,
				prompt: prompt,
				...(messages && { messages: messages }),
				type: type,
				stream: false
			},
			{ token }
		);

		const response = data?.choices[0]?.message?.content ?? '';

		try {
			const jsonStartIndex = response.indexOf('{');
			const jsonEndIndex = response.lastIndexOf('}');

			if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
				const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);

				// Parse the JSON block
				const parsed = JSON.parse(jsonResponse);

				// If there's a "text" key, return the text; otherwise, return empty string
				if (parsed && parsed.text) {
					return parsed.text;
				}
			}

			// If no valid JSON block found, return response as is
			return response;
		} catch (e) {
			// Catch and return response on any parsing errors
			console.error('Failed to parse response: ', e);
			return response;
		}
	} catch (error) {
		console.error('Failed to generate auto completion:', error);
		throw error;
	}
};

export const generateMoACompletion = async (
	token: string = '',
	model: string,
	prompt: string,
	responses: string[]
) => {
	try {
		return await webuiApiClient.post(
			'/tasks/moa/completions',
			{
				model: model,
				prompt: prompt,
				responses: responses,
				stream: true
			},
			{
				token,
				headers: { 'Content-Type': 'application/json' }
			}
		);
	} catch (error) {
		console.error('Failed to generate MoA completion:', error);
		throw error;
	}
};
