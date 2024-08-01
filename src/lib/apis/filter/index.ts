import { FILTER_API_BASE_URL } from '$lib/constants';

export const getFilterConfig = async (token: string) => {
	let error = null;

	const res = await fetch(`${FILTER_API_BASE_URL}/config`, {
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
			console.log(err);
			error = err.detail;
			return null;
		});

	if (error) {
		throw error;
	}

	return res;
};

type FilterConfigForm = {
	ENABLE_MESSAGE_FILTER: boolean;
	CHAT_FILTER_WORDS: string;
	CHAT_FILTER_WORDS_FILE: string;
	ENABLE_REPLACE_FILTER_WORDS: boolean;
	REPLACE_FILTER_WORDS: string;
	ENABLE_WECHAT_NOTICE: boolean;
	WECHAT_APP_SECRET: string;
	ENABLE_DAILY_USAGES_NOTICE: boolean;
	WECHAT_NOTICE_SUFFIX: string;

};

export const updateFilterConfig = async (token: string, payload: FilterConfigForm) => {
	let error = null;

	const res = await fetch(`${FILTER_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			...payload
		})
	})
		.then(async (res) => {
			if (!res.ok) throw await res.json();
			return res.json();
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
