import { IMAGES_API_BASE_URL } from '$lib/constants';
import { getRequest, jsonRequest } from '$lib/apis/helpers';

export const getImageGenerationConfig = async (token: string = '') => {
	return getRequest(`${IMAGES_API_BASE_URL}/config`, token);
};

export const updateImageGenerationConfig = async (
	token: string = '',
	engine: string,
	enabled: boolean
) => {
	return jsonRequest(`${IMAGES_API_BASE_URL}/config/update`, token, {
		engine,
		enabled
	});
};

export const getOpenAIConfig = async (token: string = '') => {
	return getRequest(`${IMAGES_API_BASE_URL}/openai/config`, token);
};

export const updateOpenAIConfig = async (token: string = '', url: string, key: string) => {
	return jsonRequest(`${IMAGES_API_BASE_URL}/openai/config/update`, token, {
		url,
		key
	});
};

export const getImageGenerationEngineUrls = async (token: string = '') => {
	return getRequest(`${IMAGES_API_BASE_URL}/url`, token);
};

export const updateImageGenerationEngineUrls = async (token: string = '', urls: object = {}) => {
	return jsonRequest(`${IMAGES_API_BASE_URL}/url/update`, token, { ...urls });
};

export const getImageSize = async (token: string = '') => {
	const res = await getRequest(`${IMAGES_API_BASE_URL}/size`, token);
	return res.IMAGE_SIZE;
};

export const updateImageSize = async (token: string = '', size: string) => {
	const res = await jsonRequest(`${IMAGES_API_BASE_URL}/size/update`, token, { size });
	return res.IMAGE_SIZE;
};

export const getImageSteps = async (token: string = '') => {
	const res = await getRequest(`${IMAGES_API_BASE_URL}/steps`, token);
	return res.IMAGE_STEPS;
};

export const updateImageSteps = async (token: string = '', steps: number) => {
	const res = await jsonRequest(`${IMAGES_API_BASE_URL}/steps/update`, token, { steps });
	return res.IMAGE_STEPS;
};

export const getImageGenerationModels = async (token: string = '') => {
	return getRequest(`${IMAGES_API_BASE_URL}/models`, token);
};

export const getDefaultImageGenerationModel = async (token: string = '') => {
	const res = await getRequest(`${IMAGES_API_BASE_URL}/models/default`, token);
	return res.model;
};

export const updateDefaultImageGenerationModel = async (token: string = '', model: string) => {
	const res = await jsonRequest(`${IMAGES_API_BASE_URL}/models/default/update`, token, { model });
	return res.model;
};

export const imageGenerations = async (token: string = '', prompt: string) => {
	return jsonRequest(`${IMAGES_API_BASE_URL}/generations`, token, { prompt });
};
