/**
 * Marked extension for colon-fence blocks (:::type{key="value"} ... :::)
 *
 * Used by newer OpenAI chat models to wrap semantically distinct content:
 *   :::writing    – reusable prose (letters, articles, docs)
 *   :::code_execution – code execution output
 *   :::search_results  – web search results
 *
 * The extension is generic and will tokenize any :::<identifier> block.
 */

function parseAttributes(attributeList: string): Record<string, string> {
	const attributes: Record<string, string> = {};
	for (const [, key, value] of attributeList.matchAll(/([\w-]+)="([^"]*)"/g)) {
		attributes[key] = value;
	}
	return attributes;
}

function colonFenceTokenizer(this: any, src: string) {
	// Match :::type at the start of a line, optionally followed by content, then closing :::
	const match = /^:::([\w-]+)(?:\{([^\n]*)\})?[^\n]*\n([\s\S]*?)(?:\n:::(?:\s*(?:\n|$)))/.exec(src);
	if (match) {
		const fenceType = match[1];
		const attributes = parseAttributes(match[2] ?? '');
		const text = match[3].trim();
		const raw = match[0];

		const tokens: any[] = [];
		this.lexer.blockTokens(text, tokens);

		return {
			type: 'colonFence',
			raw,
			fenceType,
			attributes,
			text,
			tokens
		};
	}
}

function colonFenceStart(src: string) {
	const idx = src.match(/^:::\w/m);
	return idx ? idx.index! : -1;
}

function colonFenceRenderer(token: any) {
	return `<div class="colon-fence colon-fence-${token.fenceType}">${token.text}</div>`;
}

function colonFenceExtension() {
	return {
		name: 'colonFence',
		level: 'block' as const,
		start: colonFenceStart,
		tokenizer: colonFenceTokenizer,
		renderer: colonFenceRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [colonFenceExtension()]
	};
}
