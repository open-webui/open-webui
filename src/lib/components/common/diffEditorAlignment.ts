import { StateEffect, StateField } from '@codemirror/state';
import {
	BlockType,
	Decoration,
	EditorView,
	WidgetType,
	type DecorationSet
} from '@codemirror/view';

// Font measurements can differ by fractions of a pixel between virtualized lines.
export function alignmentGeometryChanged(previous: readonly number[], next: readonly number[]) {
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

export function lineTextTop(view: EditorView, pos: number) {
	const block = view.lineBlockAt(pos);
	const text = Array.isArray(block.type)
		? block.type.find((part) => part.type === BlockType.Text && part.from === pos)
		: block.type === BlockType.Text
			? block
			: null;
	return text?.from === pos ? text.top : null;
}

// Measure matching rows locally; estimate unmatched ranges so large insertions remain scrollable.
export function alignChangedLines(
	a: EditorView,
	b: EditorView,
	pairs: readonly [number, number][]
) {
	const previous = (view: EditorView) => {
		const result = new Map<number, number>();
		for (let cursor = view.state.field(lineAlignment).iter(); cursor.value; cursor.next())
			result.set(cursor.value.spec.row, cursor.value.spec.widget.height);
		return result;
	};
	const oldA = previous(a),
		oldB = previous(b);
	const nextA = new Map(oldA),
		nextB = new Map(oldB);
	// Compare heights between adjacent matching rows, never estimated offsets from document start.
	for (let index = 0; index <= pairs.length; index++) {
		const start = index ? pairs[index - 1] : null;
		const end =
			index < pairs.length ? pairs[index] : [a.state.doc.length + 1, b.state.doc.length + 1];
		const from = start ?? [0, 0];
		const to = [Math.min(end[0], a.state.doc.length), Math.min(end[1], b.state.doc.length)];
		const measured =
			from[0] >= a.viewport.from &&
			from[1] >= b.viewport.from &&
			to[0] <= a.viewport.to &&
			to[1] <= b.viewport.to;
		if (!measured) {
			// Keep estimates fixed until the range is rendered, otherwise they feed back into the height map.
			if (oldA.has(end[0]) || oldB.has(end[1])) continue;
			const matchedRows = start && index < pairs.length ? 1 : 0;
			const unmatched =
				a.state.doc.lineAt(to[0]).number - a.state.doc.lineAt(from[0]).number > matchedRows ||
				b.state.doc.lineAt(to[1]).number - b.state.doc.lineAt(from[1]).number > matchedRows;
			if (!unmatched) continue;
		}
		const heights = [a, b].map((view, side) => {
			const from = start ? (measured ? start[side] : view.state.doc.lineAt(start[side]).to + 1) : 0,
				to = Math.min(end[side], view.state.doc.length);
			if (!measured && from >= end[side]) return 0;
			const top = start ? lineTextTop(view, from) : 0;
			const bottom =
				end[side] > view.state.doc.length ? view.lineBlockAt(to).bottom : lineTextTop(view, to);
			return top === null || bottom === null ? null : bottom - top;
		});
		if (heights[0] === null || heights[1] === null) continue;
		const difference = heights[0] - (oldA.get(end[0]) ?? 0) - heights[1] + (oldB.get(end[1]) ?? 0);
		nextA.delete(end[0]);
		nextB.delete(end[1]);
		if (difference < -1) nextA.set(end[0], -difference);
		if (difference > 1) nextB.set(end[1], difference);
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
						Decoration.widget({
							widget: new RowSpacer(height),
							block: true,
							side: pos ? 1 : -1,
							row: pos
						}).range(Math.max(0, pos - 1))
					),
					true
				)
			)
		});
	};
	apply(a, oldA, nextA);
	apply(b, oldB, nextB);
}
