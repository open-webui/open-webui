import { describe, expect, it } from 'vitest';

import { buildOutputDisplayItems } from './structuredOutput';

describe('buildOutputDisplayItems', () => {
	it('does not render empty completed reasoning details', () => {
		const items = buildOutputDisplayItems([
			{
				type: 'message',
				id: 'msg-1',
				content: [{ type: 'output_text', text: 'Answer' }]
			},
			{
				type: 'reasoning',
				id: 'reasoning-empty',
				status: 'completed',
				content: [{ type: 'output_text', text: '' }]
			}
		]);

		expect(items).toEqual([
			{
				type: 'message',
				id: 'msg-1',
				text: 'Answer'
			}
		]);
	});

	it('still renders reasoning details when reasoning text is present', () => {
		const items = buildOutputDisplayItems([
			{
				type: 'reasoning',
				id: 'reasoning-1',
				status: 'completed',
				duration: 3,
				content: [{ type: 'output_text', text: 'Actual reasoning' }]
			},
			{
				type: 'message',
				id: 'msg-1',
				content: [{ type: 'output_text', text: 'Answer' }]
			}
		]);

		expect(items[0]).toMatchObject({
			type: 'detail_single',
			token: {
				summary: 'Thought for 3 seconds',
				text: '> Actual reasoning',
				attributes: {
					type: 'reasoning',
					done: 'true',
					duration: '3'
				}
			}
		});
		expect(items[1]).toEqual({
			type: 'message',
			id: 'msg-1',
			text: 'Answer'
		});
	});
});
