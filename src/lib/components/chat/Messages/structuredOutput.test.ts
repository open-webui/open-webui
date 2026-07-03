import { describe, expect, test } from 'vitest';

import { buildOutputDisplayItems } from './structuredOutput';

describe('buildOutputDisplayItems', () => {
	test('skips completed reasoning items with no text', () => {
		const displayItems = buildOutputDisplayItems([
			{
				type: 'reasoning',
				status: 'completed',
				summary: []
			},
			{
				type: 'message',
				id: 'message-1',
				content: [{ type: 'output_text', text: 'Final answer' }]
			}
		]);

		expect(displayItems).toEqual([
			{
				type: 'message',
				id: 'message-1',
				text: 'Final answer'
			}
		]);
	});

	test('keeps completed reasoning items that contain text', () => {
		const displayItems = buildOutputDisplayItems([
			{
				type: 'reasoning',
				status: 'completed',
				summary: [{ type: 'summary_text', text: 'Checked the constraints.' }]
			}
		]);

		expect(displayItems).toHaveLength(1);
		expect(displayItems[0]).toMatchObject({
			type: 'detail_single',
			token: {
				attributes: { type: 'reasoning', done: 'true' },
				text: '> Checked the constraints.'
			}
		});
	});
});
