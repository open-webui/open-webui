import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';

type PromptItem = {
	command: string;
	title: string;
	content: string;
	access_control?: null | object;
};

export const createNewPrompt = async (token: string, prompt: PromptItem) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/prompts/create`, {
		method: 'POST',
		data: {
			...prompt,
			command: `/${prompt.command}`
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPrompts = async (
	token: string = '',
	options: { page?: number; limit?: number; search?: string } = {}
) => {
	let error = null;

	const { page = 1, limit = 20, search } = options;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/prompts/paginated`, {
		method: 'GET',
		params: {
			page: page,
			limit: limit,
			search: search
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPromptList = async (
	token: string = '',
	options: { page?: number; limit?: number; search?: string } = {}
) => {
	let error = null;

	const { page = 1, limit = 20, search } = options;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/prompts/list/paginated`, {
		method: 'GET',
		params: {
			page: page,
			limit: limit,
			search: search
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPromptsCount = async (token: string = '', search?: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/prompts/count`, {
		method: 'GET',
		params: {
			search: search
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

// Legacy functions for backward compatibility (now calling original endpoints)
export const getPromptsLegacy = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/prompts/`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPromptListLegacy = async (token: string = '') => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/prompts/list`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;
			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const getPromptByCommand = async (token: string, command: string) => {
	let error = null;

	// URL encode the command to properly handle special characters like question marks
	const encodedCommand = encodeURIComponent(command);

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/prompts/command/${encodedCommand}`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const updatePromptByCommand = async (token: string, prompt: PromptItem) => {
	let error = null;

	// URL encode the command to properly handle special characters like question marks
	const encodedCommand = encodeURIComponent(prompt.command);

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/prompts/command/${encodedCommand}/update`, {
		method: 'POST',
		data: {
			...prompt,
			command: `/${prompt.command}`
		}
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

export const deletePromptByCommand = async (token: string, command: string) => {
	let error = null;

	command = command.charAt(0) === '/' ? command.slice(1) : command;

	// URL encode the command to properly handle special characters like question marks
	const encodedCommand = encodeURIComponent(command);

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/prompts/command/${encodedCommand}/delete`, {
		method: 'DELETE'
	})
		.then(async (res) => {
			return res.data;
		})
		.then((json) => {
			return json;
		})
		.catch((err) => {
			error = err.detail;

			console.log(err);
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};
