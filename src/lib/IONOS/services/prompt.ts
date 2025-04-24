import { get } from 'svelte/store';
import type { Prompt } from '$lib/IONOS/stores/prompts';
import { prompts } from '$lib/IONOS/stores/prompts';
import { selectAgent } from './agent';

export const LOCALSTORAGE_START_PROMPT_KEY = 'ionosgptStartWithPrompt';

export const selectPrompt = async (promptId: number): Promise<void> => {
	const promptConfig: Prompt|undefined = get(prompts).find(({ id }) => promptId === id);

	if (!promptConfig) {
		throw new Error(`Prompt not found by prompt ID "${promptId}"!`);
	}

	localStorage.setItem(LOCALSTORAGE_START_PROMPT_KEY, promptConfig.prompt);

	selectAgent(promptConfig.agentId);
}

export const getAndForgetPrompt = (): string => {
	const prompt = localStorage.getItem(LOCALSTORAGE_START_PROMPT_KEY) ?? '';
	localStorage.removeItem(LOCALSTORAGE_START_PROMPT_KEY);
	return prompt;
}
