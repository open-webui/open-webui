import katex from 'katex'
import 'katex/dist/katex.css'

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
	return {
		name: 'inlineKatex',
		level: 'inline',
		start(src: string) {
			let index;
			let indexSrc = src;

			while (indexSrc) {
				index = indexSrc.indexOf('$');
				if (index === -1) {
					return;
				}
				const f = nonStandard ? index > -1 : index === 0 || indexSrc.charAt(index - 1) === ' ';
				if (f) {
					const possibleKatex = indexSrc.substring(index);

					if (possibleKatex.match(ruleReg)) {
						return index;
					}
				}

				indexSrc = indexSrc.substring(index + 1).replace(/^\$+/, '');
			}
		},
		tokenizer(src: string) {
			const match = src.match(/^(\${1,2})(?!\$)((?:\\.|[^\\\n])*?(?:\\.|[^\\\n\$]))\1(?=[\s?!\.,:？！。，：]|$)/)
			if (match) {
				return {
					type: 'inlineKatex',
					raw: match[0],
					text: match[2].trim(),
					displayMode: match[1].length === 2,
				}
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
