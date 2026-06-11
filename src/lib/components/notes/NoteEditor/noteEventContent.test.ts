import { describe, expect, it } from 'vitest';

import { resolveIncomingNoteContent } from './noteEventContent';

describe('resolveIncomingNoteContent', () => {
	it('rebuilds html and clears json when an incoming note event only provides markdown', () => {
		const next = resolveIncomingNoteContent(
			{
				json: { type: 'doc', stale: true },
				html: '<p>Old content</p>',
				md: 'Old content'
			},
			{
				md: '# LLM Edit\nLLM wrote this.'
			}
		);

		expect(next.md).toBe('# LLM Edit\nLLM wrote this.');
		expect(next.html).toContain('<h1>LLM Edit</h1>');
		expect(next.html).toContain('<p>LLM wrote this.</p>');
		expect(next.json).toBeNull();
	});

	it('preserves explicit html and json from the incoming content payload', () => {
		const next = resolveIncomingNoteContent(
			{
				json: null,
				html: '<p>Old content</p>',
				md: 'Old content'
			},
			{
				json: { type: 'doc', content: [] },
				html: '<p>New content</p>',
				md: 'New content'
			}
		);

		expect(next).toEqual({
			json: { type: 'doc', content: [] },
			html: '<p>New content</p>',
			md: 'New content'
		});
	});
});
