import { WEBUI_API_BASE_URL } from '$lib/constants';
import { fetchApi } from '$lib/apis/utils';

export const createNewDoc = async (
	token: string,
	collection_name: string,
	filename: string,
	name: string,
	title: string,
	content: object | null = null
) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/documents/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			collection_name: collection_name,
			filename: filename,
			name: name,
			title: title,
			...(content ? { content: JSON.stringify(content) } : {})
		})
	});

export const getDocs = async (token: string = '') =>
	await fetchApi(`${WEBUI_API_BASE_URL}/documents/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

export const getDocByName = async (token: string, name: string) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/documents/name/${name}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

type DocUpdateForm = {
	name: string;
	title: string;
};

export const updateDocByName = async (token: string, name: string, form: DocUpdateForm) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/documents/name/${name}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			name: form.name,
			title: form.title
		})
	});

type TagDocForm = {
	name: string;
	tags: string[];
};

export const tagDocByName = async (token: string, name: string, form: TagDocForm) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/documents/name/${name}/tags`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			name: form.name,
			tags: form.tags
		})
	});

export const deleteDocByName = async (token: string, name: string) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/documents/name/${name}/delete`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});
