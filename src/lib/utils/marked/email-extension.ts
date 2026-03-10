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

function emailStart(src: string) {
	return src.match(/^<email>/) ? 0 : -1;
}

function emailTokenizer(src: string) {
	const openRegex = /^<email>\n?/;
	const openMatch = openRegex.exec(src);
	if (!openMatch) return;

	const endIndex = findMatchingClosingTag(src, '<email>', '</email>');
	const closed = endIndex !== -1;

	// If closed, use the matched range. If still streaming, consume all remaining input.
	const fullMatch = closed ? src.slice(0, endIndex) : src;
	let content = closed
		? fullMatch.slice(openMatch[0].length, -'</email>'.length)
		: fullMatch.slice(openMatch[0].length);

	let subject = '';
	const subjectMatch = /^<subject>([\s\S]*?)<\/subject>\n?/.exec(content);
	if (subjectMatch) {
		subject = subjectMatch[1].trim();
		content = content.slice(subjectMatch[0].length);
	}

	let to = '';
	const toMatch = /^<to>([\s\S]*?)<\/to>\n?/.exec(content);
	if (toMatch) {
		to = toMatch[1].trim();
		content = content.slice(toMatch[0].length);
	}

	const body = content.replace(/^\n+/, '').replace(/\n+$/, '');

	return {
		type: 'email',
		raw: fullMatch,
		subject,
		to,
		body
	};
}

function emailRenderer(token: any) {
	return token.raw;
}

function emailExtension() {
	return {
		name: 'email',
		level: 'block' as const,
		start: emailStart,
		tokenizer: emailTokenizer,
		renderer: emailRenderer
	};
}

export default function (options = {}) {
	return {
		extensions: [emailExtension()]
	};
}
