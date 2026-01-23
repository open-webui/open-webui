/**
 * KaTeX copy utilities - adapted from katex/contrib/copy-tex
 * Converts rendered KaTeX HTML back to LaTeX source when copying
 */

export interface CopyDelimiters {
	inline: [string, string];
	display: [string, string];
}

// Default delimiters: $...$ for inline, $$...$$ for display (Markdown style)
export const defaultCopyDelimiters: CopyDelimiters = {
	inline: ['$', '$'],
	display: ['$$', '$$']
};

/**
 * Replace .katex elements with their TeX source (<annotation> element).
 * Modifies fragment in-place.
 */
export function katexReplaceWithTex(
	fragment: DocumentFragment,
	copyDelimiters: CopyDelimiters = defaultCopyDelimiters
): DocumentFragment {
	// Find all .katex elements and process them
	const katexElements = fragment.querySelectorAll('.katex');

	for (const katexEl of katexElements) {
		// Check if this is display mode (parent has .katex-display class)
		const isDisplay = katexEl.parentElement?.classList.contains('katex-display');
		const delimiters = isDisplay ? copyDelimiters.display : copyDelimiters.inline;

		// Find the annotation element containing the LaTeX source
		const annotation = katexEl.querySelector('annotation[encoding="application/x-tex"]');
		if (annotation && annotation.textContent) {
			// Create a text node with the LaTeX source wrapped in delimiters
			const latexText = delimiters[0] + annotation.textContent + delimiters[1];
			const textNode = document.createTextNode(latexText);

			// Replace the entire .katex element with the text node
			katexEl.replaceWith(textNode);
		}
	}

	// Also handle .katex-display wrappers (for block formulas)
	const displayElements = fragment.querySelectorAll('.katex-display');
	for (const displayEl of displayElements) {
		// If there's still a .katex child that wasn't processed, handle it
		const katexChild = displayEl.querySelector('.katex');
		if (katexChild) {
			const annotation = katexChild.querySelector('annotation[encoding="application/x-tex"]');
			if (annotation && annotation.textContent) {
				const latexText = copyDelimiters.display[0] + annotation.textContent + copyDelimiters.display[1];
				const textNode = document.createTextNode(latexText);
				displayEl.replaceWith(textNode);
			}
		}
	}

	return fragment;
}

/**
 * Return the closest .katex or .katex-display element containing the given node.
 * Used to expand selection to include entire formula.
 */
export function closestKatex(node: Node): Element | null {
	const element = node instanceof Element ? node : node.parentElement;
	if (!element) return null;

	// Check for .katex-display first (block formula wrapper)
	const katexDisplay = element.closest('.katex-display');
	if (katexDisplay) return katexDisplay;

	// Then check for .katex (inline formula)
	return element.closest('.katex');
}
