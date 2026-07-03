import { describe, expect, it } from 'vitest';

import { getArtifactCodeBlockSignature, isArtifactCodeToken } from './artifacts';

describe('artifact code block detection', () => {
	it('detects html code blocks in completed message content', () => {
		const content = [
			'Here is a preview:',
			'',
			'```html',
			'<div>Rendered after an outlet filter</div>',
			'```'
		].join('\n');

		expect(getArtifactCodeBlockSignature(content)).toBe(
			'html\n<div>Rendered after an outlet filter</div>'
		);
	});

	it('ignores non-artifact code blocks', () => {
		expect(getArtifactCodeBlockSignature('```markdown\n# Title\n```')).toBeNull();
		expect(isArtifactCodeToken({ lang: 'json', text: '{"svg": true}' })).toBe(false);
	});

	it('detects svg artifacts emitted as xml', () => {
		expect(isArtifactCodeToken({ lang: 'xml', text: '<svg viewBox="0 0 1 1"></svg>' })).toBe(true);
	});
});
