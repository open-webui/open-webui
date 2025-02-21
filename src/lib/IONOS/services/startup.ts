import { get } from 'svelte/store';
import { settings } from '$lib/stores';
import { updateUserSettings } from '$lib/apis/users';
import { getAgent } from './agent';
import { getPrompt } from './prompt';

export const storeAgent = async (id: string): void => {
	if (!id) {
		throw new Error('Agent ID must not be falsy');
	}

	const updatedSettings = {
		...get(settings),
		models: [id]
	};

	settings.set(updatedSettings);
	await updateUserSettings(localStorage.token, { ui: updatedSettings });
}

export type StartupInfo = {
	agent: string,
	prompt: string,
}

export const startup = async (): StartupInfo => {
	console.log('*** IONOS GPT startup ***');

	const agent = getAgent();
	console.log('Stored agent in settings/store:', agent);

	if (!agent) {
		console.log('No start agent stored');
		return { agent: '', prompt: '' };
	}

	await storeAgent(agent);

	const prompt = getPrompt();

	if (!prompt) {
		console.log('No start prompt stored');
		return { agent, prompt: '' };
	}

	console.log('Stored start prompt in session storage for Chat to consume:', prompt);
	return { agent, prompt };
};
