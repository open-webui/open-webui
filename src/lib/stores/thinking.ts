import { writable } from 'svelte/store';

// Initializes from localStorage if it exists, default to Medium (2048)
const initialBudget = Number(localStorage.getItem('active_thinking_budget') || '2048');

export const thinkingBudget = writable<number>(initialBudget);

// Automatically update localStorage whenever the budget changes
thinkingBudget.subscribe((value) => {
	localStorage.setItem('active_thinking_budget', value.toString());
});
