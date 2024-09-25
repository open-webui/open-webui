import katex from 'katex';

const DELIMITER_LIST = [
	{ left: '$$\n', right: '\n$$', display: true },
	{ left: '$$', right: '$$', display: false },
	{ left: '$', right: '$', display: false },
	{ left: '\\pu{', right: '}', display: false },
	{ left: '\\ce{', right: '}', display: false },
	{ left: '\\(', right: '\\)', display: false },
	// { left: '( ', right: ' )', display: false },
	{ left: '\\[', right: '\\]', display: true },
	// { left: '[ ', right: ' ]', display: true }
];

// const DELIMITER_LIST = [
//     { left: '$$', right: '$$', display: false },
//     { left: '$', right: '$', display: false },
// ];

// const inlineRule = /^(\${1,2})(?!\$)((?:\\.|[^\\\n])*?(?:\\.|[^\\\n\$]))\1(?=[\s?!\.,:？！。，：]|$)/;
// const blockRule = /^(\${1,2})\n((?:\\[^]|[^\\])+?)\n\1(?:\n|$)/;

let inlinePatterns = [];
let blockPatterns = [];

function escapeRegex(string) {
	return string.replace(/[-\/\\^$*+?.()|[\]{}（）]/g, '\\$&');
}

function generateRegexRules(delimiters) {
	delimiters.forEach((delimiter) => {
		const { left, right, display } = delimiter;
		// Ensure regex-safe delimiters
		const escapedLeft = escapeRegex(left);
		const escapedRight = escapeRegex(right);

		if (!display) {
			inlinePatterns.push(`${escapedLeft}((?:\\\\[^]|[^\\\\])+?)${escapedRight}`);
		} else {
			blockPatterns.push(`${escapedLeft}((?:\\\\[^]|[^\\\\])+?)${escapedRight}`);
		}
	});

	const inlineRule = new RegExp(`^(${inlinePatterns.join('|')})(?=[\\s?!.,:？！。，：]|$)`, 'u');
	const blockRule = new RegExp(`^(${blockPatterns.join('|')})(?=[\\s?!.,:？！。，：]|$)`, 'u');

	return { inlineRule, blockRule };
}

const { inlineRule, blockRule } = generateRegexRules(DELIMITER_LIST);

export default function (options = {}) {
	return {
		extensions: [
			blockKatex(options), // This should be on top to prevent conflict with inline delimiters.
			inlineKatex(options)
		]
	};
}

function createRenderer(options, newlineAfter) {
	return (token) =>
		// katex.renderToString(token.text, { ...options, displayMode: token.displayMode }) +
		// (newlineAfter ? '\n' : '');
		katex.renderToString(token.text, { ...options, displayMode: token.displayMode });
}

function inlineKatex(options, renderer) {
	// const ruleReg = inlineRule;
	return {
		name: 'inlineKatex',
		level: 'inline',
		// start(src) {
		// 	let index;
		// 	let indexSrc = src;

		// 	while (indexSrc) {
		// 		index = indexSrc.indexOf('$');
		// 		if (index === -1) {
		// 			return;
		// 		}
		// 		const f = index === 0 || indexSrc.charAt(index - 1) === ' ';
		// 		if (f) {
		// 			const possibleKatex = indexSrc.substring(index);

		// 			if (possibleKatex.match(ruleReg)) {
		// 				return index;
		// 			}
		// 		}

		// 		indexSrc = indexSrc.substring(index + 1).replace(/^\$+/, '');
		// 	}
		// },
		start(src: string) {
			return src.indexOf('$')
		},
		tokenizer(src, tokens) {
			const match = src.match(/^\$+([^$\n]+?)\$+/)

			if (match) {
				return {
					type: 'inlineKatex',
					raw: match[0],
					text: match[1].trim(),
					displayMode: match[0].startsWith('$$')
				}
			}
		},
		renderer
	};
}

function blockKatex(options) {
	return {
		name: 'blockKatex',
		level: 'block',
		tokenizer(src, tokens) {
			const match = src.match(blockRule);

			if (match) {
				const text = match
					.slice(2)
					.filter((item) => item)
					.find((item) => item.trim());

				return {
					type: 'blockKatex',
					raw: match[0],
					text: text,
					displayMode: match[0].startsWith('$$') || match[0].startsWith('\\[')
				};
			}
		},
		tokenizer(src, tokens) {
			return katexTokenizer(src, tokens, true);
		}
	};
}