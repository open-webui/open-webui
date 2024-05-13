import { WEBUI_API_BASE_URL } from '$lib/constants';
import type { Banner } from '$lib/types';
import { getRequest, jsonRequest } from '$lib/apis/helpers';

export const setDefaultModels = (token: string, models: string) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/configs/default/models`, token, { models });
};

export const setDefaultPromptSuggestions = (token: string, promptSuggestions: string) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/configs/default/suggestions`, token, {
		suggestions: promptSuggestions
	});
};

export const getBanners = async (token: string): Promise<Banner[]> => {
	return getRequest<Banner[]>(`${WEBUI_API_BASE_URL}/configs/banners`, token);
};

export const setBanners = async (token: string, banners: Banner[]) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/configs/banners`, token, {
		banners
	});
};
