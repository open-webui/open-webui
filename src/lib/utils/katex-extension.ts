import katex from 'katex'
import 'katex/dist/katex.css'

const inlineRule = /^(\${1,2})(?!\$)((?:\\.|[^\\\n])*?(?:\\.|[^\\\n\$]))\1(?=[\s?!\.,:？！。，：]|$)/;
const inlineRuleNonStandard = /^(\${1,2})(?!\$)((?:\\.|[^\\\n])*?(?:\\.|[^\\\n\$]))\1/; // Non-standard, even if there are no spaces before and after $ or $$, try to parse

export default function (options = {}) {
	return {
		extensions: [
			inlineKatex(options, createRenderer(options, false)),
			blockKatex(options, createRenderer(options, true)),
		],
	};
}

function createRenderer(options, newlineAfter) {
	return (token) => katex.renderToString(token.text, { ...options, displayMode: token.displayMode }) + (newlineAfter ? '\n' : '');
}

function inlineKatex(options, renderer) {
	const nonStandard = options && options.nonStandard;
	const ruleReg = nonStandard ? inlineRuleNonStandard : inlineRule;
	return {
		name: 'inlineKatex',
		level: 'inline',
		start(src: string) {
			return src.indexOf('$')
		},
		tokenizer(src, tokens) {
			const match = src.match(ruleReg);
			if (match) {
				return {
					type: 'inlineKatex',
					raw: match[0],
					text: match[2].trim(),
					displayMode: match[1].length === 2,
				};
			}
		},
		renderer,
	};
}


function blockKatex(options, renderer) {
	return {
		name: 'blockKatex',
		level: 'block',
		start(src: string) {
			return src.indexOf('$$')
		},
		tokenizer(src: string) {
			const match = src.match(/^\$\$+\n([^$]+?)\n\$\$/)
			if (match) {
				return {
					type: 'blockKatex',
					raw: match[0],
					text: match[1].trim(),
					displayMode: match[0].startsWith('$$')
				}
			}
		},
		renderer,
	};
}
