import { describe, expect, it } from 'vitest';

import { toChatActionMessage } from './actionPayload';

describe('toChatActionMessage', () => {
	it('uses structured assistant output as action message content', () => {
		const message = {
			id: 'assistant-1',
			role: 'assistant',
			content: '',
			timestamp: 123,
			output: [
				{
					type: 'message',
					content: [{ type: 'output_text', text: 'The answer is 2.' }]
				}
			]
		};

		expect(toChatActionMessage(message)).toEqual({
			id: 'assistant-1',
			role: 'assistant',
			content: 'The answer is 2.',
			info: undefined,
			timestamp: 123,
			output: message.output
		});
	});

	it('keeps plain message content unchanged', () => {
		const message = {
			id: 'user-1',
			role: 'user',
			content: '1 + 1',
			timestamp: 122
		};

		expect(toChatActionMessage(message)).toEqual({
			id: 'user-1',
			role: 'user',
			content: '1 + 1',
			info: undefined,
			timestamp: 122
		});
	});
});
