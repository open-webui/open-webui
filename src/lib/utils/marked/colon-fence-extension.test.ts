import { describe, expect, it } from 'vitest';
import { Marked } from 'marked';

import colonFenceExtension from './colon-fence-extension';

type ColonFenceToken = {
	type: string;
	fenceType: string;
	attributes: Record<string, string>;
	text: string;
};

const firstFence = (src: string) => {
	const marked = new Marked();
	marked.use(colonFenceExtension());
	const tokens = marked.lexer(src) as unknown as ColonFenceToken[];
	return tokens.find((token) => token.type === 'colonFence') as ColonFenceToken;
};

describe('colon fence extension', () => {
	it('tokenizes a block without attributes', () => {
		const token = firstFence(':::writing\n\nHello\n:::\n');

		expect(token.fenceType).toBe('writing');
		expect(token.attributes).toEqual({});
		expect(token.text).toBe('Hello');
	});

	it('parses the attributes on the opening line', () => {
		const token = firstFence(
			':::writing{variant="email" id="48173" subject="Short question" recipient="mail@example.com"}\n\nHello\n:::\n'
		);

		expect(token.attributes).toEqual({
			variant: 'email',
			id: '48173',
			subject: 'Short question',
			recipient: 'mail@example.com'
		});
		expect(token.text).toBe('Hello');
	});

	it('does not read attributes from unbraced trailing text', () => {
		const token = firstFence(':::writing{variant="document"} draft subject="junk"\n\nHello\n:::\n');

		expect(token.attributes).toEqual({ variant: 'document' });
	});

	it('ignores an opening line that has no braces at all', () => {
		const token = firstFence(
			':::note prose mentioning recipient="evil@example.com"\n\nHello\n:::\n'
		);

		expect(token.fenceType).toBe('note');
		expect(token.attributes).toEqual({});
	});

	it('ignores an unclosed brace', () => {
		const token = firstFence(':::writing{subject="Short question"\n\nHello\n:::\n');

		expect(token.attributes).toEqual({});
	});

	it('allows braces inside an attribute value', () => {
		const token = firstFence(':::writing{subject="use {x} here"}\n\nHello\n:::\n');

		expect(token.attributes.subject).toBe('use {x} here');
	});
});
