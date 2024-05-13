import { WEBUI_API_BASE_URL } from '$lib/constants';
import { deleteRequest, getRequest, jsonRequest } from '$lib/apis/helpers';

export const createNewDoc = async (
	token: string,
	collection_name: string,
	filename: string,
	name: string,
	title: string,
	content: object | null = null
) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/documents/create`, token, {
		collection_name: collection_name,
		filename: filename,
		name: name,
		title: title,
		...(content ? { content: JSON.stringify(content) } : {})
	});
};

export const getDocs = async (token: string = '') => {
	return getRequest(`${WEBUI_API_BASE_URL}/documents/`, token);
};

export const getDocByName = async (token: string, name: string) => {
	const searchParams = new URLSearchParams();
	searchParams.append('name', name);
	return getRequest(`${WEBUI_API_BASE_URL}/documents/docs?${searchParams.toString()}`, token);
};

type DocUpdateForm = {
	name: string;
	title: string;
};

export const updateDocByName = async (token: string, name: string, form: DocUpdateForm) => {
	const searchParams = new URLSearchParams();
	searchParams.append('name', name);

	return jsonRequest(
		`${WEBUI_API_BASE_URL}/documents/doc/update?${searchParams.toString()}`,
		token,
		form
	);
};

type TagDocForm = {
	name: string;
	tags: string[];
};

export const tagDocByName = async (token: string, name: string, form: TagDocForm) => {
	const searchParams = new URLSearchParams();
	searchParams.append('name', name);

	return jsonRequest(`${WEBUI_API_BASE_URL}/documents/doc/tags?${searchParams.toString()}`, token, {
		name: form.name,
		tags: form.tags
	});
};

export const deleteDocByName = async (token: string, name: string) => {
	const searchParams = new URLSearchParams();
	searchParams.append('name', name);

	const url = `${WEBUI_API_BASE_URL}/documents/doc/delete?${searchParams.toString()}`;
	return deleteRequest(url, token);
};
