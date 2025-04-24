import type { Unsubscriber } from 'svelte/store';
import { describe, beforeEach, expect, it, vi } from 'vitest';
import type { Prompt } from '$lib/IONOS/stores/prompts';
import {
	LOCALSTORAGE_START_PROMPT_KEY,
	selectPrompt,
	getAndForgetPrompt,
} from './prompt';

const mocks = vi.hoisted(() => {
	return {
		stores: {
			prompts: {
				subscribe: vi.fn(),
			},
		},
		services: {
			agent: {
				selectAgent: vi.fn(),
			}
		},
	};
});

vi.mock('$lib/IONOS/stores/prompts', async () => {
	return {
		prompts: mocks.stores.prompts,
	};
});

vi.mock('$lib/IONOS/services/agent', async () => {
	return mocks.services.agent;
});

vi.stubGlobal('localStorage', {
	getItem: vi.fn(),
	setItem: vi.fn(),
	removeItem: vi.fn(),
});

type PromptSubscriberFn = (prompts: Prompt[]) => void;

describe('prompt', () => {
	function mockPrompt(prompts: Prompt[]) {
		mocks.stores.prompts.subscribe.mockImplementation((subscriberFn: PromptSubscriberFn): Unsubscriber => {
			subscriberFn(prompts);
			return () => { };
		});
	}

	const prompts: Prompt[] = [
		{
			"id": 0,
			"promptDisplayName": "foo-display",
			"prompt": "foo-prompt",
			"agentId": "agent-1"
		},
		{
			"id": 1,
			"promptDisplayName": "bar-display",
			"prompt": "bar-prompt",
			"agentId": "agent-2"
		},
	];

	beforeEach(() => {
		vi.spyOn(localStorage, 'getItem');
		vi.spyOn(localStorage, 'setItem');
		vi.spyOn(localStorage, 'removeItem');
		vi.resetAllMocks();
	});

	describe('selectPrompt()', () => {
		beforeEach(() => {
			mockPrompt(prompts);
		});

		it('should throw if the prompt is not found', async () => {
			await expect(() => selectPrompt(47)).rejects.toThrowError('Prompt not found by prompt ID "47"!');
		});

		it('should store the prompt if found', async () => {
			const prompt = prompts[0];
			await selectPrompt(prompt.id);
			expect(localStorage.setItem).toHaveBeenCalledWith(LOCALSTORAGE_START_PROMPT_KEY, prompt.prompt);
		});

		it('should select the corresponding agent if found', async () => {
			const prompt = prompts[0];
			await selectPrompt(prompt.id);
			expect(mocks.services.agent.selectAgent).toHaveBeenCalledWith(prompt.agentId);
		});
	});

	describe('getAndForgetPrompt()', () => {
		const mockValue = 'mock-prompt';

		beforeEach(() => {
			vi.mocked(localStorage.getItem).mockImplementation((key: string): string|null => {
				if (key === LOCALSTORAGE_START_PROMPT_KEY) {
					return mockValue;
				}
				return null;
			});
		});

		it('should return the prompt from storage', () => {
			expect(getAndForgetPrompt()).toBe(mockValue);
		});

		it('should remove the prompt from storage', () => {
			getAndForgetPrompt();
			expect(localStorage.removeItem).toHaveBeenCalledWith(LOCALSTORAGE_START_PROMPT_KEY);
		});

		it('should return an empty string if not found in storage', () => {
			vi.mocked(localStorage.getItem).mockImplementation((): string|null => {
				return null;
			});
			expect(getAndForgetPrompt()).toBe('');
		});
	});
});
