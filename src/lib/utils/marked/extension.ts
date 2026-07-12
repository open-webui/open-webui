import type {
	MarkedExtension,
	TokenizerAndRendererExtension,
	TokenizerExtension,
	TokenizerThis,
	Tokens
} from 'marked';

// Helper function to find matching closing tag
function findMatchingClosingTag(src: string, openTag: string, closeTag: string): number {
	let depth = 1;
	let index = openTag.length;
	while (depth > 0 && index < src.length) {
		if (src.startsWith(openTag, index)) {
			depth++;
		} else if (src.startsWith(closeTag, index)) {
			depth--;
		}
		if (depth > 0) {
			index++;
		}
	}
	return depth === 0 ? index + closeTag.length : -1;
}

// Function to parse attributes from tag
function parseAttributes(tag: string): { [key: string]: string } {
	const attributes: { [key: string]: string } = {};
	const attrRegex = /(\w+)="(.*?)"/g;
	let match;
	while ((match = attrRegex.exec(tag)) !== null) {
		attributes[match[1]] = match[2];
	}
	return attributes;
}

type DetailsToken = Tokens.Generic & {
	attributes?: Record<string, string>;
	summary?: string;
	text: string;
};

function paragraphBeforeDetailsTokenizer(
	this: TokenizerThis,
	src: string
): Tokens.Generic | undefined {
	const boundary = /\r?\n(?=<details(?:\s+[^>]*)?>\r?\n)/.exec(src);
	if (!boundary) return;

	const raw = src.slice(0, boundary.index + boundary[0].length);
	const tokens = this.lexer.blockTokens(raw, []);

	if (tokens.length !== 1 || tokens[0].type !== 'paragraph') return;

	return tokens[0] as Tokens.Generic;
}

function paragraphBeforeDetailsExtension(): TokenizerExtension {
	return {
		name: 'paragraphBeforeDetails',
		level: 'block',
		tokenizer: paragraphBeforeDetailsTokenizer
	};
}

function detailsTokenizer(src: string) {
	// Updated regex to capture attributes inside <details>
	const detailsRegex = /^<details(\s+[^>]*)?>\r?\n/;
	const summaryRegex = /^<summary>(.*?)<\/summary>\r?\n/;

	const detailsMatch = detailsRegex.exec(src);
	if (detailsMatch) {
		const endIndex = findMatchingClosingTag(src, '<details', '</details>');
		if (endIndex === -1) return;

		const fullMatch = src.slice(0, endIndex);
		const detailsTag = detailsMatch[0];
		const attributes = parseAttributes(detailsTag); // Parse attributes from <details>

		let content = fullMatch.slice(detailsTag.length, -10).trim(); // Remove <details> and </details>
		let summary = '';

		const summaryMatch = summaryRegex.exec(content);
		if (summaryMatch) {
			summary = summaryMatch[1].trim();
			content = content.slice(summaryMatch[0].length).trim();
		}

		return {
			type: 'details',
			raw: fullMatch,
			summary: summary,
			text: content,
			attributes: attributes // Include extracted attributes from <details>
		};
	}
}

function detailsRenderer(genericToken: Tokens.Generic) {
	const token = genericToken as DetailsToken;
	const attributesString = token.attributes
		? Object.entries(token.attributes)
				.map(([key, value]) => `${key}="${value}"`)
				.join(' ')
		: '';

	return `<details ${attributesString}>
  ${token.summary ? `<summary>${token.summary}</summary>` : ''}
  ${token.text}
  </details>`;
}

// Extension wrapper function
function detailsExtension(): TokenizerAndRendererExtension {
	return {
		name: 'details',
		level: 'block',
		tokenizer: detailsTokenizer,
		renderer: detailsRenderer
	};
}

export default function (): MarkedExtension {
	return {
		extensions: [paragraphBeforeDetailsExtension(), detailsExtension()]
	};
}
