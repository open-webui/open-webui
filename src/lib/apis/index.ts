import { WEBUI_BASE_URL } from '$lib/constants';
import { fetchApi } from '$lib/apis/utils';

export const getBackendConfig = async () =>
	await fetchApi(`${WEBUI_BASE_URL}/api/config`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	});

export const getChangelog = async () =>
	await fetchApi(`${WEBUI_BASE_URL}/api/changelog`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	});

export const getVersionUpdates = async () =>
	await fetchApi(`${WEBUI_BASE_URL}/api/version/updates`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json'
		}
	});

export const getModelFilterConfig = async (token: string) =>
	await fetchApi(`${WEBUI_BASE_URL}/api/config/model/filter`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

export const updateModelFilterConfig = async (token: string, enabled: boolean, models: string[]) =>
	await fetchApi(`${WEBUI_BASE_URL}/api/config/model/filter`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			enabled: enabled,
			models: models
		})
	});

export const getWebhookUrl = async (token: string) => {
	const res = await fetchApi(`${WEBUI_BASE_URL}/api/webhook`, {
		method: 'GET',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		}
	});

	return res.url;
};

export const updateWebhookUrl = async (token: string, url: string) => {
	const res = await fetchApi(`${WEBUI_BASE_URL}/api/webhook`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			url: url
		})
	});

	return res.url;
};
