import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH, WEBUI_BASE_URL } from '$lib/constants';

export const getModels = async (token: string = '', base: boolean = false) => {
	let error = null;
	const res = await canchatAPI(`/api/models${base ? '/base' : ''}`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data.data;
		})
		.catch(async (err) => {
			error = err;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res || [];
};

type ChatCompletedForm = {
	model: string;
	messages: string[];
	chat_id: string;
	session_id: string;
};

export const chatCompleted = async (token: string, body: ChatCompletedForm) => {
	let error = null;

	const res = await await canchatAPI(`/api/chat/completed`, {
		method: 'POST',
		data: body
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type ChatActionForm = {
	model: string;
	messages: string[];
	chat_id: string;
};

export const chatAction = async (token: string, action_id: string, body: ChatActionForm) => {
	let error = null;

	const res = await await canchatAPI(`/api/chat/actions/${action_id}`, {
		method: 'POST',

		data: body
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const stopTask = async (token: string, id: string) => {
	let error = null;

	const res = await await canchatAPI(`/api/tasks/stop/${id}`, {
		method: 'POST'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getTaskConfig = async (token: string = '') => {
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/tasks/config`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateTaskConfig = async (token: string, config: object) => {
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/tasks/config/update`, {
		method: 'POST',

		data: config
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const generateTitle = async (
	token: string = '',
	model: string,
	messages: string[],
	chat_id?: string
) => {
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/tasks/title/completions`, {
		method: 'POST',
		data: {
			model: model,
			messages: messages,
			...(chat_id && { chat_id: chat_id })
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res?.choices[0]?.message?.content.replace(/["']/g, '') ?? 'New Chat';
};

export const generateTags = async (
	token: string = '',
	model: string,
	messages: string,
	chat_id?: string
) => {
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/tasks/tags/completions`, {
		method: 'POST',
		data: {
			model: model,
			messages: messages,
			...(chat_id && { chat_id: chat_id })
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	try {
		// Step 1: Safely extract the response string
		const response = res?.choices[0]?.message?.content ?? '';

		// Step 2: Attempt to fix common JSON format issues like single quotes
		const sanitizedResponse = response.replace(/['‘’`]/g, '"'); // Convert single quotes to double quotes for valid JSON

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
			} else {
				return [];
			}
		}

		// If no valid JSON block found, return an empty array
		return [];
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
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
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/tasks/emoji/completions`, {
		method: 'POST',
		data: {
			model: model,
			prompt: prompt,
			...(chat_id && { chat_id: chat_id })
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	const response = res?.choices[0]?.message?.content.replace(/["']/g, '') ?? null;

	if (response) {
		if (/\p{Extended_Pictographic}/u.test(response)) {
			return response.match(/\p{Extended_Pictographic}/gu)[0];
		}
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
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/tasks/queries/completions`, {
		method: 'POST',
		data: {
			model: model,
			messages: messages,
			prompt: prompt,
			type: type
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	// Step 1: Safely extract the response string
	const response = res?.choices[0]?.message?.content ?? '';

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
			} else {
				return [];
			}
		}

		// If no valid JSON block found, return response as is
		return [response];
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
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
	const controller = new AbortController();
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/tasks/auto/completions`, {
		signal: controller.signal,
		method: 'POST',
		data: {
			model: model,
			prompt: prompt,
			...(messages && { messages: messages }),
			type: type,
			stream: false
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	const response = res?.choices[0]?.message?.content ?? '';

	try {
		const jsonStartIndex = response.indexOf('{');
		const jsonEndIndex = response.lastIndexOf('}');

		if (jsonStartIndex !== -1 && jsonEndIndex !== -1) {
			const jsonResponse = response.substring(jsonStartIndex, jsonEndIndex + 1);

			// Step 5: Parse the JSON block
			const parsed = JSON.parse(jsonResponse);

			// Step 6: If there's a "queries" key, return the queries array; otherwise, return an empty array
			if (parsed && parsed.text) {
				return parsed.text;
			} else {
				return '';
			}
		}

		// If no valid JSON block found, return response as is
		return response;
	} catch (e) {
		// Catch and safely return empty array on any parsing errors
		console.error('Failed to parse response: ', e);
		return response;
	}
};

export const generateMoACompletion = async (
	token: string = '',
	model: string,
	prompt: string,
	responses: string[]
) => {
	const controller = new AbortController();
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/tasks/moa/completions`, {
		signal: controller.signal,
		method: 'POST',
		data: {
			model: model,
			prompt: prompt,
			responses: responses,
			stream: true
		}
	}).catch((err) => {
		console.log(err);
		error = err;
		return null;
	});

	if (error) {
		throw error;
	}

	return [res, controller];
};

export const getPipelinesList = async (token: string = '') => {
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/pipelines/list`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	let pipelines = res?.data ?? [];
	return pipelines;
};

export const uploadPipeline = async (token: string, file: File, urlIdx: string) => {
	let error = null;

	// Create a new FormData object to handle the file upload
	const formData = new FormData();
	formData.append('file', file);
	formData.append('urlIdx', urlIdx);

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/pipelines/upload`, {
		method: 'POST',
		headers: {
			...(token && { authorization: `Bearer ${token}` })
			// 'Content-Type': 'multipart/form-data' is not needed as Fetch API will set it automatically
		},
		data: formData
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const downloadPipeline = async (token: string, url: string, urlIdx: string) => {
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/pipelines/add`, {
		method: 'POST',

		data: {
			url: url,
			urlIdx: urlIdx
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deletePipeline = async (token: string, id: string, urlIdx: string) => {
	let error = null;

	const res = await await canchatAPI(`${WEBUI_API_BASE_PATH}/pipelines/delete`, {
		method: 'DELETE',

		data: {
			id: id,
			urlIdx: urlIdx
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPipelines = async (token: string, urlIdx?: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	const res = await await canchatAPI(
		`${WEBUI_API_BASE_PATH}/pipelines/?${searchParams.toString()}`,
		{
			method: 'GET'
		}
	)
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	let pipelines = res?.data ?? [];
	return pipelines;
};

export const getPipelineValves = async (token: string, pipeline_id: string, urlIdx: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	const res = await canchatAPI(
		`${WEBUI_BASE_URL}/api/v1/pipelines/${pipeline_id}/valves?${searchParams.toString()}`,
		{
			method: 'GET'
		}
	)
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPipelineValvesSpec = async (token: string, pipeline_id: string, urlIdx: string) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	const res = await canchatAPI(
		`${WEBUI_BASE_URL}/api/v1/pipelines/${pipeline_id}/valves/spec?${searchParams.toString()}`,
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
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updatePipelineValves = async (
	token: string = '',
	pipeline_id: string,
	valves: object,
	urlIdx: string
) => {
	let error = null;

	const searchParams = new URLSearchParams();
	if (urlIdx !== undefined) {
		searchParams.append('urlIdx', urlIdx);
	}

	const res = await canchatAPI(
		`${WEBUI_BASE_URL}/api/v1/pipelines/${pipeline_id}/valves/update?${searchParams.toString()}`,
		{
			method: 'POST',
			headers: {
				Accept: 'application/json',
				'Content-Type': 'application/json',
				...(token && { authorization: `Bearer ${token}` })
			},
			data: valves
		}
	)
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);

			if ('detail' in err) {
				error = err.detail;
			} else {
				error = err;
			}
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getBackendConfig = async () => {
	let error = null;

	const res = await await canchatAPI(`/api/config`, {
		method: 'GET',
		withCredentials: true,
		headers: {
			'Content-Type': 'application/json'
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getChangelog = async () => {
	let error = null;

	const res = await await canchatAPI(`/api/changelog`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getModelFilterConfig = async (token: string) => {
	let error = null;

	const res = await await canchatAPI(`/api/config/model/filter`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updateModelFilterConfig = async (
	token: string,
	enabled: boolean,
	models: string[]
) => {
	let error = null;

	const res = await await canchatAPI(`/api/config/model/filter`, {
		method: 'POST',
		data: {
			enabled: enabled,
			models: models
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getWebhookUrl = async (token: string) => {
	let error = null;

	const res = await await canchatAPI(`/api/webhook`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res.url;
};

export const updateWebhookUrl = async (token: string, url: string) => {
	let error = null;

	const res = await await canchatAPI(`/api/webhook`, {
		method: 'POST',
		data: {
			url: url
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res.url;
};

export const getCommunitySharingEnabledStatus = async (token: string) => {
	let error = null;

	const res = await await canchatAPI(`/api/community_sharing`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const toggleCommunitySharingEnabledStatus = async (token: string) => {
	let error = null;

	const res = await await canchatAPI(`/api/community_sharing/toggle`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getModelConfig = async (token: string): Promise<GlobalModelConfig> => {
	let error = null;

	const res = await await canchatAPI(`/api/config/models`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res.models;
};

export interface ModelConfig {
	id: string;
	name: string;
	meta: ModelMeta;
	base_model_id?: string;
	params: ModelParams;
}

export interface ModelMeta {
	description?: string;
	capabilities?: object;
	profile_image_url?: string;
}

export interface ModelParams {}

export type GlobalModelConfig = ModelConfig[];

export const updateModelConfig = async (token: string, config: GlobalModelConfig) => {
	let error = null;

	const res = await await canchatAPI(`/api/config/models`, {
		method: 'POST',
		data: {
			models: config
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			console.log(err);
			error = err;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
