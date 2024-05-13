import { WEBUI_API_BASE_URL } from '$lib/constants';
import { deleteRequest, getRequest, jsonRequest } from '$lib/apis/helpers';

export const createNewPrompt = async (
	token: string,
	command: string,
	title: string,
	content: string
) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/prompts/create`, token, {
		command: `/${command}`,
		title: title,
		content: content
	});
};

export const getPrompts = async (token: string = '') => {
	return getRequest(`${WEBUI_API_BASE_URL}/prompts/`, token);
};

export const getPromptByCommand = async (token: string, command: string) => {
	return getRequest(`${WEBUI_API_BASE_URL}/prompts/command/${command}`, token);
};

export const updatePromptByCommand = async (
	token: string,
	command: string,
	title: string,
	content: string
) => {
	return jsonRequest(`${WEBUI_API_BASE_URL}/prompts/command/${command}/update`, token, {
		command: `/${command}`,
		title: title,
		content: content
	});
};

export const deletePromptByCommand = async (token: string, command: string) => {
	command = command.charAt(0) === '/' ? command.slice(1) : command;
	return deleteRequest(`${WEBUI_API_BASE_URL}/prompts/command/${command}/delete`, token);
};
