import { parseDiffRows, emphasizePair, type DiffRow } from '../../chat/Messages/diff';

export type VersionDiffLine = DiffRow & { noNewline?: boolean };
export type VersionDiffRow = { before: VersionDiffLine | null; after: VersionDiffLine | null };
export type VersionDiffHunk = { beforeStart: number; afterStart: number; rows: VersionDiffRow[] };

export function versionDiffHunks(code: string): VersionDiffHunk[] {
	const hunks: VersionDiffHunk[] = [];
	let hunk: VersionDiffHunk | null = null;
	let removed: VersionDiffLine[] = [];
	let added: VersionDiffLine[] = [];
	let previous: VersionDiffLine | null = null;
	const flush = () => {
		for (let index = 0; index < Math.max(removed.length, added.length); index++) {
			const before = removed[index] ?? null;
			const after = added[index] ?? null;
			if (before && after) emphasizePair(before, after);
			hunk?.rows.push({ before, after });
		}
		removed = [];
		added = [];
	};
	for (const row of parseDiffRows(code)) {
		if (row.type === 'hunk') {
			flush();
			const match = row.content.match(/^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
			hunk = {
				beforeStart: Number(match?.[1] ?? 0),
				afterStart: Number(match?.[2] ?? 0),
				rows: []
			};
			hunks.push(hunk);
			previous = null;
		} else if (row.type === 'meta') {
			if (previous && row.content.startsWith('\\ No newline')) previous.noNewline = true;
		} else if (hunk && row.type !== 'file' && (row.oldNumber !== null || row.newNumber !== null)) {
			previous = row;
			if (row.type === 'deletion') removed.push(row);
			else if (row.type === 'addition') added.push(row);
			else {
				flush();
				hunk.rows.push({ before: row, after: row });
			}
		}
	}
	flush();
	return hunks;
}
