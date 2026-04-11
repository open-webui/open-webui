import { describe, expect, it } from 'vitest';
import { Marked } from 'marked';

import katexExtension from './katex-extension';

const createMarked = () => {
	const parser = new Marked();
	parser.use(katexExtension({ throwOnError: false, breaks: true }));
	return parser;
};

const collectKatexTokens = (tokens: any[]): any[] => {
	const result: any[] = [];

	for (const token of tokens) {
		if (token.type === 'inlineKatex' || token.type === 'blockKatex') {
			result.push(token);
		}

		if (token.tokens) {
			result.push(...collectKatexTokens(token.tokens));
		}
	}

	return result;
};

describe('katex-extension', () => {
	it('renders balanced single-line $$...$$ as display math', () => {
		const tokens = createMarked().lexer('$$x^2$$');

		expect(tokens).toHaveLength(1);
		expect(tokens[0]).toMatchObject({
			type: 'blockKatex',
			text: 'x^2',
			displayMode: true
		});
	});

	it('renders multiline $$...$$ as display math', () => {
		const input = '$$\n\\int_0^1 x^2 \\, dx\n= \\frac{1}{3}\n$$';
		const tokens = createMarked().lexer(input);

		expect(tokens).toHaveLength(1);
		expect(tokens[0]).toMatchObject({
			type: 'blockKatex',
			text: '\n\\int_0^1 x^2 \\, dx\n= \\frac{1}{3}\n',
			displayMode: true
		});
	});

	it('treats trailing spaces before newline as a block boundary', () => {
		const tokens = createMarked().lexer('$$x^2$$   \nnext line');

		expect(tokens[0]).toMatchObject({
			type: 'blockKatex',
			text: 'x^2',
			displayMode: true
		});
	});

	it('treats CRLF after closing $$ as a block boundary', () => {
		const tokens = createMarked().lexer('$$x^2$$\r\nnext line');

		expect(tokens[0]).toMatchObject({
			type: 'blockKatex',
			text: 'x^2',
			displayMode: true
		});
	});

	it('leaves stray $$ as plain text', () => {
		const tokens = createMarked().lexer('stray $$ delimiter');

		expect(collectKatexTokens(tokens)).toHaveLength(0);
		expect(tokens[0]?.type).toBe('paragraph');
		expect(tokens[0]?.text).toContain('stray');
		expect(tokens[0]?.text).toContain('$$ delimiter');
	});

	it('leaves normal prose with dollar signs untouched', () => {
		const tokens = createMarked().lexer('The total is $5.00 in normal prose.');

		expect(collectKatexTokens(tokens)).toHaveLength(0);
		expect(tokens[0]).toMatchObject({
			type: 'paragraph',
			text: 'The total is $5.00 in normal prose.'
		});
	});

	it('keeps punctuation after closing $$ attached to the surrounding paragraph', () => {
		const tokens = createMarked().lexer('Result: $$x^2$$.');
		const mathTokens = collectKatexTokens(tokens);

		expect(tokens[0]?.type).toBe('paragraph');
		expect(mathTokens).toHaveLength(1);
		expect(mathTokens[0]).toMatchObject({
			type: 'inlineKatex',
			text: 'x^2',
			displayMode: true
		});
		expect(tokens[0]?.text).toContain('.');
	});

	it('does not interfere with fenced math code blocks', () => {
		const tokens = createMarked().lexer('```math\nx^2\n```');

		expect(tokens).toHaveLength(1);
		expect(tokens[0]).toMatchObject({
			type: 'code',
			lang: 'math',
			text: 'x^2'
		});
	});
});
