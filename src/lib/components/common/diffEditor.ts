import { StateEffect, StateField, type ChangeSpec, type Text } from '@codemirror/state';
import { Decoration, EditorView, WidgetType, type DecorationSet } from '@codemirror/view';
import { Chunk, type DiffConfig } from '@codemirror/merge';

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

export function visibleDiffChunks(
	a: Text,
	b: Text,
	chunks: readonly Chunk[],
	ignoreWhitespace: boolean,
	ignoreEmphasis = false
) {
	if (!ignoreWhitespace && !ignoreEmphasis) return chunks;
	const ignored = ignoreWhitespace ? (ignoreEmphasis ? /[\s_*]/g : /\s/g) : /[_*]/g;
	return chunks.flatMap((chunk) => {
		const changes = chunk.changes.filter(
			(change) =>
				a.sliceString(chunk.fromA + change.fromA, chunk.fromA + change.toA).replace(ignored, '') !==
				b.sliceString(chunk.fromB + change.fromB, chunk.fromB + change.toB).replace(ignored, '')
		);
		return changes.length
			? [new Chunk(changes, chunk.fromA, chunk.toA, chunk.fromB, chunk.toB, chunk.precise)]
			: [];
	});
}

export type CollapsedPair = {
	a: { from: number; to: number; lines: number };
	b: { from: number; to: number; lines: number };
};

export function unchangedRanges(a: Text, b: Text, chunks: readonly Chunk[]): CollapsedPair[] {
	const result: CollapsedPair[] = [];
	let previousA = 0,
		previousB = 0;
	for (let index = 0; index <= chunks.length; index++) {
		const chunk = chunks[index];
		const range = (doc: Text, previous: number, next: number | undefined) => {
			const first = index ? doc.lineAt(Math.min(previous, doc.length)).number + 3 : 1;
			const last = next === undefined ? doc.lines : doc.lineAt(next).number - 4;
			return last - first >= 3
				? { from: doc.line(first).from, to: doc.line(last).to, lines: last - first + 1 }
				: null;
		};
		const left = range(a, previousA, chunk?.fromA),
			right = range(b, previousB, chunk?.fromB);
		if (left && right) result.push({ a: left, b: right });
		if (chunk) {
			previousA = chunk.toA;
			previousB = chunk.toB;
		}
	}
	return result;
}

class CollapsedLines extends WidgetType {
	constructor(
		readonly label: string,
		readonly expand: () => void
	) {
		super();
	}
	toDOM() {
		const button = document.createElement('button');
		button.type = 'button';
		button.className = 'cm-collapsedLines w-full text-left';
		button.textContent = this.label;
		button.addEventListener('click', this.expand);
		return button;
	}
	get estimatedHeight() {
		return 27;
	}
	ignoreEvent() {
		return true;
	}
}

export const setDiffPresentation = StateEffect.define<DecorationSet>();
const presentation = StateField.define<DecorationSet>({
	create: () => Decoration.none,
	update(value, transaction) {
		for (const effect of transaction.effects)
			if (effect.is(setDiffPresentation)) return effect.value;
		return value.map(transaction.changes);
	},
	provide: (field) => EditorView.decorations.from(field)
});
export const diffPresentation = [
	presentation,
	EditorView.atomicRanges.of((view) =>
		view.state
			.field(presentation)
			.update({ filter: (_from, _to, decoration) => !!decoration.spec.block })
	)
];

export function presentationDecorations(
	doc: Text,
	side: 'a' | 'b',
	chunks: readonly Chunk[],
	ignoreWhitespace: boolean,
	ignoreEmphasis: boolean,
	folds: readonly CollapsedPair[],
	label: (lines: number) => string,
	expand: (pair: CollapsedPair) => void
) {
	const decorations = [];
	if (ignoreWhitespace || ignoreEmphasis) {
		const visible = ignoreWhitespace ? (ignoreEmphasis ? /[^\s_*]+/g : /\S+/g) : /[^_*]+/g;
		const rows = new Set<number>();
		for (const chunk of chunks) {
			const offset = side === 'a' ? chunk.fromA : chunk.fromB;
			for (const change of chunk.changes) {
				const from = offset + (side === 'a' ? change.fromA : change.fromB);
				const to = offset + (side === 'a' ? change.toA : change.toB);
				for (const match of doc.sliceString(from, to).matchAll(visible)) {
					const start = from + match.index;
					decorations.push(
						Decoration.mark({ class: 'cm-visibleChangedText' }).range(
							start,
							start + match[0].length
						)
					);
					for (
						let line = doc.lineAt(start).number;
						line <= doc.lineAt(start + match[0].length - 1).number;
						line++
					)
						rows.add(doc.line(line).from);
				}
			}
		}
		for (const from of rows)
			decorations.push(Decoration.line({ class: 'cm-visibleChangedLine' }).range(from));
	}
	for (const pair of folds) {
		const range = pair[side];
		decorations.push(
			Decoration.replace({
				block: true,
				widget: new CollapsedLines(label(range.lines), () => expand(pair))
			}).range(range.from, range.to)
		);
	}
	return Decoration.set(decorations, true);
}
