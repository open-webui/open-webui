import type { ChangeSpec, Text } from '@codemirror/state';
import type { Chunk, DiffConfig } from '@codemirror/merge';

// A scanLimit also gives up based on document length, even for sparse, tiny edits.
export const diffEditorConfig: DiffConfig = { timeout: 100 };

export type MergeDirection = 'to-working' | 'to-proposal';

export function changedLineCounts(a: Text, b: Text, chunks: readonly Chunk[]) {
	const count = (doc: Text, side: 'A' | 'B') => {
		let total = 0;
		let lastLine = 0;
		for (const chunk of chunks) {
			for (const change of chunk.changes) {
				const from = chunk[`from${side}`] + change[`from${side}`];
				const to = chunk[`from${side}`] + change[`to${side}`];
				if (from === to) continue;
				const first = doc.lineAt(from).number;
				const last = doc.lineAt(to - 1).number;
				total += Math.max(0, last - Math.max(first - 1, lastLine));
				lastLine = last;
			}
		}
		return total;
	};
	return { removed: count(a, 'A'), added: count(b, 'B') };
}

export function chunkOverview(a: Text, b: Text, chunks: readonly Chunk[]) {
	const range = (doc: Text, from: number, to: number) => ({
		from: (doc.lineAt(Math.min(from, doc.length)).number - 1) / doc.lines,
		to: doc.lineAt(Math.min(Math.max(from, to - 1), doc.length)).number / doc.lines
	});
	return chunks.map((chunk) => ({
		a: range(a, chunk.fromA, chunk.toA),
		b: range(b, chunk.fromB, chunk.toB)
	}));
}

export function nearestOverviewChunk(
	ranges: ReturnType<typeof chunkOverview>,
	side: 'a' | 'b',
	position: number
) {
	let nearest = -1;
	let distance = Infinity;
	ranges.forEach((range, index) => {
		const delta = Math.max(range[side].from - position, position - range[side].to, 0);
		if (delta < distance) {
			nearest = index;
			distance = delta;
		}
	});
	return nearest;
}

export function copyChunk(a: Text, b: Text, chunk: Chunk, direction: MergeDirection): ChangeSpec {
	const toWorking = direction === 'to-working';
	const source = toWorking ? b : a;
	const destination = toWorking ? a : b;
	const [from, to, sourceFrom, sourceTo] = toWorking
		? [chunk.fromA, chunk.toA, chunk.fromB, chunk.toB]
		: [chunk.fromB, chunk.toB, chunk.fromA, chunk.toA];
	// Chunk ends include a virtual newline at EOF; only insert it between actual lines.
	let insert = source.sliceString(sourceFrom, Math.max(sourceFrom, sourceTo - 1));
	if (sourceFrom !== sourceTo && to <= destination.length) insert += '\n';
	return { from, to: Math.min(to, destination.length), insert };
}

export function keepBothChunk(a: Text, b: Text, chunk: Chunk): ChangeSpec | null {
	// A line-aligned chunk can include text on both sides even for a pure EOF insertion.
	if (
		!chunk.changes.some((change) => change.fromA < change.toA) ||
		!chunk.changes.some((change) => change.fromB < change.toB)
	)
		return null;
	const original = a.sliceString(chunk.fromA, Math.min(chunk.toA, a.length));
	const proposed = b.sliceString(chunk.fromB, Math.min(chunk.toB, b.length));
	return {
		from: chunk.fromB,
		to: Math.min(chunk.toB, b.length),
		insert: original + (original.endsWith('\n') ? '' : '\n') + proposed
	};
}

export function selectedChunk(chunks: readonly Chunk[], side: 'a' | 'b', position: number) {
	return chunks.findIndex((chunk) => {
		const from = side === 'a' ? chunk.fromA : chunk.fromB;
		const to = side === 'a' ? chunk.toA : chunk.toB;
		return position >= from && (position < to || position === from);
	});
}
