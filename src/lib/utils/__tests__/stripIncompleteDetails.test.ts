import { describe, it, expect } from 'vitest';
import { stripIncompleteDetails } from '$lib/utils';

describe('stripIncompleteDetails (ACP-5048)', () => {
	it('leaves complete details blocks intact', () => {
		const content =
			'<details type="streaming">\n<summary>S</summary>\nevents\n</details>\n\n---\n\nFinal answer';
		expect(stripIncompleteDetails(content)).toBe(content);
	});

	it('removes incomplete opening tag at end', () => {
		const content = 'Some text\n<details type="strea';
		const result = stripIncompleteDetails(content);
		expect(result).toBe('Some text\n');
	});

	it('removes incomplete details block without closing tag', () => {
		const content =
			'<details type="streaming">\n<summary>🔄 Real-time Agent Execution</summary>\n\n🚀 Starting...';
		const result = stripIncompleteDetails(content);
		expect(result).toBe('');
	});

	it('removes only the unclosed block, keeps closed ones', () => {
		const content =
			'<details type="reasoning">\n<summary>R</summary>\nthoughts\n</details>\n' +
			'<details type="streaming">\n<summary>S</summary>\nevents...';
		const result = stripIncompleteDetails(content);
		expect(result).toContain('</details>');
		expect(result).toContain('type="reasoning"');
		expect(result).not.toContain('type="streaming"');
	});

	it('handles content with no details tags', () => {
		const content = 'Just some regular markdown content';
		expect(stripIncompleteDetails(content)).toBe(content);
	});

	it('handles empty string', () => {
		expect(stripIncompleteDetails('')).toBe('');
	});

	it('handles multiple complete blocks', () => {
		const content =
			'<details type="a">\n<summary>A</summary>\na\n</details>\n' +
			'<details type="b">\n<summary>B</summary>\nb\n</details>\n' +
			'Final text';
		expect(stripIncompleteDetails(content)).toBe(content);
	});
});
