import { describe, expect, it } from 'vitest';
import { marked } from 'marked';
import katex from 'katex';
import mathExtension from './katex-extension';

type MathToken = { type: string; text: string; displayMode: boolean; tokens?: MathToken[] };

function mathTokens(source: string): MathToken[] {
	const lexer = new marked.Lexer({ extensions: marked.defaults.extensions });
	return collect(lexer.lex(source) as unknown as MathToken[]);
}

function collect(tokens: MathToken[]): MathToken[] {
	return tokens.flatMap((token) => [
		...(token.type === 'inlineKatex' || token.type === 'blockKatex' ? [token] : []),
		...(token.tokens ? collect(token.tokens) : [])
	]);
}

marked.use(mathExtension());

describe('math in Persian Markdown', () => {
	it.each([
		'اگر $P(B)=0$، نسبت تعریف نمی‌شود.',
		'احتمال$P(B)=0$است.',
		'اگر \\(P(B)=0\\)؛ نسبت تعریف نمی‌شود.',
		'احتمال\\(P(B)=0\\)است.',
		'مقدار $x=1$\u200cاست.',
		'اگر $\\mathbb{P}(B)=0$، نسبت تعریف نمی‌شود.',
		'احتمال $x=1$؟',
		'قيمة$x=1$هي.',
		'اگر $x=1$\u200f باشد.'
	])('recognizes inline math next to Persian letters and punctuation: %s', (source) => {
		const tokens = mathTokens(source);
		expect(tokens).toHaveLength(1);
		expect(tokens[0].displayMode).toBe(false);
		expect(() => katex.renderToString(tokens[0].text, { throwOnError: true })).not.toThrow();
	});

	it.each([
		'فرمول $$\\frac{a}{b}$$، نتیجه است.',
		'فرمول \\[\\frac{a}{b}\\]، نتیجه است.',
		'فرمول:\n\n$$\n\\frac{a}{b}\n$$\n',
		'فرمول:\n\n\\[\n\\frac{a}{b}\n\\]\n'
	])('preserves display mode for display delimiters: %s', (source) => {
		const tokens = mathTokens(source);
		expect(tokens).toHaveLength(1);
		expect(tokens[0].displayMode).toBe(true);
		expect(() => katex.renderToString(tokens[0].text, { throwOnError: true })).not.toThrow();
	});

	it('keeps adjacent Persian formulas separate and leaves incomplete streaming math as text', () => {
		const tokens = mathTokens('اگر $P(B)=0$، آنگاه $P(A)=1$ است.');
		expect(tokens.map((token) => token.text)).toEqual(['P(B)=0', 'P(A)=1']);
		expect(mathTokens('اگر $\\frac{a}{b}')).toHaveLength(0);
		expect(mathTokens('اگر $\\frac{a}{b}$، درست است.')).toHaveLength(1);
	});

	it('does not change escaped dollars or code', () => {
		expect(mathTokens('قیمت \\$5 و ` $x$ ` است.')).toHaveLength(0);
		expect(mathTokens('```tex\n$x$\n```')).toHaveLength(0);
	});

	it('does not treat English currency as math', () => {
		expect(mathTokens('It costs $5 and $10 today.')).toHaveLength(0);
	});
});
