export function citationExtension() {
	return {
		name: 'citation',
		level: 'inline' as const,

		start(src: string) {
			// Trigger on any [number]
			return src.search(/\[(\d[\d,\s]*)\]/);
		},

		tokenizer(src: string) {
			// Avoid matching footnotes
			if (/^\[\^/.test(src)) return;

			// Match ONE OR MORE adjacent [1] or [1,2] blocks
			// Example matched: "[1][2,3][4]"
			const rule = /^(\[(?:\d[\d,\s]*)\])+/;
			const match = rule.exec(src);
			if (!match) return;

			const raw = match[0];

			// Extract ALL bracket groups inside the big match
			const groupRegex = /\[([\d,\s]+)\]/g;
			const ids: number[] = [];
			let m: RegExpExecArray | null;

			while ((m = groupRegex.exec(raw))) {
				const parsed = m[1]
					.split(',')
					.map((n) => parseInt(n.trim(), 10))
					.filter((n) => !isNaN(n));

				ids.push(...parsed);
			}

			return {
				type: 'citation',
				raw,
				ids // merged list
			};
		},

		renderer(token: any) {
			// e.g. "1,2,3"
			return token.ids.join(',');
		}
	};
}

export default function () {
	return {
		extensions: [citationExtension()]
	};
}
