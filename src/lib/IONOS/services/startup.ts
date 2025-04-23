import {
	updateSettings
} from './settings';
import {
	getAndForgetAgent,
	hasAgent,
} from './agent';
import {
	getAndForgetPrompt,
	hasPrompt,
} from './prompt';

export type StartupInfo = {
	agent: string,
	prompt: string,
}

export const hasStoredState = (): boolean => {
	return hasAgent() || hasPrompt();
}

export const startup = async (): Promise<StartupInfo> => {
	console.log('*** IONOS GPT startup ***');

	const agent = getAndForgetAgent();
	console.log('Stored agent in settings/store:', agent);

	if (!agent) {
		console.log('No start agent stored');
		return { agent: '', prompt: '' };
	}

	await updateSettings({
		models: [agent]
	});

	const prompt = getAndForgetPrompt();

	if (!prompt) {
		console.log('No start prompt stored');
		return { agent, prompt: '' };
	}

	console.log('Stored start prompt in session storage for Chat to consume:', prompt);
	return { agent, prompt };
};
