import { WEBUI_API_BASE_URL } from '$lib/constants';
import { fetchApi } from '$lib/apis/utils';

export const createNewPrompt = async (
	token: string,
	command: string,
	title: string,
	content: string
) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/prompts/create`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			command: `/${command}`,
			title: title,
			content: content
		})
	});

export const getPrompts = async (token: string = '') =>
	await fetchApi(`${WEBUI_API_BASE_URL}/prompts/`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

export const getPromptByCommand = async (token: string, command: string) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/prompts/command/${command}`, {
		method: 'GET',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});

export const updatePromptByCommand = async (
	token: string,
	command: string,
	title: string,
	content: string
) =>
	await fetchApi(`${WEBUI_API_BASE_URL}/prompts/command/${command}/update`, {
		method: 'POST',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		},
		body: JSON.stringify({
			command: `/${command}`,
			title: title,
			content: content
		})
	});

export const deletePromptByCommand = async (token: string, command: string) => {
	command = command.charAt(0) === '/' ? command.slice(1) : command;

	return await fetchApi(`${WEBUI_API_BASE_URL}/prompts/command/${command}/delete`, {
		method: 'DELETE',
		headers: {
			Accept: 'application/json',
			'Content-Type': 'application/json',
			authorization: `Bearer ${token}`
		}
	});
};
