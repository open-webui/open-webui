import { autoUpdate, computePosition, flip, offset, shift } from '@floating-ui/dom';

// Range geometry follows scrolling; Floating UI also accounts for the on-screen keyboard.
export function positionSelectionToolbar(node: HTMLElement, range: Range | null) {
	let cleanup = () => {};
	const update = (range: Range | null) => {
		cleanup();
		cleanup = () => {};
		if (!range) return;
		let active = true;
		const reference = {
			getBoundingClientRect: () => range.getBoundingClientRect(),
			contextElement: range.commonAncestorContainer.parentElement ?? undefined
		};
		const stop = autoUpdate(reference, node, () => {
			void computePosition(reference, node, {
				strategy: 'fixed',
				placement: 'bottom-start',
				middleware: [offset(12), flip(), shift({ padding: 8 })]
			}).then(({ x, y }) => {
				if (!active) return;
				node.style.left = `${x}px`;
				node.style.top = `${y}px`;
			});
		});
		cleanup = () => {
			active = false;
			stop();
		};
	};
	update(range);
	return { update, destroy: () => cleanup() };
}
