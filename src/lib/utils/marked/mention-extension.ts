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

function mentionTokenizer(this: any, src: string, options: MentionOptions = {}) {
	const trigger = options.triggerChar ?? '@';
	// Build dynamic regex for `<@id>`, `<@id|label>`, `<@id|>`
	// Added forward slash (/) to the character class for IDs
	const re = new RegExp(`^<\\${trigger}([\\w.\\-:/]+)(?:\\|([^>]*))?>`);
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
	return {
		name: 'mention',
		level: 'inline' as const,
		start: mentionStart,
		tokenizer(src: string) {
			return mentionTokenizer.call(this, src, opts);
		},
		renderer(token: any) {
			return mentionRenderer(token, opts);
		}
	};
}

// Usage:
// import { marked } from 'marked';
// marked.use({ extensions: [mentionExtension({ triggerChar: '@' })] });
