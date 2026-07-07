import { describe, expect, it } from 'vitest';

import { createFormattedClipboardItemData } from './clipboard';

describe('createFormattedClipboardItemData', () => {
	it('puts source markdown in plain text before formatted html', async () => {
		const markdown = [
			'# Header Test',
			'',
			'## Sub Header',
			'',
			'- Bullet 1',
			'- Bullet 2',
			'',
			'| A | B |',
			'|---|---|',
			'| 1 | 2 |'
		].join('\n');

		const data = createFormattedClipboardItemData(markdown, '<h1>Header Test</h1>');

		expect(Object.keys(data)).toEqual(['text/plain', 'text/html']);
		expect(await data['text/plain'].text()).toBe(markdown);
		expect(await data['text/html'].text()).toBe('<h1>Header Test</h1>');
	});

	it('adds a markdown clipboard format when supported', async () => {
		const markdown = '# Header\n\n- item';
		const data = createFormattedClipboardItemData(markdown, null, (mimeType) => {
			return mimeType === 'text/markdown';
		});

		expect(Object.keys(data).slice(0, 2)).toEqual(['text/plain', 'text/markdown']);
		expect(await data['text/markdown'].text()).toBe(markdown);
	});
});
