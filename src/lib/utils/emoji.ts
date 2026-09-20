/**
 * Convert an emoji Unicode codepoint sequence into the emoji character.
 *
 * `emoji-shortcodes.json` is keyed by the emoji's code point sequence. For
 * multi-code-point emoji that sequence is hyphen separated (`1F44B` for 👋,
 * `0023-FE0F-20E3` for #️⃣, `1F1E6-1F1E8` for 🇦🇨), so every part has to be
 * converted separately. Handing the whole string to `parseInt` keeps only the
 * leading code point and silently yields the wrong character, for example a
 * plain `#` instead of #️⃣.
 *
 * Parts are validated as whole hex values first, because `parseInt` also accepts
 * a valid prefix of a longer string (`parseInt('codepoint', 16)` is `12`).
 */
export const unicodeToEmoji = (unicode: string): string =>
	(unicode ?? '')
		.split('-')
		.filter((codePoint) => /^[0-9a-f]{1,6}$/i.test(codePoint))
		.map((codePoint) => parseInt(codePoint, 16))
		.filter((codePoint) => codePoint <= 0x10ffff)
		.map((codePoint) => String.fromCodePoint(codePoint))
		.join('');
