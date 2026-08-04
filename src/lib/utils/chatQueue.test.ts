import { describe, expect, it } from 'vitest';
import { dequeueChatRequest, type ChatRequestQueues } from './chatQueue';

describe('dequeueChatRequest', () => {
	it('dequeues only the oldest request and preserves later requests', () => {
		const queues: ChatRequestQueues = {
			chat: [
				{ id: 'first', prompt: 'First prompt', files: [{ id: 'first-file' }] },
				{ id: 'second', prompt: 'Second prompt', files: [{ id: 'second-file' }] }
			],
			other: [{ id: 'other', prompt: 'Other chat', files: [] }]
		};

		const result = dequeueChatRequest(queues, 'chat');

		expect(result.request).toEqual(queues.chat[0]);
		expect(result.queues).toEqual({
			chat: [queues.chat[1]],
			other: queues.other
		});
		expect(queues.chat).toHaveLength(2);
	});

	it('removes the chat queue after dequeuing its last request', () => {
		const queues: ChatRequestQueues = {
			chat: [{ id: 'only', prompt: 'Only prompt', files: [] }]
		};

		expect(dequeueChatRequest(queues, 'chat')).toEqual({
			queues: {},
			request: queues.chat[0]
		});
	});

	it('leaves queues unchanged when the chat has no pending request', () => {
		const queues: ChatRequestQueues = {};

		expect(dequeueChatRequest(queues, 'chat')).toEqual({
			queues,
			request: null
		});
	});
});
