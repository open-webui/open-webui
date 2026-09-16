export type DiffSegment = { text: string; changed: boolean };
export type DiffRow = {
	type: 'file' | 'hunk' | 'addition' | 'deletion' | 'meta' | 'context';
	prefix: string;
	content: string;
	oldNumber: number | null;
	newNumber: number | null;
	segments: DiffSegment[];
};

export function parseDiffRows(code: string): DiffRow[] {
	let oldNumber = 0;
	let newNumber = 0;
	let oldRemaining = 0;
	let newRemaining = 0;
	const rows = code.split('\n').map((text): DiffRow => {
		const row: DiffRow = {
			type: 'context',
			prefix: '',
			content: text,
			oldNumber: null,
			newNumber: null,
			segments: []
		};
		const hunk = text.match(/^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/);
		const inHunk = oldRemaining > 0 || newRemaining > 0;
		if (hunk) {
			row.type = 'hunk';
			oldNumber = Number(hunk[1]);
			newNumber = Number(hunk[3]);
			oldRemaining = Number(hunk[2] ?? 1);
			newRemaining = Number(hunk[4] ?? 1);
		} else if (
			text.startsWith('diff ') ||
			(!inHunk &&
				/^(index |---(?:\s|$)|\+\+\+(?:\s|$)|(?:old|new|deleted file|new file) mode |(?:dis)?similarity index |(?:rename|copy) (?:from|to) )/.test(
					text
				))
		) {
			row.type = 'file';
			oldRemaining = newRemaining = 0;
		} else if (text.startsWith('@@')) {
			// Incomplete streaming headers must not inherit the preceding hunk's numbers.
			row.type = 'hunk';
			oldRemaining = newRemaining = 0;
		} else if (text.startsWith('\\')) {
			row.type = 'meta';
		} else {
			if (text.startsWith('+')) row.type = 'addition';
			if (text.startsWith('-')) row.type = 'deletion';
			if (/^[+\- ]/.test(text)) {
				row.prefix = text[0];
				row.content = text.slice(1);
			}
			if (inHunk && (row.prefix || text === '')) {
				if (row.type !== 'addition' && oldRemaining > 0) {
					row.oldNumber = oldNumber++;
					oldRemaining--;
				}
				if (row.type !== 'deletion' && newRemaining > 0) {
					row.newNumber = newNumber++;
					newRemaining--;
				}
			}
		}
		row.segments = [{ text: row.content, changed: false }];
		return row;
	});

	for (let i = 0; i < rows.length; ) {
		const removed: DiffRow[] = [];
		const added: DiffRow[] = [];
		while (rows[i]?.type === 'deletion' || rows[i]?.type === 'addition') {
			(rows[i].type === 'deletion' ? removed : added).push(rows[i++]);
		}
		if (removed.length === added.length) {
			removed.forEach((oldRow, index) => emphasizePair(oldRow, added[index]));
		}
		i++;
	}
	return rows;
}

function emphasizePair(oldRow: DiffRow, newRow: DiffRow) {
	if (
		oldRow.content === newRow.content ||
		Math.max(oldRow.content.length, newRow.content.length) >= 1024
	)
		return;
	const oldText = Array.from(oldRow.content);
	const newText = Array.from(newRow.content);
	let start = 0;
	while (start < Math.min(oldText.length, newText.length) && oldText[start] === newText[start])
		start++;
	let oldEnd = oldText.length;
	let newEnd = newText.length;
	while (oldEnd > start && newEnd > start && oldText[oldEnd - 1] === newText[newEnd - 1]) {
		oldEnd--;
		newEnd--;
	}
	// ponytail: like computer's Git view, emphasize one changed middle per paired line.
	// Use a token diff if multiple independent edits need separate spans.
	for (const [row, text, end] of [
		[oldRow, oldText, oldEnd],
		[newRow, newText, newEnd]
	] as const) {
		row.segments = [
			{ text: text.slice(0, start).join(''), changed: false },
			{ text: text.slice(start, end).join(''), changed: true },
			{ text: text.slice(end).join(''), changed: false }
		].filter((segment) => segment.text.length > 0);
	}
}
