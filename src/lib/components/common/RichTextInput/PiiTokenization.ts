/**
 * Text tokenization utilities for PII processing
 * Used for word boundary detection and selection expansion
 */

import type { Node as ProseMirrorNode } from 'prosemirror-model';

// Tokenizer pattern for broader context word detection
// Matches words, hyphenated terms, and international characters
export const WORD_TOKENIZER_PATTERN = /[\w'-äöüÄÖÜß]+(?=\b|\.)/g;

/**
 * Find all tokenized words touched by a text selection with broader context
 * This function expands the selection context and finds all words that
 * intersect with the given selection range.
 *
 * @param doc ProseMirror document
 * @param selectionFrom Start position of selection
 * @param selectionTo End position of selection
 * @returns Array of words with their positions
 */
export function findTokenizedWords(
	doc: ProseMirrorNode,
	selectionFrom: number,
	selectionTo: number
): Array<{ word: string; from: number; to: number }> {
	const words: Array<{ word: string; from: number; to: number }> = [];

	// Expand context to include words that might be partially selected
	const contextStart = Math.max(0, selectionFrom - 100); // 100 chars before
	const contextEnd = Math.min(doc.content.size, selectionTo + 100); // 100 chars after

	let contextText = '';

	// Build context text with position mapping
	const positionMap: number[] = []; // Maps context text index to document position

	doc.nodesBetween(contextStart, contextEnd, (node, nodePos) => {
		if (node.isText && node.text) {
			const nodeStart = nodePos;
			const nodeEnd = nodePos + node.text.length;
			const effectiveStart = Math.max(nodeStart, contextStart);
			const effectiveEnd = Math.min(nodeEnd, contextEnd);

			if (effectiveStart < effectiveEnd) {
				const startOffset = effectiveStart - nodeStart;
				const endOffset = effectiveEnd - nodeStart;
				const textSlice = node.text.substring(startOffset, endOffset);

				// Map each character position
				for (let i = 0; i < textSlice.length; i++) {
					positionMap.push(effectiveStart + i);
				}

				contextText += textSlice;
			}
		}
	});

	// Find all words using tokenizer
	let match;
	WORD_TOKENIZER_PATTERN.lastIndex = 0; // Reset regex

	while ((match = WORD_TOKENIZER_PATTERN.exec(contextText)) !== null) {
		const wordStart = match.index;
		const wordEnd = match.index + match[0].length;

		// Map back to document positions
		const docStart = positionMap[wordStart];
		// Fix: Ensure we don't access invalid array index
		const lastValidIndex = Math.min(wordEnd - 1, positionMap.length - 1);
		const docEnd = positionMap[lastValidIndex] + 1; // +1 because we want end position

		// Check if this word is "touched" by the selection (overlaps with selection range)
		if (
			docEnd > selectionFrom &&
			docStart < selectionTo &&
			docStart !== undefined &&
			docEnd !== undefined
		) {
			words.push({
				word: match[0],
				from: docStart,
				to: docEnd
			});
		}
	}

	// Remove duplicates and sort by position
	const uniqueWords = words
		.filter(
			(word, index, arr) => arr.findIndex((w) => w.from === word.from && w.to === word.to) === index
		)
		.sort((a, b) => a.from - b.from);

	return uniqueWords;
}
