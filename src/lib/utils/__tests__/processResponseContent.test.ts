import { describe, it, expect } from 'vitest';
import { processResponseContent } from '$lib/utils';
import { marked, type Token } from 'marked';
import markedExtension from '$lib/utils/marked/extension';

// Wire up the same block/inline extensions the chat Markdown renderer uses so we
// exercise the real pipeline (processResponseContent -> marked lexer).
marked.use(markedExtension({}));

const tokenTypes = (src: string): string[] =>
	marked
		.lexer(processResponseContent(src))
		.map((t: Token) => t.type + (t.type === 'heading' ? `(depth ${(t as any).depth})` : ''));

const hasDetailsWidget = (src: string): boolean => {
	const tokens = marked.lexer(processResponseContent(src));
	// A correctly-rendered <details> block produces either a custom `details`
	// token (this extension) or an `html` token whose raw starts with `<details`
	// (no heading swallowing the tag source).
	return tokens.some(
		(t) => (t.type === 'details' || t.type === 'html') && (t.raw ?? '').startsWith('<details')
	);
};

describe('processResponseContent - #27001 details/setext heading regression', () => {
	it('precedes a <details> block with a blank line so it is not swallowed into a heading', () => {
		const input = [
			'Here is some introductory text before the widget.',
			'<details>',
			'<summary>Click to expand</summary>',
			'line one',
			'---',
			'line two',
			'</details>'
		].join('\n');

		const output = processResponseContent(input);

		// The paragraph and the <details> tag must be separated by a blank line.
		expect(output).toContain(
			'Here is some introductory text before the widget.\n\n<details>'
		);
	});

	it('renders a real collapsed details widget (not a heading) when bare --- is present', () => {
		const input = [
			'Here is some introductory text before the widget.',
			'<details>',
			'<summary>Click to expand</summary>',
			'line one',
			'---',
			'line two',
			'</details>'
		].join('\n');

		expect(tokenTypes(input)).not.toContain('heading(depth 2)');
		expect(hasDetailsWidget(input)).toBe(true);
	});

	it('renders a real collapsed details widget (not a heading) when bare === is present', () => {
		const input = [
			'Here is some introductory text before the widget.',
			'<details>',
			'<summary>Click to expand</summary>',
			'line one',
			'===',
			'line two',
			'</details>'
		].join('\n');

		expect(tokenTypes(input)).not.toContain('heading(depth 1)');
		expect(hasDetailsWidget(input)).toBe(true);
	});

	it('does not add a blank line when one already exists (no double spacing)', () => {
		const input = [
			'Here is some introductory text before the widget.',
			'',
			'<details>',
			'<summary>Click to expand</summary>',
			'line one',
			'---',
			'line two',
			'</details>'
		].join('\n');

		const output = processResponseContent(input);
		expect(output).not.toContain('\n\n\n<details>');
		expect(hasDetailsWidget(input)).toBe(true);
	});

	it('handles <details> with attributes directly after prose', () => {
		const input = [
			'Some prose.',
			'<details type="tool_calls" name="search">',
			'<summary>Tool call</summary>',
			'result',
			'---',
			'</details>'
		].join('\n');

		const output = processResponseContent(input);
		expect(output).toContain('Some prose.\n\n<details type="tool_calls" name="search">');
		expect(tokenTypes(input)).not.toContain('heading(depth 2)');
	});

	it('leaves standalone paragraphs without a trailing <details> untouched', () => {
		const input = 'Just a normal paragraph.\nAnother line without details.\n---';
		const output = processResponseContent(input);
		// No <details> present, so the normalization should not change anything
		// beyond the existing trim.
		expect(output).toBe(input.trim());
	});
});
