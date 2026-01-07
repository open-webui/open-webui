const DELIMITER_LIST = [
	{ left: '$$', right: '$$', display: true },
	{ left: '$', right: '$', display: false },
	{ left: '\\pu{', right: '}', display: false },
	{ left: '\\ce{', right: '}', display: false },
	{ left: '\\(', right: '\\)', display: false },
	{ left: '\\[', right: '\\]', display: true },
	{ left: '\\begin{equation}', right: '\\end{equation}', display: true }
];

// Defines characters that are allowed to immediately precede or follow a math delimiter.
// Added * and # for list items and headers, () for parentheses
const ALLOWED_SURROUNDING_CHARS =
	'\\s,\\.。，、､;；„"\'\'""()（）「」『』［］《》【】‹›«»…⋯:：？！～⇒?!*#>+\\-\\/:-@\\[-`{-~\\p{Script=Han}\\p{Script=Hiragana}\\p{Script=Katakana}\\p{Script=Hangul}';
// Modified to fit more formats in different languages. Originally: '\\s?。，、；!-\\/:-@\\[-`{-~\\p{Script=Han}\\p{Script=Hiragana}\\p{Script=Katakana}\\p{Script=Hangul}';

// const DELIMITER_LIST = [
//     { left: '$$', right: '$$', display: false },
//     { left: '$', right: '$', display: false },
// ];

// const inlineRule = /^(\${1,2})(?!\$)((?:\\.|[^\\\n])*?(?:\\.|[^\\\n\$]))\1(?=[\s?!\.,:？！。，：]|$)/;
// const blockRule = /^(\${1,2})\n((?:\\[^]|[^\\])+?)\n\1(?:\n|$)/;

const inlinePatterns = [];
const blockPatterns = [];

// Newline pattern supporting both LF and CRLF
const NL = '(?:\\r?\\n)';

function escapeRegex(string) {
	return string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
}

// Check if content looks like actual math formula vs plain text
// Returns true if it looks like math, false if it's just plain text
function looksLikeMath(content: string): boolean {
	// If empty or whitespace only, not math
	if (!content || !content.trim()) {
		return false;
	}

	// LaTeX commands (backslash followed by letters)
	const hasLatexCommand = /\\[a-zA-Z]+/.test(content);
	if (hasLatexCommand) {
		return true;
	}

	// Math operators and symbols
	const hasMathSymbols = /[=+\-*/^_{}\\|<>≤≥≠±×÷∑∏∫∂∇√∞∈∉⊂⊃∪∩∧∨¬→←↔⇒⇐⇔αβγδεζηθικλμνξπρστυφχψωΓΔΘΛΞΠΣΦΨΩ]/.test(content);
	if (hasMathSymbols) {
		return true;
	}

	// Fractions, subscripts, superscripts patterns
	const hasMathPatterns = /\d+\/\d+|[a-zA-Z]\d|[a-zA-Z]_|[a-zA-Z]\^/.test(content);
	if (hasMathPatterns) {
		return true;
	}

	// If content is primarily CJK characters (Korean, Chinese, Japanese) without math symbols, it's not math
	// Count CJK characters vs other characters
	const cjkPattern = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}]/gu;
	const cjkMatches = content.match(cjkPattern);
	const cjkCount = cjkMatches ? cjkMatches.length : 0;

	// If more than 50% of non-whitespace characters are CJK, it's probably not math
	const nonWhitespace = content.replace(/\s/g, '');
	if (nonWhitespace.length > 0 && cjkCount / nonWhitespace.length > 0.5) {
		return false;
	}

	// If it contains at least some numbers or latin letters, could be math
	const hasNumbersOrLatinLetters = /[a-zA-Z0-9]/.test(content);
	if (hasNumbersOrLatinLetters) {
		return true;
	}

	// Default: if only CJK and punctuation, not math
	return false;
}

function generateRegexRules(delimiters) {
	delimiters.forEach((delimiter) => {
		const { left, right, display } = delimiter;
		// Ensure regex-safe delimiters
		const escapedLeft = escapeRegex(left);
		const escapedRight = escapeRegex(right);

		if (!display) {
			// For single $ delimiter, ensure it's not part of $$
			if (left === '$') {
				// Single $ must not be followed by another $ (to avoid matching $$)
				// And closing $ must not be followed by another $
				// Content must not contain $$ (to prevent matching across $$ blocks)
				inlinePatterns.push(`\\$(?!\\$)((?:\\\\[^]|[^\\\\\\$]|\\$(?!\\$))+?)\\$(?!\\$)`);
			} else {
				// For other inline delimiters, we match everything
				inlinePatterns.push(`${escapedLeft}((?:\\\\[^]|[^\\\\])+?)${escapedRight}`);
			}
		} else {
			// Special handling for $$ delimiter
			if (left === '$$') {
				// Block pattern: $$ followed by newline, content, newline, $$ (supports CRLF)
				blockPatterns.push(`\\$\\$\\s*${NL}([\\s\\S]+?)${NL}\\s*\\$\\$`);
				// Single-line display pattern: $$ content $$ (no newlines in content)
				blockPatterns.push(`\\$\\$\\s*([^\\r\\n]+?)\\s*\\$\\$`);
			} else {
				// Other block delimiters: with newline (supports CRLF)
				blockPatterns.push(`${escapedLeft}\\s*${NL}([\\s\\S]+?)${NL}\\s*${escapedRight}`);
				// Single-line variant for other display delimiters
				blockPatterns.push(`${escapedLeft}\\s*([^\\r\\n]+?)\\s*${escapedRight}`);
			}
		}
	});

	// Math formulas can end in special characters
	const inlineRule = new RegExp(
		`^(${inlinePatterns.join('|')})(?=[${ALLOWED_SURROUNDING_CHARS}]|$)`,
		'u'
	);
	const blockRule = new RegExp(
		`^(${blockPatterns.join('|')})(?=[${ALLOWED_SURROUNDING_CHARS}]|$)`,
		'u'
	);

	return { inlineRule, blockRule };
}

const { inlineRule, blockRule } = generateRegexRules(DELIMITER_LIST);

export default function (options = {}) {
	return {
		extensions: [inlineKatex(options), blockKatex(options)]
	};
}

function katexStart(src, displayMode: boolean) {
	const ruleReg = displayMode ? blockRule : inlineRule;

	let indexSrc = src;
	let offset = 0;

	while (indexSrc) {
		let minIndex = -1;
		let startDelimiter = '';
		let endDelimiter = '';

		// Find the EARLIEST occurrence of any matching delimiter
		for (const delimiter of DELIMITER_LIST) {
			// For block mode, only check display:true delimiters
			// For inline mode, check ALL delimiters (since inlinePatterns includes both)
			if (displayMode && !delimiter.display) {
				continue;
			}

			let startIndex = indexSrc.indexOf(delimiter.left);
			if (startIndex === -1) {
				continue;
			}

			// For single $, skip if it's part of $$ (check previous char in original src)
			if (delimiter.left === '$' && !displayMode) {
				const absolutePos = offset + startIndex;
				// Check if this $ is preceded by another $ (making it part of $$)
				if (absolutePos > 0 && src.charAt(absolutePos - 1) === '$') {
					// This $ is the second char of $$, skip it
					// Try to find next $
					const nextIndex = indexSrc.indexOf('$', startIndex + 1);
					if (nextIndex === -1) {
						continue;
					}
					startIndex = nextIndex;
					// Check again if this new $ is preceded by $
					const newAbsolutePos = offset + startIndex;
					if (newAbsolutePos > 0 && src.charAt(newAbsolutePos - 1) === '$') {
						continue;
					}
				}
				// Also check if this $ is followed by another $ (first char of $$)
				if (startIndex + 1 < indexSrc.length && indexSrc.charAt(startIndex + 1) === '$') {
					// This is the first char of $$, skip single $ matching
					continue;
				}
			}

			// Keep track of the earliest (minimum) index
			if (minIndex === -1 || startIndex < minIndex) {
				minIndex = startIndex;
				startDelimiter = delimiter.left;
				endDelimiter = delimiter.right;
			}
		}

		if (minIndex === -1) {
			return;
		}

		// Check if the delimiter is preceded by a special character.
		// If it does, then it's potentially a math formula.
		const f =
			minIndex === 0 ||
			indexSrc.charAt(minIndex - 1).match(new RegExp(`[${ALLOWED_SURROUNDING_CHARS}]`, 'u'));
		if (f) {
			const possibleKatex = indexSrc.substring(minIndex);

			if (possibleKatex.match(ruleReg)) {
				return offset + minIndex;
			}
		}

		offset += minIndex + startDelimiter.length;
		indexSrc = indexSrc.substring(minIndex + startDelimiter.length).replace(endDelimiter, '');
	}
}

function katexTokenizer(src, tokens, displayMode: boolean) {
	const ruleReg = displayMode ? blockRule : inlineRule;
	const type = displayMode ? 'blockKatex' : 'inlineKatex';

	const match = src.match(ruleReg);

	if (match) {
		// Extract the formula content from capture groups
		// Skip match[0] (full match) and match[1] (outer wrapper group)
		// Find the first non-empty capture group which contains the formula
		const text = match
			.slice(2)
			.filter((item) => item !== undefined && item !== null)
			.find((item) => item.trim().length > 0);

		if (text) {
			// Validate that the content looks like actual math, not plain text
			if (!looksLikeMath(text)) {
				return;
			}

			return {
				type,
				raw: match[0],
				text: text.trim(),
				displayMode
			};
		}
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
