import { describe, expect, it, vi } from 'vitest';

import { createMarkdownUpdateScheduler, resolveMarkdownDone } from './markdown-update-scheduler';

describe('createMarkdownUpdateScheduler', () => {
	it('coalesces the fade-disabled done path onto the pending frame', () => {
		let content = '';
		let done = resolveMarkdownDone(false, false);
		const parsed: Array<{ content: string; done: boolean }> = [];
		const frames: FrameRequestCallback[] = [];
		const requestFrame = vi.fn((callback: FrameRequestCallback) => {
			frames.push(callback);
			return frames.length;
		});
		const scheduler = createMarkdownUpdateScheduler(
			() => parsed.push({ content, done }),
			requestFrame,
			vi.fn()
		);

		scheduler.update(content);
		expect(requestFrame).not.toHaveBeenCalled();

		content = 'partial';
		scheduler.update(content);
		content = 'final';
		done = resolveMarkdownDone(false, true);
		scheduler.update(content);

		expect(requestFrame).toHaveBeenCalledTimes(1);
		expect(parsed).toEqual([]);

		frames[0](16);
		expect(parsed).toEqual([{ content: 'final', done: true }]);
	});

	it('cancels a pending frame on teardown', () => {
		const cancelFrame = vi.fn();
		const scheduler = createMarkdownUpdateScheduler(
			vi.fn(),
			vi.fn(() => 42),
			cancelFrame
		);

		scheduler.update('streaming');
		scheduler.cancel();
		scheduler.cancel();

		expect(cancelFrame).toHaveBeenCalledOnce();
		expect(cancelFrame).toHaveBeenCalledWith(42);
	});
});

describe('resolveMarkdownDone', () => {
	it.each([
		{ fadeStreamingText: false, messageDone: false, expected: true },
		{ fadeStreamingText: false, messageDone: true, expected: true },
		{ fadeStreamingText: true, messageDone: false, expected: false },
		{ fadeStreamingText: true, messageDone: true, expected: true },
		{ fadeStreamingText: undefined, messageDone: false, expected: false }
	])(
		'returns $expected when fadeStreamingText=$fadeStreamingText and messageDone=$messageDone',
		({ fadeStreamingText, messageDone, expected }) => {
			expect(resolveMarkdownDone(fadeStreamingText, messageDone)).toBe(expected);
		}
	);
});
