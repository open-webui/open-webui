import { type Writable, get, writable } from 'svelte/store';
import { agents as agentsStore, init as initAgents } from './agents';

export type Prompt = {
	id: string,
	promptDisplayName: string,
	prompt: string,
	agentId: string,
}

const LOCATION = '/data/prompts.json';

export const prompts: Writable<Prompt[]> = writable([]);

let initialized = false;

export const init = async (): void => {
	if (initialized) {
		return;
	}

	await initAgents();

	const response = await fetch(LOCATION);
	const allPrompts = await response.json();

	const agents = get(agentsStore);
	const agentIds = agents.map(({ id }) => id);

	const includeOnlyKnownAgents = ({ agentId }) => agentIds.includes(agentId);
	const sanitizedPrompts = allPrompts.filter(includeOnlyKnownAgents);

	if (sanitizedPrompts.length !== allPrompts.length) {
		console.warn(
			'Prompts contain unknown agent (model) IDs: ',
			allPrompts
				.filter((p) => !includeOnlyKnownAgents(p))
				.map(({ agentId }) => agentId)
		);
	}

	prompts.set(sanitizedPrompts);
	initialized = true;
}
