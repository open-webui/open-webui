import { describe, expect, it } from 'vitest';

import {
	deepestDescendantId,
	isDescendantMessage,
	restoreStoppedResponse,
	shouldProcessQueueAfterTaskCancel
} from './chat-history';

describe('restoreStoppedResponse', () => {
	it('writes the interrupted reply back onto its own id, not the later currentId', () => {
		const interrupted = {
			id: 'story-reply',
			parentId: 'story-user',
			childrenIds: [],
			content: 'once upon a time'
		};
		const nextReply = {
			id: 'no-reply',
			parentId: 'no-user',
			childrenIds: [],
			content: ''
		};
		const history = {
			currentId: 'no-reply',
			messages: {
				'story-reply': interrupted,
				'no-reply': nextReply
			}
		};

		restoreStoppedResponse(history, interrupted);

		expect(history.messages['story-reply']).toBe(interrupted);
		expect(history.messages['no-reply']).toBe(nextReply);
		expect(history.messages['no-reply'].content).toBe('');
	});
});

describe('shouldProcessQueueAfterTaskCancel', () => {
	it('flushes the queue when Stop cancels the current reply', () => {
		expect(
			shouldProcessQueueAfterTaskCancel({
				cancelMessageId: 'story-reply',
				currentId: 'story-reply',
				skipQueueOnTaskCancel: false
			})
		).toBe(true);
	});

	it('keeps remaining queued messages when Send now is stopping the current reply', () => {
		expect(
			shouldProcessQueueAfterTaskCancel({
				cancelMessageId: 'story-reply',
				currentId: 'story-reply',
				skipQueueOnTaskCancel: true
			})
		).toBe(false);
	});

	it('does not flush after currentId has already moved to the Send now reply', () => {
		expect(
			shouldProcessQueueAfterTaskCancel({
				cancelMessageId: 'story-reply',
				currentId: 'no-reply',
				skipQueueOnTaskCancel: false
			})
		).toBe(false);
	});
});

describe('deepestDescendantId', () => {
	it('follows the last child', () => {
		const messages = {
			root: { childrenIds: ['a'] },
			a: { childrenIds: ['b'] },
			b: { childrenIds: [] }
		};
		expect(deepestDescendantId(messages, 'root')).toBe('b');
	});

	it('stops on a childrenIds cycle instead of looping forever', () => {
		const messages = {
			clicked: { childrenIds: ['sibling'] },
			sibling: { childrenIds: ['clicked'] }
		};
		expect(deepestDescendantId(messages, 'clicked')).toBe('sibling');
	});

	it('returns the last unique node in a longer cycle', () => {
		const messages = {
			a: { childrenIds: ['b'] },
			b: { childrenIds: ['c'] },
			c: { childrenIds: ['a'] }
		};
		expect(deepestDescendantId(messages, 'a')).toBe('c');
	});
});

describe('isDescendantMessage', () => {
	it('returns false on a cycle instead of overflowing the stack', () => {
		const messages = {
			a: { childrenIds: ['b'] },
			b: { childrenIds: ['a'] }
		};
		expect(isDescendantMessage(messages, 'a', 'missing')).toBe(false);
	});
});
