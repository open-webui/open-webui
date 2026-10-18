import { StateEffect, StateField } from '@codemirror/state';
import {
	BlockType,
	Decoration,
	EditorView,
	WidgetType,
	type DecorationSet
} from '@codemirror/view';
import type { Chunk } from '@codemirror/merge';
import { changedLinePairs } from './diffEditor';

export function alignmentGeometryChanged(previous: readonly number[], next: readonly number[]) {
	// DOM line-height measurements can vary by a fraction of a pixel while scrolling.
	return next.some((value, index) => Math.abs(value - previous[index]) > (index < 2 ? 0 : 0.5));
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

// MergeView owns alignment between chunks. Only align rows inside each changed
// chunk, using local heights so its spacers cannot feed back into ours.
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
	const textTop = (view: EditorView, pos: number) => {
		const block = view.lineBlockAt(pos);
		const text = Array.isArray(block.type)
			? block.type.find((part) => part.type === BlockType.Text && part.from === pos)
			: block.type === BlockType.Text
				? block
				: null;
		return text?.from === pos ? text.top : null;
	};
	for (const chunk of chunks) {
		if (
			chunk.toA < a.viewport.from ||
			chunk.toB < b.viewport.from ||
			chunk.fromA > a.viewport.to ||
			chunk.fromB > b.viewport.to
		)
			continue;
		let previousA = chunk.fromA,
			previousB = chunk.fromB,
			first = true;
		for (const [posA, posB] of changedLinePairs(a.state.doc, b.state.doc, chunk)) {
			// Both ends of the interval must be rendered; offscreen estimates are not row heights.
			if (
				previousA >= a.viewport.from &&
				previousB >= b.viewport.from &&
				posA <= a.viewport.to &&
				posB <= b.viewport.to
			) {
				const topA = textTop(a, posA),
					topB = textTop(b, posB);
				const startA = first ? a.lineBlockAt(previousA).top : textTop(a, previousA);
				const startB = first ? b.lineBlockAt(previousB).top : textTop(b, previousB);
				if (topA !== null && topB !== null && startA !== null && startB !== null) {
					const heightA = topA - startA - (oldA.get(posA) ?? 0);
					const heightB = topB - startB - (oldB.get(posB) ?? 0);
					const difference = heightA - heightB;
					nextA.delete(posA);
					nextB.delete(posB);
					if (difference < -1) nextA.set(posA, -difference);
					if (difference > 1) nextB.set(posB, difference);
				}
			}
			previousA = posA;
			previousB = posB;
			first = false;
		}
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
