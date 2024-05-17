import { WEBUI_API_BASE_URL } from '$lib/constants';
import { fetchApi } from '$lib/apis/utils';

export const setDefaultModels = async (token: string, models: string) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/configs/default/models`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			models: models
		})
	});

export const setDefaultPromptSuggestions = async (token: string, promptSuggestions: string) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/configs/default/suggestions`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
			Authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			suggestions: promptSuggestions
		})
	});
