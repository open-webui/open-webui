import katex from 'katex';

export default function (options = {}) {
	return {
		extensions: [
			inlineKatex(options, createRenderer(options)),
		]
	};
}

function createRenderer(options) {
	return (token) =>
		katex.renderToString(token.text, { ...options, displayMode: token.displayMode });
}

function inlineKatex(options, renderer) {
	return {
		name: 'inlineKatex',
		level: 'inline',
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