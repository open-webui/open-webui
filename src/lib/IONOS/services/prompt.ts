import { get } from 'svelte/store';
import { prompts } from '$lib/IONOS/stores/prompts';
import { selectAgent } from './agent';

export const LOCALSTORAGE_START_PROMPT_KEY = 'ionosgptStartWithPrompt';

export const selectPrompt = async (promptId: number): void => {
	const promptConfig: Prompt = get(prompts).find(({ id }) => promptId === id);

	localStorage.setItem(LOCALSTORAGE_START_PROMPT_KEY, promptConfig.prompt);

	selectAgent(promptConfig.agentId);
}

export const getPrompt = (): string => {
	const prompt = localStorage.getItem(LOCALSTORAGE_START_PROMPT_KEY) ?? '';
	localStorage.removeItem(LOCALSTORAGE_START_PROMPT_KEY);
	return prompt;
}
