export function citationExtension() {
	return {
		name: 'citation',
		level: 'inline' as const,

		start(src: string) {
			// Trigger on any `[`; we filter precisely in the tokenizer.
			// The tokenizer rejects markdown links (`[text](url)`) and
			// footnotes (`[^foo]`).
			return src.search(/\[/);
		},

		tokenizer(src: string) {
			// Avoid matching footnotes
			if (/^\[\^/.test(src)) return;

			// 1) Numeric path: ONE OR MORE adjacent [1], [1,2], [1#foo] blocks.
			// Backward-compatible with existing chat history that has [N] tokens.
			const numericRule = /^(\[(?:\d+(?:#[^,\]\s]+)?(?:,\s*\d+(?:#[^,\]\s]+)?)*)\])+/;
			const numericMatch = numericRule.exec(src);
			if (numericMatch) {
				const raw = numericMatch[0];
				const groupRegex = /\[([^\]]+)\]/g;
				const ids: number[] = [];
				const citationIdentifiers: string[] = [];
				let m: RegExpExecArray | null;
				while ((m = groupRegex.exec(raw))) {
					const parts = m[1].split(',').map((p) => p.trim());
					parts.forEach((part) => {
						const inner = /^(\d+)(?:#(.+))?$/.exec(part);
						if (inner) {
							const index = parseInt(inner[1], 10);
							if (!isNaN(index)) {
								ids.push(index);
								citationIdentifiers.push(part);
							}
						}
					});
				}
				if (ids.length === 0) return;
				return {
					type: 'citation',
					raw,
					ids,
					citationIdentifiers
				};
			}

			// 2) Name path: a single [non-empty content] bracket whose content
			// is not purely-numeric (handled above), contains no `]` or `(`,
			// and is not followed by `(` (which would make it a markdown link).
			// Examples matched: [contract.pdf], [wikipedia.org], [Wikipedia: Python]
			// NOT matched: [text](url), [^foo], [1], [1, 2]
			const nameRule = /^\[([^\[\]()\n]+?)\](?!\()/;
			const nameMatch = nameRule.exec(src);
			if (!nameMatch) return;
			const content = nameMatch[1].trim();
			if (!content) return;
			if (/^\d+(?:\s*,\s*\d+)*$/.test(content)) return;
			return {
				type: 'citation',
				raw: nameMatch[0],
				ids: [], // no numeric id; lookup is by name
				citationIdentifiers: [content]
			};
		},

		renderer(token: any) {
			// fallback text
			return token.raw;
		}
	};
}

export default function () {
	return {
		extensions: [citationExtension()]
	};
}
