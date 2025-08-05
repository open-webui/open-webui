function codeTokenizer(src: string) {
	const match = src.match(/^```([^\n]*)\n([\s\S]*?)\n```/);
	if (!match) return;

	const raw = match[0];
	const info = match[1];
	const text = match[2];

	const [lang, ...attrs] = info.trim().split(/\s+/);

	return {
		type: 'code',
		raw,
		lang,
		attrs,
		text
	};
}

function codeRenderer(token: any) {
	const { lang } = token;
	return `<code class="language-${lang}">${token.text}</code>`;
}

function codeStart(src: string) {
	return src.match(/^```/) ? 0 : -1;
}

// Extension wrapper function
function codeExtension() {
	return {
		name: 'code-block',
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
