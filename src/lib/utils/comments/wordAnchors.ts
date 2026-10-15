/** Boundary strings are the docx-preview 0.4.0 renderer contract, tested in a browser. */
export function wordAnchors(container: HTMLElement): Map<string, Range> {
	const starts = new Map<string, Comment>();
	const ranges = new Map<string, Range>();
	const walker = document.createTreeWalker(container, NodeFilter.SHOW_COMMENT);
	let node: Node | null;
	while ((node = walker.nextNode())) {
		const start = /^start of comment #(.*)$/.exec(node.textContent ?? '');
		const end = /^end of comment #(.*)$/.exec(node.textContent ?? '');
		const point = /^comment #(.*?) by /.exec(node.textContent ?? '');
		if (start) starts.set(start[1], node as Comment);
		if (end && starts.has(end[1])) {
			const range = document.createRange();
			range.setStartAfter(starts.get(end[1])!);
			range.setEndBefore(node);
			ranges.set(end[1], range);
		}
		if (point && !ranges.has(point[1])) {
			const range = document.createRange();
			range.setStartBefore(node);
			range.collapse(true);
			ranges.set(point[1], range);
		}
	}
	return ranges;
}
