import { IMAGES_API_BASE_URL } from '$lib/constants';
import { fetchApi } from '$lib/apis/utils';

export const getImageGenerationConfig = async (token: string = '') =>
	await fetchApi(`${IMAGES_API_BASE_URL}/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

export const updateImageGenerationConfig = async (
	token: string = '',
	engine: string,
	enabled: boolean
) =>
	await fetchApi(`${IMAGES_API_BASE_URL}/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			engine,
			enabled
		})
	});

export const getOpenAIConfig = async (token: string = '') =>
	await fetchApi(`${IMAGES_API_BASE_URL}/openai/config`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

export const updateOpenAIConfig = async (token: string = '', url: string, key: string) =>
	await fetchApi(`${IMAGES_API_BASE_URL}/openai/config/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			url: url,
			key: key
		})
	});

export const getImageGenerationEngineUrls = async (token: string = '') =>
	await fetchApi(`${IMAGES_API_BASE_URL}/url`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

export const updateImageGenerationEngineUrls = async (token: string = '', urls: object = {}) =>
	await fetchApi(`${IMAGES_API_BASE_URL}/url/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			...urls
		})
	});

export const getImageSize = async (token: string = '') => {
	const res = await fetchApi(`${IMAGES_API_BASE_URL}/size`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	return res.IMAGE_SIZE;
};

export const updateImageSize = async (token: string = '', size: string) => {
	const res = await fetchApi(`${IMAGES_API_BASE_URL}/size/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			size: size
		})
	});

	return res.IMAGE_SIZE;
};

export const getImageSteps = async (token: string = '') => {
	const res = await fetchApi(`${IMAGES_API_BASE_URL}/steps`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	return res.IMAGE_STEPS;
};

export const updateImageSteps = async (token: string = '', steps: number) => {
	const res = await fetchApi(`${IMAGES_API_BASE_URL}/steps/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({ steps })
	});

	return res.IMAGE_STEPS;
};

export const getImageGenerationModels = async (token: string = '') => {
	const res = await fetchApi(`${IMAGES_API_BASE_URL}/models`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	return res;
};

export const getDefaultImageGenerationModel = async (token: string = '') => {
	const res = await fetchApi(`${IMAGES_API_BASE_URL}/models/default`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		}
	});

	return res.model;
};

export const updateDefaultImageGenerationModel = async (token: string = '', model: string) => {
	const res = await fetchApi(`${IMAGES_API_BASE_URL}/models/default/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			model: model
		})
	});

	return res.model;
};

export const imageGenerations = async (token: string = '', prompt: string) => {
	const res = await fetchApi(`${IMAGES_API_BASE_URL}/generations`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			...(token && { authorization: `Bearer ${token}` })
		},
		body: JSON.stringify({
			prompt: prompt
		})
	});

	return res;
};
