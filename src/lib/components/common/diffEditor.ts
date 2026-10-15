import type { ChangeSpec, Text } from '@codemirror/state';
import type { Chunk, DiffConfig } from '@codemirror/merge';

// A scanLimit also gives up based on document length, even for sparse, tiny edits.
export const diffEditorConfig: DiffConfig = { timeout: 100 };

export type MergeDirection = 'to-working' | 'to-proposal';

// Match rows by the text preserved inside a chunk, not their ordinal position.
export function changedLinePairs(a: Text, b: Text, chunk: Chunk): [number, number][] {
	const candidates = new Map<number, Map<number, { a: number; b: number; weight: number }>>();
	let fromA = chunk.fromA;
	let fromB = chunk.fromB;
	for (let index = 0; index <= chunk.changes.length; index++) {
		const change = chunk.changes[index];
		const endA = change ? chunk.fromA + change.fromA : Math.min(chunk.toA, a.length);
		const endB = change ? chunk.fromB + change.fromB : Math.min(chunk.toB, b.length);
		while (fromA < endA && fromB < endB) {
			const lineA = a.lineAt(fromA),
				lineB = b.lineAt(fromB);
			const length = Math.min(endA - fromA, endB - fromB, lineA.to - fromA, lineB.to - fromB);
			const weight = a.sliceString(fromA, fromA + length).replace(/\s/g, '').length;
			if (weight) {
				let row = candidates.get(lineA.from);
				if (!row) candidates.set(lineA.from, (row = new Map()));
				const pair = row.get(lineB.from) ?? { a: lineA.from, b: lineB.from, weight: 0 };
				pair.weight += weight;
				row.set(lineB.from, pair);
			}
			fromA += length || 1;
			fromB += length || 1;
		}
		if (change) {
			fromA = chunk.fromA + change.toA;
			fromB = chunk.fromB + change.toB;
		}
	}
	const bestA = new Map<number, { a: number; b: number; weight: number }>();
	const bestB = new Map<number, { a: number; b: number; weight: number }>();
	for (const row of candidates.values()) {
		for (const pair of row.values()) {
			if (pair.weight > (bestA.get(pair.a)?.weight ?? 0)) bestA.set(pair.a, pair);
			if (pair.weight > (bestB.get(pair.b)?.weight ?? 0)) bestB.set(pair.b, pair);
		}
	}
	return [...bestA.values()]
		.filter((pair) => bestB.get(pair.b) === pair)
		.map((pair) => [pair.a, pair.b]);
}

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
