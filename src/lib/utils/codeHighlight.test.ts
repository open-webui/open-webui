import { describe, expect, it } from 'vitest';

import { isCodeEditorFile, isCodeFile } from './codeHighlight';

describe('isCodeEditorFile', () => {
	it('keeps markdown files on the plain-text editor path', () => {
		expect(isCodeFile('/notes/readme.md')).toBe(true);
		expect(isCodeEditorFile('/notes/readme.md')).toBe(false);
		expect(isCodeEditorFile('/notes/guide.markdown')).toBe(false);
		expect(isCodeEditorFile('/notes/component.mdx')).toBe(false);
	});

	it('still treats regular code files as code-editor files', () => {
		expect(isCodeEditorFile('/src/example.ts')).toBe(true);
		expect(isCodeEditorFile('/config/docker-compose.yml')).toBe(true);
	});
});
