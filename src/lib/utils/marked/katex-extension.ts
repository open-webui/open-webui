import katex from 'katex';

const DELIMITER_LIST = [
	{ left: '$$', right: '$$', display: true },
	{ left: '$', right: '$', display: false },
	{ left: '\\pu{', right: '}', display: false },
	{ left: '\\ce{', right: '}', display: false },
	{ left: '\\(', right: '\\)', display: false },
	{ left: '\\[', right: '\\]', display: true },
	{ left: '\\begin{equation}', right: '\\end{equation}', display: true }
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
	return string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
}

// Define CJK character ranges for Chinese, Japanese and Korean characters and punctuations
// Includes full-width punctuations and symbols commonly used in CJK text
const CJK_CHARS = '\\u2E80-\\u2FFF\\u3000-\\u303F\\u3040-\\u309F\\u30A0-\\u30FF\\u3100-\\u312F\\u3130-\\u318F\\u3190-\\u31FF\\u3200-\\u32FF\\u3300-\\u33FF\\u3400-\\u4DBF\\u4E00-\\u9FFF\\uF900-\\uFAFF\\uFF00-\\uFFEF';

function generateRegexRules(delimiters) {
	delimiters.forEach((delimiter) => {
		const { left, right, display } = delimiter;
		// Ensure regex-safe delimiters
		const escapedLeft = escapeRegex(left);
		const escapedRight = escapeRegex(right);

		if (!display) {
			// For inline delimiters, we match everything
			inlinePatterns.push(`${escapedLeft}((?:\\\\[^]|[^\\\\])+?)${escapedRight}`);
		} else {
			// For block delimiters, allow multi-line content by using dotall flag
			// Instead of restricting with (?!\n), we'll handle multi-line content better
			inlinePatterns.push(`${escapedLeft}((?:\\\\[^]|[^\\\\])+?)${escapedRight}`);
			// Allow any character including newlines between delimiters for block content
			blockPatterns.push(`${escapedLeft}([\\s\\S]+?)${escapedRight}`);
		}
	});

	// Math formulas can end in special characters
	// Added CJK character ranges to support full-width characters in CJK languages
	const inlineRule = new RegExp(
		`^(${inlinePatterns.join('|')})(?=[\\s?。，!-\/:-@[-\`{-~${CJK_CHARS}]|$)`,
		'u'
	);
	const blockRule = new RegExp(`^(${blockPatterns.join('|')})(?=[\\s?。，!-\/:-@[-\`{-~${CJK_CHARS}]|$)`, 'us'); // Added 's' flag for dotall (matching newlines)

	return { inlineRule, blockRule };
}

const { inlineRule, blockRule } = generateRegexRules(DELIMITER_LIST);

export default function (options = {}) {
	return {
		extensions: [inlineKatex(options), blockKatex(options)]
	};
}

function katexStart(src, displayMode: boolean) {
	let ruleReg = displayMode ? blockRule : inlineRule;

	let indexSrc = src;

	while (indexSrc) {
		let index = -1;
		let startIndex = -1;
		let startDelimiter = '';
		let endDelimiter = '';
		for (let delimiter of DELIMITER_LIST) {
			if (delimiter.display !== displayMode) {
				continue;
			}

			startIndex = indexSrc.indexOf(delimiter.left);
			if (startIndex === -1) {
				continue;
			}

			index = startIndex;
			startDelimiter = delimiter.left;
			endDelimiter = delimiter.right;
		}

		if (index === -1) {
			return;
		}

		// Check if the delimiter is preceded by a special character or CJK character
		// Added CJK character range to support LaTeX after full-width characters in CJK languages
		// If it does, then it's potentially a math formula.
		const f = index === 0 || indexSrc.charAt(index - 1).match(new RegExp(`[\\s?。，!-\\/:-@[-\`{-~${CJK_CHARS}]`, 'u'));
		if (f) {
			const possibleKatex = indexSrc.substring(index);

			if (possibleKatex.match(ruleReg)) {
				return index;
			}
		}

		// Improved handling of end delimiter to prevent issues with nested content
		const nextStartPos = index + startDelimiter.length;
		const endDelimPos = indexSrc.indexOf(endDelimiter, nextStartPos);
		
		if (endDelimPos === -1) {
			// If no end delimiter found, skip this potential match
			indexSrc = indexSrc.substring(nextStartPos);
		} else {
			// Skip to after the end delimiter
			indexSrc = indexSrc.substring(endDelimPos + endDelimiter.length);
		}
	}
}

function katexTokenizer(src, tokens, displayMode: boolean) {
	let ruleReg = displayMode ? blockRule : inlineRule;
	let type = displayMode ? 'blockKatex' : 'inlineKatex';

	const match = src.match(ruleReg);

	if (match) {
		const text = match
			.slice(2)
			.filter((item) => item)
			.find((item) => typeof item === 'string');

		return {
			type,
			raw: match[0],
			text: text,
			displayMode
		};
	}
}

function inlineKatex(options) {
	return {
		name: 'inlineKatex',
		level: 'inline',
		start(src) {
			return katexStart(src, false);
		},
		tokenizer(src, tokens) {
			return katexTokenizer(src, tokens, false);
		},
		renderer(token) {
			return `${token?.text ?? ''}`;
		}
	};
}

function blockKatex(options) {
	return {
		name: 'blockKatex',
		level: 'block',
		start(src) {
			return katexStart(src, true);
		},
		tokenizer(src, tokens) {
			return katexTokenizer(src, tokens, true);
		},
		renderer(token) {
			return `${token?.text ?? ''}`;
		}
	};
}
