import { WEBUI_API_BASE_URL } from '$lib/constants';
import { fetchApi } from '$lib/apis/utils';

export const createNewModelfile = async (token: string, modelfile: object) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/modelfiles/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			modelfile: modelfile
		})
	});

export const getModelfiles = async (token: string = '') => {
	const res = await fetchApi(`${WEBUI_API_BASE_URL}/modelfiles/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

	return res.map((modelfile) => modelfile.modelfile);
};

export const getModelfileByTagName = async (token: string, tagName: string) => {
	const res = await fetchApi(`${WEBUI_API_BASE_URL}/modelfiles/`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			tag_name: tagName
		})
	});

	return res.modelfile;
};

export const updateModelfileByTagName = async (token: string, tagName: string, modelfile: object) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/modelfiles/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			tag_name: tagName,
			modelfile: modelfile
		})
	});

export const deleteModelfileByTagName = async (token: string, tagName: string) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/modelfiles/delete`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			tag_name: tagName
		})
	});
