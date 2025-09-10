/**
 * Pure utility functions for PII text processing
 * Shared between PiiDetectionExtension and PiiModifierExtension
 */

import type { Node as ProseMirrorNode } from 'prosemirror-model';

/**
 * Generate unique ID for modifiers
 */
export function generateModifierId(): string {
	return `modifier_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Decode common HTML entities to plain characters for matching
 */
export function decodeHtmlEntities(text: string): string {
	if (!text) return text;
	// Fast path for numeric entities and a few named ones we often see
	const named: Record<string, string> = {
		'&amp;': '&',
		'&lt;': '<',
		'&gt;': '>',
		'&quot;': '"',
		'&#39;': "'",
		'&nbsp;': '\u00A0'
	};
	let result = text.replace(/&(amp|lt|gt|quot|#39);/g, (m) => named[m] || m);
	// Generic numeric (decimal or hex)
	result = result.replace(/&#(x?[0-9a-fA-F]+);/g, (_m, code) => {
		try {
			const num =
				code[0] === 'x' || code[0] === 'X' ? parseInt(code.slice(1), 16) : parseInt(code, 10);
			if (!isNaN(num)) return String.fromCharCode(num);
		} catch {}
		return _m;
	});
	return result;
}

/**
 * Count words in text for granular change detection
 */
export function countWords(text: string): number {
	if (!text.trim()) return 0;
	// Split on whitespace and filter empty strings
	return text
		.trim()
		.split(/\s+/)
		.filter((word) => word.length > 0).length;
}

/**
 * Extract individual words from text for comparison
 */
export function extractWords(text: string): Set<string> {
	if (!text.trim()) return new Set();
	return new Set(
		text
			.trim()
			.toLowerCase()
			.split(/\s+/)
			.filter((word) => word.length > 0)
			.map((word) => word.replace(/[.,!?;:"'()[\]{}]/g, '')) // Remove punctuation
			.filter((word) => word.length > 0)
	);
}

/**
 * Robust word detection using broader context (inspired by old findTokenizedWords)
 * This addresses boundary condition issues by using the selection text directly
 * with proper boundary verification
 */
export function findCompleteWordsRobust(
	doc: ProseMirrorNode,
	selectionFrom: number,
	selectionTo: number
): string {
	if (selectionFrom >= selectionTo) return '';

	// Get the selected text directly
	const selectedText = doc.textBetween(selectionFrom, selectionTo, '\n', '\0');
	if (!selectedText.trim()) return '';

	// For boundary checking, get 10 characters before and after (not just 1)
	const contextStart = Math.max(0, selectionFrom - 10);
	const contextEnd = Math.min(doc.content.size, selectionTo + 10);
	const fullContext = doc.textBetween(contextStart, contextEnd, '\n', '\0');

	// Find the selected text within the full context
	const selectedStartInContext = selectionFrom - contextStart;
	const selectedEndInContext = selectionTo - contextStart;

	// Check what comes before and after the selection in the context
	const charBefore = selectedStartInContext > 0 ? fullContext[selectedStartInContext - 1] : '';
	const charAfter =
		selectedEndInContext < fullContext.length ? fullContext[selectedEndInContext] : '';

	// Helper function for word character detection
	const isWordChar = (char: string) => /[a-zA-Z0-9äöüÄÖÜß'-]/.test(char);

	// Simple approach: if the selection has word boundaries, return it as-is
	// This handles "Medienaufteilung" where before is space and after is ":"
	const hasStartBoundary = !charBefore || !isWordChar(charBefore);
	const hasEndBoundary = !charAfter || !isWordChar(charAfter);

	if (hasStartBoundary && hasEndBoundary) {
		// The entire selection is a complete word/phrase, clean it up
		const cleanedText = selectedText.replace(/^[^\w]+|[^\w]+$/g, ''); // Remove leading/trailing non-word chars
		if (cleanedText.trim()) {
			return cleanedText;
		}
	}

	// Fallback: extract individual words from selection using regex
	const wordRegex = /\b[\w'-äöüÄÖÜß]+(?:['-][\w'-äöüÄÖÜß]+)*\b/g;
	const words: string[] = [];
	let match;

	while ((match = wordRegex.exec(selectedText)) !== null) {
		words.push(match[0]);
	}

	return words.join(' ');
}

/**
 * Check if a character is part of a word (using same pattern as WORD_TOKENIZER_PATTERN)
 */
function isWordChar(char: string): boolean {
	return /[\w'-äöüÄÖÜß]/.test(char || '');
}
