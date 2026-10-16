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
		'flex items-center justify-center rounded text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 bg-white/95 dark:bg-gray-850/95 focus-visible:outline focus-visible:outline-2';
	Object.assign(button.style, {
		position: 'absolute',
		width: '20px',
		height: '20px',
		pointerEvents: 'auto',
		cursor: 'help'
	});
	return button;
}

export function findTextRange(container: HTMLElement, quote: string): Range | null {
	const chars: Array<{ node: Text; offset: number; end: number }> = [];
	let text = '';
	const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
	let next: Node | null;
	while ((next = walker.nextNode())) {
		const node = next as Text;
		if (!node.parentElement?.closest('.textLayer')) continue;
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
