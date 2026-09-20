import { describe, expect, it } from 'vitest';

import emojiShortCodes from '../emoji-shortcodes.json';
import { unicodeToEmoji } from './emoji';

describe('unicodeToEmoji', () => {
	it('converts an emoji made of a single code point', () => {
		expect(unicodeToEmoji('1F44B')).toBe('👋');
		expect(unicodeToEmoji('1F525')).toBe('🔥');
	});

	it('converts every code point of a multi-code-point emoji', () => {
		// keycap sequences used to lose everything after the leading code point
		expect(unicodeToEmoji('0023-FE0F-20E3')).toBe('#️⃣');
		expect(unicodeToEmoji('0031-FE0F-20E3')).toBe('1️⃣');
		// regional indicator pair (flag)
		expect(unicodeToEmoji('1F1E6-1F1E8')).toBe('🇦🇨');
		// zero width joiner sequence
		expect(unicodeToEmoji('2764-FE0F-200D-1F525')).toBe('❤️‍🔥');
	});

	it('accepts lowercase hex', () => {
		expect(unicodeToEmoji('1f44b')).toBe('👋');
		expect(unicodeToEmoji('0023-fe0f-20e3')).toBe('#️⃣');
	});

	it('returns an empty string for empty or malformed input', () => {
		expect(unicodeToEmoji('')).toBe('');
		expect(unicodeToEmoji(undefined as unknown as string)).toBe('');
		// `parseInt` would read this as a hex prefix, the whole part has to be valid
		expect(unicodeToEmoji('zz-zz')).toBe('');
		expect(unicodeToEmoji('codepoint')).toBe('');
	});

	it('keeps one code point per part for every shortcode in the emoji table', () => {
		const codepointSequences = Object.keys(emojiShortCodes);

		expect(codepointSequences.length).toBeGreaterThan(0);

		for (const codepointSequence of codepointSequences) {
			const expected = codepointSequence.split('-').length;
			expect(Array.from(unicodeToEmoji(codepointSequence))).toHaveLength(expected);
		}
	});
});
