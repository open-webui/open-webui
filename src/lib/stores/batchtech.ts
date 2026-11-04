// BATCHTECH: Chat / Code mode, modelled on the claude.ai Chat and Code switch.
// Chat prefers an OpenAI model and Code prefers a Claude model. Both are picked
// from whatever connections the admin has added, so no keys live in the UI.
import { writable } from 'svelte/store';

export type AppMode = 'chat' | 'code';

const KEY = 'batchtech.mode';

const readMode = (): AppMode => {
	try {
		return localStorage.getItem(KEY) === 'code' ? 'code' : 'chat';
	} catch {
		return 'chat';
	}
};

export const appMode = writable<AppMode>(readMode());

appMode.subscribe((value) => {
	try {
		localStorage.setItem(KEY, value);
	} catch {
		// storage can be blocked; the mode still works for this page load
	}
});

const MODEL_PATTERNS: Record<AppMode, RegExp> = {
	chat: /gpt|openai|\bo[134]\b/i,
	code: /claude|anthropic/i
};

/** First visible model that matches the mode's provider, or null. */
export const pickModelForMode = (models: any[], mode: AppMode): string | null => {
	const visible = (models ?? []).filter((m) => !(m?.info?.meta?.hidden ?? false));
	const match = visible.find((m) => MODEL_PATTERNS[mode].test(`${m.id} ${m.name ?? ''}`));
	return match?.id ?? null;
};

/** Switch mode and remember the matching model so the next new chat starts on it. */
export const setAppMode = (mode: AppMode, models: any[]) => {
	const id = pickModelForMode(models, mode);
	if (id) {
		try {
			sessionStorage.selectedModels = JSON.stringify([id]);
		} catch {
			// ignore
		}
	}
	appMode.set(mode);
};

export const CODE_SYSTEM_PROMPT =
	'You are a careful senior software engineer helping the user write, read and debug code. ' +
	'Prefer complete, runnable code in fenced blocks with the language named. Ask a short ' +
	'clarifying question only when the request is genuinely ambiguous. When fixing a bug, ' +
	'explain the cause first, then show the fix. Keep explanations brief and concrete.';

export const greetingFor = (name: string | undefined, mode: AppMode, now = new Date()): string => {
	const who = name ? `, ${name.split(' ')[0]}` : '';
	if (mode === 'code') return `What are we building${who}?`;
	const h = now.getHours();
	const part = h < 5 ? 'Evening' : h < 12 ? 'Morning' : h < 18 ? 'Afternoon' : 'Evening';
	return `${part}${who}`;
};
