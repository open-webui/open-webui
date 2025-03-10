import { type Writable, writable } from 'svelte/store';

export const knowledgeManager: Writable<boolean> = writable(false);

export const showKnowlegeManager = (newState: boolean = true): void => {
	console.log('knowledgeManager.show=', newState);
	knowledgeManager.set(newState);
}
