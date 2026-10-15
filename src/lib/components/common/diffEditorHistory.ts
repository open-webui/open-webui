import { EditorState, Transaction } from '@codemirror/state';
import { isolateHistory, undoDepth } from '@codemirror/commands';

type Side = 'a' | 'b';

// Keep the panes' native undo groups in chronological order.
export class DiffUndoHistory {
	private order: { side: Side; depth: number }[] = [];
	private lastSide: Side | null = null;

	get nextSide(): Side | null {
		return this.order.at(-1)?.side ?? null;
	}

	extension(side: Side) {
		return EditorState.transactionExtender.of((transaction) => {
			if (
				transaction.docChanged &&
				this.lastSide !== side &&
				!transaction.isUserEvent('undo') &&
				!transaction.isUserEvent('redo') &&
				!transaction.annotation(isolateHistory)
			)
				return { annotations: isolateHistory.of('before') };
			return null;
		});
	}

	record(side: Side, transaction: Transaction) {
		if (!transaction.docChanged || transaction.annotation(Transaction.addToHistory) === false)
			return;
		this.lastSide = side;
		const before = undoDepth(transaction.startState);
		const after = undoDepth(transaction.state);
		if (transaction.isUserEvent('undo')) {
			this.order = this.order.filter((entry) => entry.side !== side || entry.depth <= after);
			return;
		}
		// Native history periodically drops its oldest groups when it reaches its limit.
		if (after < before) {
			for (const entry of this.order) if (entry.side === side) entry.depth -= before + 1 - after;
		}
		this.order = this.order.filter(
			(entry) => entry.side !== side || (entry.depth > 0 && entry.depth < after)
		);
		if (after) this.order.push({ side, depth: after });
	}
}
