import { StateEffect, StateField, type Text } from '@codemirror/state';
import {
	BlockType,
	Decoration,
	EditorView,
	WidgetType,
	type DecorationSet
} from '@codemirror/view';
import type { Chunk } from '@codemirror/merge';
import { changedLinePairs } from './diffEditor';

export function pairedLinePosition(a: Text, b: Text, chunks: readonly Chunk[], position: number) {
	let offset = 0;
	for (const chunk of chunks) {
		if (position < chunk.fromA) break;
		if (position < chunk.toA) {
			const pairs = changedLinePairs(a, b, chunk);
			const line = a.lineAt(position).from;
			return (
				(pairs.find(([from]) => from >= line) ?? pairs.at(-1))?.[1] ??
				Math.min(chunk.fromB, b.length)
			);
		}
		offset = chunk.toB - chunk.toA;
	}
	return Math.max(0, Math.min(position + offset, b.length));
}

class RowSpacer extends WidgetType {
	constructor(readonly height: number) {
		super();
	}
	eq(other: RowSpacer) {
		return Math.abs(this.height - other.height) <= 1;
	}
	toDOM() {
		const element = document.createElement('div');
		element.className = 'cm-mergeSpacer cm-diff-rowSpacer';
		element.style.height = `${this.height}px`;
		return element;
	}
	get estimatedHeight() {
		return this.height;
	}
}
const setSpacers = StateEffect.define<DecorationSet>();
export const lineAlignment = StateField.define<DecorationSet>({
	create: () => Decoration.none,
	update: (value, transaction) => {
		for (const effect of transaction.effects) if (effect.is(setSpacers)) return effect.value;
		return transaction.docChanged ? Decoration.none : value;
	},
	provide: (field) => EditorView.decorations.from(field)
});

export function clearLineAlignment(a: EditorView, b: EditorView) {
	let changed = false;
	for (const view of [a, b]) {
		if (view.state.field(lineAlignment).size) {
			view.dispatch({ effects: setSpacers.of(Decoration.none) });
			changed = true;
		}
	}
	return changed;
}

// Only remeasure paired rows present in both virtualized viewports. Recomputing
// offscreen spacers from estimated heights would move already aligned content.
export function alignChangedLines(a: EditorView, b: EditorView, chunks: readonly Chunk[]) {
	const previous = (view: EditorView) => {
		const result = new Map<number, number>();
		for (let cursor = view.state.field(lineAlignment).iter(); cursor.value; cursor.next())
			result.set(cursor.from, cursor.value.spec.widget.height);
		return result;
	};
	const oldA = previous(a),
		oldB = previous(b);
	const nextA = new Map(oldA),
		nextB = new Map(oldB);
	let offsetA = 0,
		offsetB = 0;
	const textTop = (view: EditorView, pos: number) => {
		const block = view.lineBlockAt(pos);
		const text = Array.isArray(block.type)
			? block.type.find((part) => part.type === BlockType.Text && part.from === pos)
			: block.type === BlockType.Text
				? block
				: null;
		return text?.from === pos ? text.top : null;
	};
	const align = (posA: number, posB: number) => {
		if (
			posA < a.viewport.from ||
			posB < b.viewport.from ||
			posA > a.viewport.to ||
			posB > b.viewport.to
		)
			return;
		const topA = textTop(a, posA),
			topB = textTop(b, posB);
		if (topA === null || topB === null) return;
		const previousA = oldA.get(posA) ?? 0,
			previousB = oldB.get(posB) ?? 0;
		const difference = topA - previousA + offsetA - topB + previousB - offsetB;
		const sizeA = difference < -1 ? -difference : 0,
			sizeB = difference > 1 ? difference : 0;
		nextA.delete(posA);
		nextB.delete(posB);
		if (sizeA) nextA.set(posA, sizeA);
		if (sizeB) nextB.set(posB, sizeB);
		offsetA += sizeA - previousA;
		offsetB += sizeB - previousB;
	};
	let fromA = 0,
		fromB = 0;
	for (let index = 0; index <= chunks.length; index++) {
		const chunk = chunks[index];
		const endA = chunk ? chunk.fromA : a.state.doc.length + 1;
		let posA = Math.max(
			fromA,
			a.state.doc.lineAt(
				Math.min(
					a.state.doc.length,
					Math.max(fromA, a.viewport.from, fromA + b.viewport.from - fromB)
				)
			).from
		);
		for (; posA < endA && posA <= a.viewport.to; posA = a.state.doc.lineAt(posA).to + 1) {
			const posB = fromB + posA - fromA;
			if (posB > b.viewport.to) break;
			align(posA, posB);
		}
		if (!chunk) break;
		for (const [posA, posB] of changedLinePairs(a.state.doc, b.state.doc, chunk)) align(posA, posB);
		fromA = chunk.toA;
		fromB = chunk.toB;
	}
	const apply = (view: EditorView, old: Map<number, number>, next: Map<number, number>) => {
		if (
			old.size === next.size &&
			[...next].every(([pos, size]) => Math.abs((old.get(pos) ?? 0) - size) <= 1)
		)
			return;
		view.dispatch({
			effects: setSpacers.of(
				Decoration.set(
					[...next].map(([pos, height]) =>
						Decoration.widget({ widget: new RowSpacer(height), block: true, side: -1 }).range(pos)
					),
					true
				)
			)
		});
	};
	apply(a, oldA, nextA);
	apply(b, oldB, nextB);
}
