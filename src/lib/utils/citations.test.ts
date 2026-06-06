import { describe, expect, it } from 'vitest';

import { removeCitationMarkersOutsideCode } from './citations';

describe('removeCitationMarkersOutsideCode', () => {
	it('removes citation markers from prose', () => {
		const content = 'Answer [1] and more text [2, 3#chunk].';

		expect(removeCitationMarkersOutsideCode(content)).toBe('Answer and more text.');
	});

	it('preserves citation-like brackets inside inline code', () => {
		const content = 'Use `[1]` in arrays, then cite [2].';

		expect(removeCitationMarkersOutsideCode(content)).toBe('Use `[1]` in arrays, then cite.');
	});

	it('preserves citation-like brackets inside fenced code blocks', () => {
		const content = `Before [1]

\`\`\`javascript
const value = items[0];
const marker = "[2]";
\`\`\`

After [2].`;

		expect(removeCitationMarkersOutsideCode(content)).toBe(`Before

\`\`\`javascript
const value = items[0];
const marker = "[2]";
\`\`\`

After.`);
	});
});
