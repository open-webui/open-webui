import type { MarkedExtension, Tokens } from 'marked';

/**
 * Replaces the default `del` tokenizer so that only ~~text~~ is strikethrough.
 * Single tilde ~text~ is not matched as del (returns false), so it is rendered as plain text.
 */
export function disableSingleTildeExtension() {
	const extension: MarkedExtension = {
		tokenizer: {
			del(this: { lexer: { inlineTokens: (src: string) => Tokens.Generic[] } }, src: string) {
				// 1. Real strikethrough: ~~text~~
				const doubleMatch = /^~~(?=\S)([\s\S]*?\S)~~/.exec(src);
				if (doubleMatch) {
					return {
						type: 'del',
						raw: doubleMatch[0],
						text: doubleMatch[1],
						tokens: this.lexer.inlineTokens(doubleMatch[1])
					};
				}

				// 2. Single tilde ~text~: do not match as del, so it stays plain text
				const singleMatch = /^~(?=\S)([\s\S]*?\S)~/.exec(src);
				if (singleMatch) {
					return false;
				}

				return false;
			}
		}
	};

	return extension;
}
