import { describe, expect, it } from 'vitest';

import { resolveNoteEventContent } from './events';

describe('resolveNoteEventContent', () => {
	it('builds editor content from markdown-only note events', () => {
		const content = resolveNoteEventContent(
			{
				md: '# Original',
				html: '<h1>Original</h1>',
				json: { type: 'doc', content: [] }
			},
			{
				md: '# LLM Edit'
			},
			(md) => `<h1>${md.replace('# ', '')}</h1>`
		);

		expect(content).toEqual({
			md: '# LLM Edit',
			html: '<h1>LLM Edit</h1>',
			json: null
		});
	});
});
