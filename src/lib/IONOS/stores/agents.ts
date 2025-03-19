import { type Writable, writable } from 'svelte/store';

export type Agent = {
	id: string,
	name: string,
	subtitle: string,
	description: string,
}

const LOCATION = '/data/agents.json';

export const agents: Writable<Agent[]> = writable([]);

let initialized = false;

export const init = async (): Promise<void> => {
	if (initialized) {
		return;
	}

	const response = await fetch(LOCATION);
	const agentsArray = (await response.json()) as Agent[];

	agents.set(agentsArray);
	initialized = true;
}
