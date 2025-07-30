function ssmlTokenizer(src: string) {
	const match = src.match(/^<speak>([\s\S]*?)<\/speak>/);
	if (!match) return;

	const raw = match[0];
	const content = match[1];

	return {
		type: 'ssml',
		raw,
		text: content
	};
}

function ssmlRenderer(token: any) {
	return `<code class="language-ssml">${token.text}</code>`;
}

function ssmlStart(src: string) {
	return src.match(/^<speak>/) ? 0 : -1;
}

// Extension wrapper function
function ssmlExtension() {
	return {
		name: 'ssml',
		level: 'block',
		start: ssmlStart,
		tokenizer: ssmlTokenizer,
		renderer: ssmlRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [ssmlExtension(options)]
	};
}
