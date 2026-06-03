import { describe, expect, it } from 'vitest';

import { appendTaskIds, canClearTaskIds } from './taskIds';

describe('chat task id tracking', () => {
	it('preserves task ids written by a newer send while completion work is pending', () => {
		const completionGeneration = 2;
		const currentGeneration = completionGeneration + 1;

		expect(canClearTaskIds(completionGeneration, currentGeneration)).toBe(false);
	});

	it('allows completion cleanup when no newer send has written task ids', () => {
		const completionGeneration = 2;

		expect(canClearTaskIds(completionGeneration, completionGeneration)).toBe(true);
	});

	it('appends new task ids without mutating the previous task id list', () => {
		const previousTaskIds = ['title-task'];
		const nextTaskIds = appendTaskIds(previousTaskIds, ['follow-up-task']);

		expect(previousTaskIds).toEqual(['title-task']);
		expect(nextTaskIds).toEqual(['title-task', 'follow-up-task']);
	});

	it('does not treat an empty task id response as a newer cancellable task', () => {
		expect(appendTaskIds(['title-task'], [])).toEqual(['title-task']);
	});
});
