import { describe, expect, it, vi } from 'vitest';

import { getEditorPlainText } from './plainText';

describe('getEditorPlainText', () => {
	it('reads plain text directly from the editor document', () => {
		const text = 'OS: Ubuntu Linux\n\nShell: zsh\n\nPlease write a command line cheat sheet.';
		const textBetween = vi.fn(() => text);
		const editor = {
			state: {
				doc: {
					content: {
						size: 42
					},
					textBetween
				}
			}
		};

		expect(getEditorPlainText(editor)).toBe(text);
		expect(textBetween).toHaveBeenCalledWith(0, 42, '\n');
		expect(getEditorPlainText(editor)).not.toContain('  \n');
	});
});
