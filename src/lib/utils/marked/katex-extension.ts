import { marked } from 'marked';

const blockRules = {
	doubleDollar: /^\$\$([\s\S]+?)\$\$/,
	bracket: /^\\\[([\s\S]+?)\\\]/,
	environment: /^\\begin\{([a-zA-Z0-9\*]+)\}([\s\S]+?)\\end\{\1\}/
};

const inlineRules = {
	singleDollar: /^\$([^$\n]+?)\$/,
	paren: /^\\\(([\s\S]+?)\\\)/
};

function blockKatex(options) {
	return {
		name: 'blockKatex',
		level: 'block',
		start(src) {
			return src.match(/\$\$|\\\[|\\begin\{/)?.index;
		},
		tokenizer(src, tokens) {
			let match = blockRules.doubleDollar.exec(src);
			if (match) {
				return {
					type: 'blockKatex',
					raw: match[0],
					text: match[1].trim(),
					displayMode: true
				};
			}

			match = blockRules.bracket.exec(src);
			if (match) {
				return {
					type: 'blockKatex',
					raw: match[0],
					text: match[1].trim(),
					displayMode: true
				};
			}

			match = blockRules.environment.exec(src);
			if (match) {
				return {
					type: 'blockKatex',
					raw: match[0],
					text: match[0],
					displayMode: true
				};
			}
		},
		renderer(token) {
			return token.text;
		}
	};
}

function inlineKatex(options) {
	return {
		name: 'inlineKatex',
		level: 'inline',
		start(src) {
			return src.match(/[$(\\]/)?.index;
		},
		tokenizer(src, tokens) {
			let match = blockRules.doubleDollar.exec(src);
			if (match) {
				return {
					type: 'blockKatex',
					raw: match[0],
					text: match[1].trim(),
					displayMode: true
				};
			}

			match = blockRules.bracket.exec(src);
			if (match) {
				return {
					type: 'blockKatex',
					raw: match[0],
					text: match[1].trim(),
					displayMode: true
				};
			}

			match = blockRules.environment.exec(src);
			if (match) {
				return {
					type: 'blockKatex',
					raw: match[0],
					text: match[0],
					displayMode: true
				};
			}

			match = inlineRules.singleDollar.exec(src);
			if (match) {
				const content = match[1];
				// Basic currency check: if it looks like a number or currency amount, ignore it.
				// e.g. $10, $10.50, $1,000
				if (/^\s*\d+(?:[.,]\d+)*\s*$/.test(content)) {
					return;
				}
				
				return {
					type: 'inlineKatex',
					raw: match[0],
					text: content.trim(),
					displayMode: false
				};
			}

			match = inlineRules.paren.exec(src);
			if (match) {
				return {
					type: 'inlineKatex',
					raw: match[0],
					text: match[1].trim(),
					displayMode: false
				};
			}
		},
		renderer(token) {
			return token.text;
		}
	};
}

export default function (options = {}) {
	return {
		extensions: [blockKatex(options), inlineKatex(options)]
	};
}
