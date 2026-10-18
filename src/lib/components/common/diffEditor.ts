import {
	StateEffect,
	StateField,
	RangeSet,
	ChangeSet,
	EditorState,
	type EditorStateConfig,
	type Transaction,
	type ChangeSpec,
	type Text
} from '@codemirror/state';
import {
	Decoration,
	BlockType,
	EditorView,
	GutterMarker,
	gutter,
	WidgetType,
	type DecorationSet
} from '@codemirror/view';
import { Chunk, type DiffConfig } from '@codemirror/merge';
import { lineTextTop } from './diffEditorAlignment';

// A scanLimit also gives up based on document length, even for sparse, tiny edits.
export const diffEditorConfig: DiffConfig = { timeout: 100 };

// The existing row alignment owns spacing; MergeView's second spacer pass would fight it.
export class DiffEditorView {
	readonly a: EditorView;
	readonly b: EditorView;
	readonly dom: HTMLDivElement;
	chunks: readonly Chunk[];
	linePairs: [number, number][];
	scrollSource: EditorView;
	private scrollFrame = 0;
	constructor(config: { a: EditorStateConfig; b: EditorStateConfig; parent: HTMLElement }) {
		const states = (['a', 'b'] as const).map((side) =>
			EditorState.create({
				...config[side],
				extensions: [
					config[side].extensions ?? [],
					EditorView.editorAttributes.of({ class: `cm-merge-${side}` })
				]
			})
		);
		this.chunks = Chunk.build(states[0].doc, states[1].doc, diffEditorConfig);
		this.linePairs = matchingLinePairs(states[0].doc, states[1].doc, this.chunks);
		this.dom = document.createElement('div');
		this.dom.className = 'cm-mergeView';
		const editors = this.dom.appendChild(document.createElement('div'));
		editors.className = 'cm-mergeViewEditors';
		const create = (side: 'a' | 'b', index: number) => {
			const wrapper = editors.appendChild(document.createElement('div'));
			wrapper.className = 'cm-mergeViewEditor';
			return new EditorView({
				state: states[index],
				parent: wrapper,
				dispatchTransactions: (transactions) => this.dispatch(transactions, side)
			});
		};
		this.a = create('a', 0);
		this.b = create('b', 1);
		config.parent.appendChild(this.dom);
		// Only the pane receiving input drives scrolling; the other pane's height corrections must not feed back.
		this.scrollSource = this.a;
		for (const editor of [this.a, this.b]) {
			for (const event of ['wheel', 'touchstart', 'pointerdown', 'keydown', 'focusin'])
				editor.dom.addEventListener(event, () => (this.scrollSource = editor), { passive: true });
			editor.scrollDOM.addEventListener('scroll', () => this.syncScroll());
		}
	}
	syncScroll() {
		if (this.scrollFrame) return;
		this.scrollFrame = requestAnimationFrame(() => {
			this.scrollFrame = 0;
			const index = this.scrollSource === this.a ? 0 : 1;
			const other = index === 0 ? this.b : this.a;
			const block = this.scrollSource.lineBlockAtHeight(this.scrollSource.scrollDOM.scrollTop);
			const line = block.from;
			const text = Array.isArray(block.type)
				? block.type.find((part) => part.type === BlockType.Text)
				: block.type === BlockType.Text
					? block
					: null;
			let pair = this.linePairs[0];
			for (const candidate of this.linePairs) {
				if (candidate[index] > line) break;
				pair = candidate;
			}
			if (
				pair &&
				text &&
				pair[index] === text.from &&
				this.scrollSource.scrollDOM.scrollTop < text.bottom &&
				(pair[1 - index] < other.viewport.from || pair[1 - index] > other.viewport.to)
			)
				other.dispatch({
					effects: EditorView.scrollIntoView(pair[1 - index], { y: 'nearest', yMargin: 0 })
				});
			const sourceTop = pair
				? (lineTextTop(this.scrollSource, pair[index]) ??
					this.scrollSource.lineBlockAt(pair[index]).top)
				: 0;
			const targetTop = pair
				? (lineTextTop(other, pair[1 - index]) ?? other.lineBlockAt(pair[1 - index]).top)
				: 0;
			other.scrollDOM.scrollTop = targetTop + this.scrollSource.scrollDOM.scrollTop - sourceTop;
		});
	}
	private dispatch(transactions: readonly Transaction[], side: 'a' | 'b') {
		if (transactions.some((transaction) => transaction.docChanged)) {
			const document = transactions[transactions.length - 1].newDoc;
			const changes = transactions.reduce(
				(changes, transaction) => changes.compose(transaction.changes),
				ChangeSet.empty(transactions[0].startState.doc.length)
			);
			this.chunks =
				side === 'a'
					? Chunk.updateA(this.chunks, document, this.b.state.doc, changes, diffEditorConfig)
					: Chunk.updateB(this.chunks, this.a.state.doc, document, changes, diffEditorConfig);
			this.linePairs = matchingLinePairs(
				side === 'a' ? document : this.a.state.doc,
				side === 'b' ? document : this.b.state.doc,
				this.chunks
			);
		}
		this[side].update(transactions);
	}
	destroy() {
		cancelAnimationFrame(this.scrollFrame);
		this.a.destroy();
		this.b.destroy();
		this.dom.remove();
	}
}

// Pair unchanged rows and the rows whose text survives within changed chunks.
function matchingLinePairs(a: Text, b: Text, chunks: readonly Chunk[]): [number, number][] {
	const pairs: [number, number][] = [];
	let fromA = 0,
		fromB = 0;
	for (let index = 0; index <= chunks.length; index++) {
		const chunk = chunks[index];
		const end = chunk ? chunk.fromA : a.length + 1;
		for (let pos = fromA; pos < end; pos = a.lineAt(pos).to + 1)
			pairs.push([pos, fromB + pos - fromA]);
		if (!chunk) break;
		for (const pair of changedLinePairs(a, b, chunk)) pairs.push(pair);
		fromA = chunk.toA;
		fromB = chunk.toB;
	}
	return pairs;
}

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
class ChangedLineMarker extends GutterMarker {
	elementClass = 'cm-changedLineGutter';
}
const changedLineMarker = new ChangedLineMarker();

export const diffPresentation = [
	presentation,
	gutter({
		class: 'cm-changeGutter',
		renderEmptyElements: true,
		markers: (view) => {
			const markers = [];
			for (let cursor = view.state.field(presentation).iter(); cursor.value; cursor.next())
				if (cursor.value.spec.class === 'cm-visibleChangedLine')
					markers.push(changedLineMarker.range(cursor.from));
			return RangeSet.of(markers, true);
		}
	}),
	EditorView.baseTheme({
		'.cm-changeGutter': { width: '3px' },
		'&.cm-merge-a .cm-changedLineGutter': { backgroundColor: '#f0a394' },
		'&.cm-merge-b .cm-changedLineGutter': { backgroundColor: '#7dd3c5' }
	}),
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
	const visible = ignoreWhitespace
		? ignoreEmphasis
			? /[^\s_*]+/g
			: /\S+/g
		: ignoreEmphasis
			? /[^_*]+/g
			: /[\s\S]+/g;
	const rows = new Set<number>();
	for (const chunk of chunks) {
		const offset = side === 'a' ? chunk.fromA : chunk.fromB;
		if (!ignoreWhitespace && !ignoreEmphasis) {
			const end = side === 'a' ? chunk.toA : chunk.toB;
			for (let from = offset; from < end && from <= doc.length; from = doc.lineAt(from).to + 1)
				rows.add(from);
		}
		for (const change of chunk.changes) {
			const from = offset + (side === 'a' ? change.fromA : change.fromB);
			const to = offset + (side === 'a' ? change.toA : change.toB);
			for (const match of doc.sliceString(from, to).matchAll(visible)) {
				const start = from + match.index;
				decorations.push(
					Decoration.mark({ class: 'cm-visibleChangedText' }).range(start, start + match[0].length)
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
