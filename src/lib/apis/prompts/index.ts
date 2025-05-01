import { webuiApiClient } from '../clients';

type PromptItem = {
	command: string;
	title: string;
	content: string;
	access_control?: null | object;
};

export const createNewPrompt = async (token: string, prompt: PromptItem) =>
	webuiApiClient.post('/prompts/create', { ...prompt, command: `/${prompt.command}` }, { token });

export const getPrompts = async (token: string = '') => webuiApiClient.get('/prompts/', { token });

export const getPromptList = async (token: string = '') =>
	webuiApiClient.get('/prompts/list', { token });

export const getPromptByCommand = async (token: string, command: string) =>
	webuiApiClient.get(`/prompts/command/${command}`, { token });

export const updatePromptByCommand = async (token: string, prompt: PromptItem) =>
	webuiApiClient.post(
		`/prompts/command/${prompt.command}/update`,
		{ ...prompt, command: `/${prompt.command}` },
		{ token }
	);

export const deletePromptByCommand = async (token: string, command: string) =>
	webuiApiClient.del(
		`/prompts/command/${command.charAt(0) === '/' ? command.slice(1) : command}/delete`,
		null,
		{ token }
	);
