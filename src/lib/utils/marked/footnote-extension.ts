// footnote-extension.ts
// Simple extension for marked to support footnote references like [^1], [^note]

function escapeHtml(s: string) {
	return s.replace(
		/[&<>"']/g,
		(c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!
	);
}

export function footnoteExtension() {
	return {
		name: 'footnoteRef',
		level: 'inline' as const,
		start(src: string) {
			return src.search(/\[\^\s*[a-zA-Z0-9_-]+\s*\]/);
		},
		tokenizer(src: string) {
			const rule = /^\[\^\s*([a-zA-Z0-9_-]+)\s*\]/;
			const match = rule.exec(src);
			if (match) {
				const escapedText = escapeHtml(match[1]);
				const html = `<sup class="footnote-ref footnote-ref-text">${escapedText}</sup>`;				
				return {
					type: 'footnoteRef',
					raw: match[0],
					text: match[1],
					html: html
				};
			}
		},
		renderer(token: { type: string; raw: string; text: string; html: string }) {
			return token.html;
		}
	};
}

export default function () {
	return {
		extensions: [footnoteExtension()]
	};
}
