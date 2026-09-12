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
				// return a plain-text token, NOT del
				return {
					type: 'text',
					raw: singleMatch[0],
					text: singleMatch[0] // include both tildes as literal text
				};
			}

			return false;
		}
	}
};
