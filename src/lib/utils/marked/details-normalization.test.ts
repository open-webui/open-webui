import { describe, expect, it } from 'vitest';
import { Marked } from 'marked';

import { normalizeStructuralDetailsBlocks } from './details-normalization';
import markedExtension from './extension';

const lexerWithDetails = (value: string) => {
	const parser = new Marked();
	parser.use(markedExtension());

	return parser.lexer(value);
};

describe('normalizeStructuralDetailsBlocks', () => {
	it('separates structural details from adjacent assistant prose', () => {
		const input = [
			'<details type="reasoning" done="true">',
			'<summary>Thought</summary>',
			'&gt; private notes',
			'</details>',
			'Assistant answer',
			'<details type="tool_calls" done="true" arguments="&quot;{\\&quot;command\\&quot;:\\&quot;echo hi\\&quot;}&quot;">',
			'<summary>tool</summary>',
			'{}',
			'</details>',
			'Done'
		].join('\n');

		expect(normalizeStructuralDetailsBlocks(input)).toBe(
			[
				'<details type="reasoning" done="true">',
				'<summary>Thought</summary>',
				'&gt; private notes',
				'</details>',
				'Assistant answer',
				'',
				'<details type="tool_calls" done="true" arguments="&quot;{\\&quot;command\\&quot;:\\&quot;echo hi\\&quot;}&quot;">',
				'<summary>tool</summary>',
				'{}',
				'</details>',
				'Done'
			].join('\n')
		);
	});

	it('does not add separator tokens between consecutive structural details', () => {
		const input = [
			'<details type="reasoning" done="true">',
			'<summary>Thought</summary>',
			'&gt; private notes',
			'</details>',
			'<details type="tool_calls" done="true" arguments="&quot;{}&quot;">',
			'<summary>tool</summary>',
			'{}',
			'</details>'
		].join('\n');

		expect(normalizeStructuralDetailsBlocks(input)).toBe(input);
	});

	it('lets marked tokenize structural details that directly follow prose', () => {
		const toolCallWithMultilineArguments = `<details type="tool_calls" done="true" arguments="&quot;{\\&quot;command\\&quot;:\\&quot;# Analyze each file
DIR=/tmp/data
echo ===== file =====\\&quot;}&quot;">`;
		const input = [
			'<details type="reasoning" done="true">',
			'<summary>Thought</summary>',
			'&gt; private notes',
			'</details>',
			'Assistant answer',
			toolCallWithMultilineArguments,
			'<summary>tool</summary>',
			'{}',
			'</details>',
			'Done'
		].join('\n');

		expect(
			lexerWithDetails(normalizeStructuralDetailsBlocks(input)).some(
				(token) => token.type === 'details'
			)
		).toBe(true);
	});

	it('leaves ordinary details and unmatched structural details unchanged', () => {
		const ordinary = '<details>\n<summary>Normal</summary>\ncontent\n</details>\ntext';
		const unmatched = 'before\n<details type="tool_calls">\nmissing close';

		expect(normalizeStructuralDetailsBlocks(ordinary)).toBe(ordinary);
		expect(normalizeStructuralDetailsBlocks(unmatched)).toBe(unmatched);
	});
});
