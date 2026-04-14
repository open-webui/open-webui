// mention-extension.ts
type MentionOptions = {
	triggerChar?: string; // default "@"
	className?: string; // default "mention"
	extraAttrs?: Record<string, string>; // additional HTML attrs
};

function escapeHtml(s: string) {
	return s.replace(
		/[&<>"']/g,
		(c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!
	);
}

function mentionStart(src: string) {
	// Find the first "<" followed by trigger char
	// We'll refine inside tokenizer
	return src.indexOf('<');
}

function mentionRenderer(token: any, options: MentionOptions = {}) {
	const trigger = options.triggerChar ?? '@';
	const cls = options.className ?? 'mention';
	const extra = options.extraAttrs ?? {};

	const attrs = Object.entries({
		class: cls,
		'data-type': 'mention',
		'data-id': token.id,
		'data-mention-suggestion-char': trigger,
		...extra
	})
		.map(([k, v]) => `${k}="${escapeHtml(String(v))}"`)
		.join(' ');

	return `<span ${attrs}>${escapeHtml(trigger + token.label)}</span>`;
}

export function mentionExtension(opts: MentionOptions = {}) {
	// Compile the regex once when the extension is created, not on every tokenizer call.
	// mentionStart fires on every '<' in the document, making the tokenizer a hot path.
	const trigger = opts.triggerChar ?? '@';
	const re = new RegExp(`^<\\${trigger}([\\w.\\-:/]+)(?:\\|([^>]*))?>`);
	const snapshot: MentionOptions = {
		triggerChar: trigger,
		className: opts.className,
		extraAttrs: opts.extraAttrs
	};

	return {
		name: 'mention',
		level: 'inline' as const,
		start: mentionStart,
		tokenizer(src: string) {
			const m = re.exec(src);
			if (!m) return;
			const [, id, label] = m;
			return {
				type: 'mention',
				raw: m[0],
				triggerChar: trigger,
				id,
				label: label && label.length > 0 ? label : id
			};
		},
		renderer(token: any) {
			return mentionRenderer(token, snapshot);
		}
	};
}

// Usage:
// import { marked } from 'marked';
// marked.use({ extensions: [mentionExtension({ triggerChar: '@' })] });
