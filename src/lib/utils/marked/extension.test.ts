import { Marked } from 'marked';
import { describe, expect, test } from 'vitest';

import markedExtension from './extension';

const createMarked = () => new Marked(markedExtension());

const findDetailsToken = (tokens: { type: string }[]) =>
	tokens.find((token) => token.type === 'details');

describe('marked details extension', () => {
	test.each([
		['bare --- without a blank line', 'line one\n---\nline two'],
		['bare === without a blank line', 'line one\n===\nline two'],
		['content without setext marker and without a blank line', 'line one\nline two']
	])('keeps paragraph and details separate for %s', (_, body) => {
		const marked = createMarked();
		const tokens = marked.lexer(`Here is some introductory text before the widget.
<details>
<summary>Click to expand</summary>
${body}
</details>`);

		expect(tokens[0]).toMatchObject({
			type: 'paragraph',
			text: 'Here is some introductory text before the widget.'
		});
		expect(tokens[1]).toMatchObject({
			type: 'details',
			summary: 'Click to expand',
			text: body
		});
		expect(tokens).toHaveLength(2);
	});

	test('keeps details with a preceding blank line separate', () => {
		const marked = createMarked();
		const tokens = marked.lexer(`Here is some introductory text before the widget.

<details>
<summary>Click to expand</summary>
line one
---
line two
</details>`);

		expect(tokens[0]).toMatchObject({ type: 'paragraph' });
		const details = findDetailsToken(tokens);
		expect(details).toMatchObject({
			type: 'details',
			summary: 'Click to expand',
			text: 'line one\n---\nline two'
		});
	});

	test('preserves ordinary setext headings and horizontal rules outside details blocks', () => {
		const marked = createMarked();
		const setextTokens = marked.lexer('Heading\n---');
		const hrTokens = marked.lexer('---');

		expect(setextTokens[0]).toMatchObject({ type: 'heading', depth: 2, text: 'Heading' });
		expect(hrTokens[0]).toMatchObject({ type: 'hr' });
	});

	test('does not tokenize details markup inside fenced code or inline code', () => {
		const marked = createMarked();
		const fencedTokens = marked.lexer(`\`\`\`
Here is some introductory text before the widget.
<details>
<summary>Click to expand</summary>
line one
---
line two
</details>
\`\`\``);
		const inlineTokens = marked.lexer('`<details>`');

		expect(fencedTokens[0]).toMatchObject({ type: 'code' });
		expect(findDetailsToken(fencedTokens)).toBeUndefined();
		expect(inlineTokens[0]).toMatchObject({ type: 'paragraph', text: '`<details>`' });
		expect(findDetailsToken(inlineTokens)).toBeUndefined();
	});

	test('preserves supported details attributes and nested details blocks', () => {
		const marked = createMarked();
		const tokens = marked.lexer(`<details open="true" class="abc">
<summary>Outer</summary>
outer
<details>
<summary>Inner</summary>
inner
</details>
</details>`);

		expect(tokens[0]).toMatchObject({
			type: 'details',
			summary: 'Outer',
			attributes: { open: 'true', class: 'abc' }
		});
		expect(tokens[0]).toMatchObject({ text: expect.stringContaining('<details>') });
		expect(tokens).toHaveLength(1);
	});

	test('does not consume malformed unclosed details markup', () => {
		const marked = createMarked();
		const tokens = marked.lexer(`<details>
<summary>Click to expand</summary>
line one`);

		expect(findDetailsToken(tokens)).toBeUndefined();
	});

	test('handles CRLF input consistently with LF input', () => {
		const marked = createMarked();
		const tokens = marked.lexer(
			'Here is some introductory text before the widget.\r\n<details>\r\n<summary>Click to expand</summary>\r\nline one\r\n---\r\nline two\r\n</details>'
		);

		expect(tokens[0]).toMatchObject({ type: 'paragraph' });
		const details = findDetailsToken(tokens);
		expect(details).toMatchObject({
			type: 'details',
			summary: 'Click to expand',
			text: 'line one\n---\nline two'
		});
	});

	test.each([
		['with a setext marker', 'line one\n---\nline two'],
		['without a setext marker', 'line one\nline two']
	])('keeps a multi-line paragraph intact %s', (_, body) => {
		const marked = createMarked();
		const tokens = marked.lexer(`First line of the introduction.
Second line of the introduction.
<details>
<summary>Click to expand</summary>
${body}
</details>`);

		expect(tokens[0]).toMatchObject({
			type: 'paragraph',
			text: 'First line of the introduction.\nSecond line of the introduction.'
		});
		expect(tokens[1]).toMatchObject({ type: 'details', text: body });
		expect(tokens).toHaveLength(2);
	});

	test('does not coerce native block tokens into paragraphs before details', () => {
		const marked = createMarked();
		const listTokens = marked.lexer(`- list item
<details>
<summary>Click to expand</summary>
line one
---
line two
</details>`);
		const blockquoteTokens = marked.lexer(`> quoted text
<details>
<summary>Click to expand</summary>
line one
---
line two
</details>`);

		expect(listTokens[0]).toMatchObject({ type: 'list' });
		expect(blockquoteTokens[0]).toMatchObject({ type: 'blockquote' });
		expect(blockquoteTokens[1]).toMatchObject({ type: 'details' });
	});
});
