import { type Writable, writable } from 'svelte/store';

export type Agent = {
	id: string,
	name: string,
	subtitle: string,
	description: string,
	avatarUrl: string,
}

const LOCATION = '/data/agents.json';

export const agents: Writable<Agent[]> = writable([]);

let initialized = false;

export const init = async (): void => {
	if (initialized) {
		return;
	}

	const response = await fetch(LOCATION);
	const agentsArray = await response.json();

	agents.set(agentsArray);
	initialized = true;
}
