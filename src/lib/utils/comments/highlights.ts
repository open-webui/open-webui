/** Use DOM text ranges so highlight edges follow actual glyph layout, including zoom. */
export function highlightRange(
	container: HTMLElement,
	layer: HTMLElement,
	range: Range,
	id: string,
	label: string
): boolean {
	const bounds = container.getBoundingClientRect();
	const scale = bounds.width / container.offsetWidth || 1;
	const rects = Array.from(range.getClientRects()).filter((r) => r.width > 0 && r.height > 0);
	for (const rect of rects) {
		const target = document.createElement('button');
		target.type = 'button';
		target.dataset.fileCommentId = id;
		target.dataset.commentHighlight = id;
		target.setAttribute('aria-label', label);
		target.setAttribute('aria-haspopup', 'dialog');
		Object.assign(target.style, {
			position: 'absolute',
			left: `${(rect.left - bounds.left) / scale}px`,
			top: `${(rect.top - bounds.top) / scale}px`,
			width: `${rect.width / scale}px`,
			height: `${rect.height / scale}px`,
			// Let the text underneath receive native selection gestures.
			pointerEvents: 'none',
			padding: '0',
			margin: '0',
			border: '0',
			borderBottom: '1px solid rgba(180,130,30,.55)',
			borderRadius: '2px',
			background: 'rgba(250,204,21,.20)',
			cursor: 'help'
		});
		layer.appendChild(target);
	}
	return rects.length > 0;
}

export function commentPin(id: string, label: string): HTMLButtonElement {
	const button = document.createElement('button');
	button.type = 'button';
	button.dataset.fileCommentId = id;
	button.setAttribute('aria-label', label);
	button.setAttribute('aria-haspopup', 'dialog');
	button.innerHTML =
		'<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 13.8214 2.48697 15.5291 3.33782 17L2.5 21.5L7 20.6622C8.47087 21.513 10.1786 22 12 22Z"/></svg>';
	button.className =
		'flex items-center justify-center rounded text-base-400 hover:text-base-600 dark:text-base-500 dark:hover:text-base-300 bg-base-0/95 dark:bg-base-850/95 focus-visible:outline focus-visible:outline-2';
	Object.assign(button.style, {
		position: 'absolute',
		width: '20px',
		height: '20px',
		pointerEvents: 'auto',
		cursor: 'help'
	});
	return button;
}

type TextIndex = { text: string; chars: Array<{ node: Text; offset: number; end: number }> };

/** The text under a container with whitespace removed, mapped back to its nodes. */
export function textIndex(container: HTMLElement, within: string | null = '.textLayer'): TextIndex {
	const chars: TextIndex['chars'] = [];
	let text = '';
	const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
	let next: Node | null;
	while ((next = walker.nextNode())) {
		const node = next as Text;
		const parent = node.parentElement;
		if (within ? !parent?.closest(within) : parent?.closest('style, script')) continue;
		let offset = 0;
		for (const char of node.data) {
			for (const normalized of char.normalize('NFKC'))
				if (!/\s/.test(normalized)) {
					text += normalized;
					chars.push({ node, offset, end: offset + char.length });
				}
			offset += char.length;
		}
	}
	return { text, chars };
}

/** The range of a quote that appears exactly once in the indexed text. */
export function rangeOf({ text, chars }: TextIndex, quote: string): Range | null {
	const needle = quote.normalize('NFKC').replace(/\s/g, '');
	const index = needle ? text.indexOf(needle) : -1;
	if (index < 0 || text.indexOf(needle, index + 1) !== -1) return null;
	const start = chars[index],
		end = chars[index + needle.length - 1];
	if (!start || !end) return null;
	const range = document.createRange();
	range.setStart(start.node, start.offset);
	range.setEnd(end.node, end.end);
	return range;
}

export function findTextRange(container: HTMLElement, quote: string): Range | null {
	return rangeOf(textIndex(container), quote);
}

/** The lines of a retrieved Markdown passage, as they would read on the source page. */
export function quoteLines(passage: string, limit = 400): string[] {
	const lines = passage
		// Table cells and other HTML blocks become lines of their own
		.replace(/<[^<>]+>/g, '\n')
		.replace(/!?\[([^\[\]]*)\]\([^()]*\)/g, '$1')
		.split(/\n|\|/)
		// A sentence can still match where the rest of its paragraph reads differently
		.flatMap((line) => line.split(/(?<=[.!?;:])\s+/))
		.map((line) =>
			line
				.replace(/^\s*(#{1,6}|[-*+>]|\d+[.)])\s+/, '')
				.replace(/[*_`$]/g, '')
				.trim()
		)
		.filter((line) => line.replace(/\s/g, '').length >= 6);
	return [...new Set(lines)].slice(0, limit);
}

/** Mark a text range without making it a comment target. */
export function markRange(
	container: HTMLElement,
	layer: HTMLElement,
	range: Range,
	quote = ''
): void {
	const bounds = container.getBoundingClientRect();
	const scale = bounds.width / container.offsetWidth || 1;
	for (const rect of range.getClientRects()) {
		if (rect.width <= 0 || rect.height <= 0) continue;
		const mark = document.createElement('div');
		mark.dataset.quote = quote;
		Object.assign(mark.style, {
			position: 'absolute',
			left: `${(rect.left - bounds.left) / scale}px`,
			top: `${(rect.top - bounds.top) / scale}px`,
			width: `${rect.width / scale}px`,
			height: `${rect.height / scale}px`,
			borderRadius: '2px',
			background: 'rgba(250,204,21,.25)'
		});
		layer.appendChild(mark);
	}
}

/** The quote mark under a point. Marks ignore the pointer so the text under them stays selectable. */
export function markAt(root: ParentNode | null | undefined, x: number, y: number) {
	return Array.from(root?.querySelectorAll<HTMLElement>('[data-quote]') ?? []).find((mark) => {
		const rect = mark.getBoundingClientRect();
		return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
	});
}

type QuoteMarkOptions = {
	quotes: string[];
	onHover?: (index: number | null, rect: DOMRect | null) => void;
};

/**
 * Mark quotes in any preview drawn as real text, such as a Word document or a sheet.
 * The marks sit in the preview's own scrolling area and are redrawn when it changes.
 */
export function quoteMarks(node: HTMLElement, options: QuoteMarkOptions) {
	let layer: HTMLElement | null = null;
	let timer: ReturnType<typeof setTimeout> | null = null;
	let hovered: number | null = null;
	let revealed = false;
	let revealedQuotes: string[] | null = null;

	const redraw = () => {
		if (timer) clearTimeout(timer);
		timer = setTimeout(draw, 200);
	};
	const observer = new MutationObserver(redraw);
	// A centred page moves when its pane is resized, with nothing inside it changing
	const resizeObserver = new ResizeObserver(redraw);
	resizeObserver.observe(node);
	const observe = () =>
		observer.observe(node, {
			subtree: true,
			childList: true,
			attributes: true,
			attributeFilter: ['style', 'class']
		});

	function draw() {
		observer.disconnect();
		layer?.remove();
		layer = null;
		const index = options.quotes.length ? textIndex(node, null) : null;
		const ranges = options.quotes
			.map((quote, i) => ({ i, range: index && rangeOf(index, quote) }))
			.filter((found): found is { i: number; range: Range } => !!found.range);
		if (ranges.length) {
			// The marks scroll with the text, so they live inside whatever scrolls it
			let scroller = ranges[0].range.startContainer.parentElement ?? node;
			while (scroller !== node && !/auto|scroll/.test(getComputedStyle(scroller).overflowY))
				scroller = scroller.parentElement ?? node;
			if (getComputedStyle(scroller).position === 'static') scroller.style.position = 'relative';
			layer = document.createElement('div');
			Object.assign(layer.style, {
				position: 'absolute',
				left: '0',
				top: '0',
				width: '0',
				height: '0',
				pointerEvents: 'none',
				zIndex: '3'
			});
			scroller.prepend(layer);
			// Text already marked by an earlier quote is not marked again, so no mark looks darker
			const drawn: Range[] = [];
			for (const { i, range } of ranges) {
				const overlaps = drawn.some(
					(other) =>
						range.compareBoundaryPoints(Range.END_TO_START, other) < 0 &&
						range.compareBoundaryPoints(Range.START_TO_END, other) > 0
				);
				if (overlaps) continue;
				drawn.push(range);
				markRange(layer, layer, range, String(i));
			}
			if (!revealed && layer.firstElementChild) {
				revealed = true;
				revealedQuotes = options.quotes;
				layer.firstElementChild.scrollIntoView({ block: 'center' });
			}
		}
		observe();
	}

	const hover = (event: MouseEvent | null) => {
		const mark = event ? markAt(layer, event.clientX, event.clientY) : undefined;
		const index = mark ? Number(mark.dataset.quote) : null;
		if (index === hovered) return;
		hovered = index;
		options.onHover?.(index, mark?.getBoundingClientRect() ?? null);
	};
	const leave = () => hover(null);
	node.addEventListener('mousemove', hover);
	node.addEventListener('mouseleave', leave);
	draw();

	return {
		update(next: QuoteMarkOptions) {
			const changed = next.quotes !== options.quotes;
			options = next;
			if (!changed) return;
			// Marks switched back on stay where the reader is; only new quotes scroll into view
			if (next.quotes.length && next.quotes !== revealedQuotes) revealed = false;
			draw();
		},
		destroy() {
			observer.disconnect();
			resizeObserver.disconnect();
			if (timer) clearTimeout(timer);
			node.removeEventListener('mousemove', hover);
			node.removeEventListener('mouseleave', leave);
			layer?.remove();
		}
	};
}
