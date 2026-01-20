import canchatAPI from '$lib/apis/canchatAPI';
import { WEBUI_API_BASE_PATH } from '$lib/constants';
import type { Banner } from '$lib/types';

export const importConfig = async (token: string, config) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/configs/import`, {
		method: 'POST',
		data: {
			config: config
		}
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

export const exportConfig = async (token: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/configs/export`, {
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

export const getModelsConfig = async (token: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/configs/models`, {
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

export const setModelsConfig = async (token: string, config: object) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/configs/models`, {
		method: 'POST',
		data: {
			...config
		}
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

export const setDefaultPromptSuggestions = async (token: string, promptSuggestions: string) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/configs/suggestions`, {
		method: 'POST',
		data: {
			suggestions: promptSuggestions
		}
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

export const getBanners = async (token: string): Promise<Banner[]> => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/configs/banners`, {
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

export const setBanners = async (token: string, banners: Banner[]) => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/configs/banners`, {
		method: 'POST',
		data: {
			banners: banners
		}
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

// Chat Lifetime Configuration
export interface ChatLifetimeConfig {
	enabled: boolean;
	days: number;
	preserve_pinned: boolean;
	preserve_archived: boolean;
}

export const getChatLifetimeConfig = async (token: string): Promise<ChatLifetimeConfig> => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/configs/chat-lifetime`, {
		method: 'GET'
	})
		.then(async (res) => {
			return res.data as ChatLifetimeConfig;
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

export const updateChatLifetimeConfig = async (
	token: string,
	config: ChatLifetimeConfig
): Promise<ChatLifetimeConfig> => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/configs/chat-lifetime`, {
		method: 'POST',
		data: config
	})
		.then(async (res) => {
			res.data;
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

// Cleanup Operations
export const triggerChatCleanup = async (
	token: string,
	options?: {
		max_age_days?: number;
		preserve_pinned?: boolean;
		preserve_archived?: boolean;
	}
) => {
	let error = null;

	const res = await canchatAPI(
		`${WEBUI_API_BASE_PATH}/retrieval/maintenance/cleanup/expired-chats`,
		{
			method: 'POST',
			params: {
				max_age_days: options?.max_age_days,
				preserve_pinned: options?.preserve_pinned,
				preserve_archived: options?.preserve_archived
			}
		}
	)
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

export const triggerComprehensiveCleanup = async (
	token: string,
	options?: {
		max_age_days?: number;
		include_chat_cleanup?: boolean;
		preserve_pinned?: boolean;
		preserve_archived?: boolean;
	}
) => {
	let error = null;

	const res = await canchatAPI(
		`${WEBUI_API_BASE_PATH}/retrieval/maintenance/cleanup/comprehensive`,
		{
			method: 'POST',
			params: {
				max_age_days: options?.max_age_days,
				include_chat_cleanup: options?.include_chat_cleanup,
				preserve_pinned: options?.preserve_pinned,
				preserve_archived: options?.preserve_archived
			}
		}
	)
		.then(async (res) => {
			return res.data``;
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

export interface ChatLifetimeScheduleInfo {
	enabled: boolean;
	status: string;
	next_run: string | null;
	lifetime_days: number;
	schedule?: string;
	error?: string;
}

export const getChatLifetimeSchedule = async (token: string): Promise<ChatLifetimeScheduleInfo> => {
	let error = null;

	const res = await canchatAPI(`${WEBUI_API_BASE_PATH}/configs/chat-lifetime/schedule`, {
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
