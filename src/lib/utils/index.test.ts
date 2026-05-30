import { describe, expect, it } from 'vitest';

import { replaceOutsideCode } from './index';

const removeCitationMarkers = (content: string) =>
	replaceOutsideCode(content, (segment) =>
		segment.replace(/\s*(\[(?:\d+(?:#[^,\]\s]+)?(?:,\s*\d+(?:#[^,\]\s]+)?)*)\])+/g, '')
	);

describe('replaceOutsideCode', () => {
	it('applies replacements outside code', () => {
		expect(removeCitationMarkers('Alpha [1] beta [2, 3#page].')).toBe('Alpha beta.');
	});

	it('preserves citation-like brackets inside fenced code blocks', () => {
		const content = ['Before [1]', '```python', 'data = [0]', 'values = [1, 2, 3]', '```'].join(
			'\n'
		);

		expect(removeCitationMarkers(content)).toBe(
			['Before', '```python', 'data = [0]', 'values = [1, 2, 3]', '```'].join('\n')
		);
	});

	it('preserves citation-like brackets inside tilde fenced code blocks', () => {
		const content = ['Before [1]', '~~~python', 'data = [0]', 'values = [1, 2, 3]', '~~~'].join(
			'\n'
		);

		expect(removeCitationMarkers(content)).toBe(
			['Before', '~~~python', 'data = [0]', 'values = [1, 2, 3]', '~~~'].join('\n')
		);
	});

	it('preserves citation-like brackets inside inline code', () => {
		expect(removeCitationMarkers('Use `data = [0]` here [1].')).toBe('Use `data = [0]` here.');
	});
});
