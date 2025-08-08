function codeTokenizer(src: string) {
	const match = /^```(\w+)?(.*?)\n([\s\S]*?)(?:\n```|$)/.exec(src);
	if (!match) return;
	const lang = match[1] || null;
	const attrs = match[2].trim().split(/\s+/).filter(Boolean);
	const text = match[3];

	return {
		type: 'code',
		lang,
		attrs,
		raw: match[0],
		text
	};
}

function codeRenderer(token: any) {
	return `<code class="language-${token.lang}">${token.text}</code>`;
}

function codeStart(src: string) {
	return src.match(/^```/) ? 0 : -1;
}

// Extension wrapper function
function codeExtension() {
	return {
		name: 'custom-code',
		level: 'block',
		start: codeStart,
		tokenizer: codeTokenizer,
		renderer: codeRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [codeExtension(options)]
	};
}
