import { WEBUI_API_BASE_URL } from '$lib/constants';
import { deleteRequest, getRequest, jsonRequest } from '$lib/apis/helpers';

export const getMemories = async (token: string) => {
	return getRequest(`${WEBUI_API_BASE_URL}/memories/`, token);
};

export const addNewMemory = async (token: string, content: string) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/memories/add`, token, { content });
};

export const updateMemoryById = async (token: string, id: string, content: string) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/memories/${id}/update`, token, { content });
};

export const queryMemory = async (token: string, content: string) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/memories/query`, token, { content });
};

export const deleteMemoryById = async (token: string, id: string) => {
	return deleteRequest(`${WEBUI_API_BASE_URL}/memories/${id}`, token);
};

export const deleteMemoriesByUserId = async (token: string) => {
	return deleteRequest(`${WEBUI_API_BASE_URL}/memories/user`, token);
};
