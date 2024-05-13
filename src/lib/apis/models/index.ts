import { WEBUI_API_BASE_URL } from '$lib/constants';
import { deleteRequest, getRequest, jsonRequest } from '$lib/apis/helpers';

export const addNewModel = async (token: string, model: object) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/models/add`, token, model);
};

export const getModelInfos = async (token: string = '') => {
	return getRequest(`${WEBUI_API_BASE_URL}/models`, token);
};

export const getModelById = async (token: string, id: string) => {
	const searchParams = new URLSearchParams();
	searchParams.append('id', id);
	return getRequest(`${WEBUI_API_BASE_URL}/models?${searchParams.toString()}`, token);
};

export const updateModelById = async (token: string, id: string, model: object) => {
	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	return jsonRequest(
		`${WEBUI_API_BASE_URL}/models/update?${searchParams.toString()}`,
		token,
		model
	);
};

export const deleteModelById = async (token: string, id: string) => {
	const searchParams = new URLSearchParams();
	searchParams.append('id', id);

	return deleteRequest(`${WEBUI_API_BASE_URL}/models/delete?${searchParams.toString()}`, token);
};
