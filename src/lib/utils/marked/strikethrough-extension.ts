export const disableSingleTilde = {
	tokenizer: {
		del(src) {
			// 1. First check for the REAL strikethrough: ~~text~~
			const doubleMatch = /^~~(?=\S)([\s\S]*?\S)~~/.exec(src);
			if (doubleMatch) {
				return {
					type: 'del',
					raw: doubleMatch[0],
					text: doubleMatch[1],
					tokens: this.lexer.inlineTokens(doubleMatch[1])
				};
			}

			// 2. Check for single-tilde: ~text~
			const singleMatch = /^~(?=\S)([\s\S]*?\S)~/.exec(src);
			if (singleMatch) {
				// the rest of the span re-lexes as normal inline markdown
				return {
					type: 'text',
					raw: '~',
					text: '~'
				};
			}

			return false;
		}
	}
};
