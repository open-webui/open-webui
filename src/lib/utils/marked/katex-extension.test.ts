import { describe, it, expect } from 'vitest';
import { Marked } from 'marked';
import markedKatexExtension from './katex-extension';

const buildMarked = () => {
	const m = new Marked();
	m.use(markedKatexExtension({}));
	return m;
};

// Recursively collect every token type in the tree (inline tokens live under .tokens / .items).
const collectTypes = (tokens: any[], acc: Set<string> = new Set<string>()): Set<string> => {
	for (const t of tokens ?? []) {
		acc.add(t.type);
		if (t.tokens) collectTypes(t.tokens, acc);
		if (t.items) for (const item of t.items) collectTypes(item.tokens ?? [], acc);
	}
	return acc;
};

const countType = (tokens: any[], type: string): number => {
	let n = 0;
	for (const t of tokens ?? []) {
		if (t.type === type) n++;
		if (t.tokens) n += countType(t.tokens, type);
		if (t.items) for (const item of t.items) n += countType(item.tokens ?? [], type);
	}
	return n;
};

describe('katex-extension: $ adjacent to / inside code is not math', () => {
	it('does not turn $ inside inline code spans into math', () => {
		const tokens = buildMarked().lexer('Use `$PATH` and `$HOME` in your shell.');
		const types = collectTypes(tokens);

		expect(types.has('inlineKatex')).toBe(false);
		expect(types.has('blockKatex')).toBe(false);
		expect(countType(tokens, 'codespan')).toBe(2);
	});

	it('rejects a $...$ match whose body contains a backtick', () => {
		const tokens = buildMarked().lexer('value $x = `a`$ end');
		expect(collectTypes(tokens).has('inlineKatex')).toBe(false);
	});
});

describe('katex-extension: real math still renders (no over-correction)', () => {
	it('renders real inline math', () => {
		const tokens = buildMarked().lexer('Pythagoras: $x^2 + y^2 = z^2$ is classic.');
		expect(countType(tokens, 'inlineKatex')).toBe(1);
	});

	it('renders real display math', () => {
		const tokens = buildMarked().lexer('$$\\int_0^1 x\\,dx$$');
		const types = collectTypes(tokens);
		expect(types.has('blockKatex') || types.has('inlineKatex')).toBe(true);
	});

	it('renders math that legitimately follows a closed code span', () => {
		const tokens = buildMarked().lexer('Run `cmd` then compute $a+b$.');
		expect(countType(tokens, 'codespan')).toBe(1);
		expect(countType(tokens, 'inlineKatex')).toBe(1);
	});
});
