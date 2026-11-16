// Buffer incomplete markup rather than asking the browser to repair partial attributes or CSS.
export function findSafeCut(source: string): number {
	let cursor = 0,
		safe = 0;
	while (cursor < source.length) {
		if (source[cursor] === '&') {
			const tail = source.slice(cursor);
			if (/^&(?:#[xX]?[\da-f]*|[a-z\d]*)$/i.test(tail)) break;
		}
		if (source[cursor] !== '<') {
			safe = ++cursor;
			continue;
		}
		if (source.startsWith('<!--', cursor) || source.startsWith('<![CDATA[', cursor)) {
			const cdata = source.startsWith('<![CDATA[', cursor);
			const end = source.indexOf(cdata ? ']]>' : '-->', cursor + (cdata ? 9 : 4));
			if (end < 0) break;
			cursor = safe = end + 3;
			continue;
		}
		let end = cursor + 1,
			quote = '';
		for (; end < source.length; end++) {
			const c = source[end];
			if (quote) {
				if (c === quote) quote = '';
			} else if (c === '"' || c === "'") quote = c;
			else if (c === '>') break;
		}
		if (end === source.length) break;
		const tag = /^<\s*(script|style|textarea|title)(?=[\s/>])/i.exec(source.slice(cursor, end + 1));
		if (tag) {
			const close = new RegExp('</' + tag[1] + '\\s*>', 'gi');
			close.lastIndex = end + 1;
			const match = close.exec(source);
			if (!match) break;
			end = match.index + match[0].length - 1;
		}
		cursor = safe = end + 1;
	}
	return safe;
}
