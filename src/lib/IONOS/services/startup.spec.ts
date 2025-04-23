import { describe, beforeEach, expect, it, vi } from 'vitest';
import {
	startup,
	hasStoredState,
} from './startup';

const mocks = vi.hoisted(() => {
	return {
		services: {
			agent: {
				getAndForgetAgent: vi.fn(),
				hasAgent: vi.fn(),
			},
			prompt: {
				getAndForgetPrompt: vi.fn(),
				hasPrompt: vi.fn(),
			},
			settings: {
				updateSettings: vi.fn(),
			},
		},
	};
});

vi.mock('$lib/IONOS/services/agent', async () => {
	return mocks.services.agent;
});

vi.mock('$lib/IONOS/services/prompt', async () => {
	return mocks.services.prompt;
});

vi.mock('$lib/IONOS/services/settings', async () => {
	return mocks.services.settings;
});

describe('startup', () => {
	beforeEach(() => {
		startup();
	});

	describe('startup()', () => {
		const mockAgent = 'agent-foo';
		const mockPrompt = 'prompt-foo';

		beforeEach(() => {
			mocks.services.agent.getAndForgetAgent.mockImplementation(() => {
				return mockAgent;
			});

			mocks.services.prompt.getAndForgetPrompt.mockImplementation(() => {
				return mockPrompt;
			});
		});

		it('should get and forget the agent', async () => {
			await startup();
			expect(mocks.services.agent.getAndForgetAgent).toHaveBeenCalled();
		});

		it('should return an empty agent and prompt if no agent was stored', async () => {
			mocks.services.agent.getAndForgetAgent.mockImplementation(() => {
				return '';
			});
			expect(await startup()).toEqual({ agent: '', prompt: '' });
		});

		it('should store the agent', async () => {
			await startup();
			expect(mocks.services.settings.updateSettings).toHaveBeenCalledWith({ models: [mockAgent] });
		});

		describe('no prompt was stored', () => {
			beforeEach(() => {
				mocks.services.prompt.getAndForgetPrompt.mockImplementation(() => {
					return '';
				});
			});

			it('should get and forget the prompt', async () => {
				await startup();
				expect(mocks.services.prompt.getAndForgetPrompt).toHaveBeenCalled();
			});

			it('should return an empty prompt but return the agent', async () => {
				expect(await startup()).toEqual({ agent: mockAgent, prompt: '' });
			});
		});

		it('should return both agent and prompt if both are stored', async () => {
			expect(await startup()).toEqual({ agent: mockAgent, prompt: mockPrompt });
		});
	});

	describe('hasStoredState()', () => {
		let hasAgent = false;
		let hasPrompt = false;

		beforeEach(() => {
			mocks.services.agent.hasAgent.mockImplementation(() => {
				return hasAgent;
			});

			mocks.services.prompt.hasPrompt.mockImplementation(() => {
				return hasPrompt;
			});
		});

		it('return true only if either agent or prompt is stored', () => {
			expect(hasStoredState()).toBe(false);

			hasAgent = true;
			expect(hasStoredState()).toBe(true);

			hasAgent = false;
			hasPrompt = true;
			expect(hasStoredState()).toBe(true);

			hasAgent = true;
			hasPrompt = true;
			expect(hasStoredState()).toBe(true);
		});
	});
});
