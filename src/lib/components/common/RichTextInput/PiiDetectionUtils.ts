// Utility functions for PII detection and text analysis
import type { PiiEntity, ExtendedPiiEntity } from '$lib/types';

/**
 * Extract completed words from text (words followed by whitespace, punctuation, or end of text)
 */
export function extractCompletedWords(text: string): Set<string> {
	if (!text.trim()) return new Set();

	// More flexible approach: Find words with word boundaries OR at end of text
	const words = new Set<string>();

	// Method 1: Standard word boundary detection (for words in the middle)
	const boundaryMatches = text.match(/\b\w+\b/g) || [];
	boundaryMatches.forEach((word) => {
		if (word.length >= 3 && /^[a-zA-Z]+$/.test(word)) {
			words.add(word.toLowerCase());
		}
	});

	// Method 2: Handle words at the end of text (more lenient for real-time typing)
	// Look for word characters followed by non-word characters OR end of string
	const endWordMatches = text.match(/\b\w+(?=\W|$)/g) || [];
	endWordMatches.forEach((word) => {
		if (word.length >= 3 && /^[a-zA-Z]+$/.test(word)) {
			words.add(word.toLowerCase());
		}
	});

	return words;
}

/**
 * Find newly added COMPLETED words between two texts using proper diff detection
 */
export function findNewWords(previousText: string, currentText: string): string[] {
	// First try the fast approach for simple cases
	const previousWords = extractCompletedWords(previousText);
	const currentWords = extractCompletedWords(currentText);

	const newWords: string[] = [];
	for (const word of currentWords) {
		if (!previousWords.has(word)) {
			newWords.push(word);
		}
	}

	// If no new words detected but text length increased, try incremental approach
	if (newWords.length === 0 && currentText.length > previousText.length) {
		// Find the actual changed content using diff detection
		const addedContent = extractIncrementalContent(previousText, currentText);
		if (addedContent && addedContent.content.trim()) {
			// For real-time typing, also check if we're completing words in the surrounding context
			// Get a bit more context around the change to detect word completion
			const contextStart = Math.max(0, addedContent.offset - 10);
			const contextEnd = Math.min(
				currentText.length,
				addedContent.offset + addedContent.content.length + 10
			);

			const previousContext = previousText.substring(
				contextStart,
				Math.min(previousText.length, contextEnd)
			);
			const currentContext = currentText.substring(contextStart, contextEnd);

			// Check for newly completed words in the context
			const contextPreviousWords = extractCompletedWords(previousContext);
			const contextCurrentWords = extractCompletedWords(currentContext);

			for (const word of contextCurrentWords) {
				if (!contextPreviousWords.has(word)) {
					newWords.push(word);
				}
			}

			// Debug logging for word completion
			if (newWords.length > 0) {
				console.log('PiiDetectionExtension: 🔍 Found completed words in context', {
					addedContent: addedContent.content,
					contextPreviousWords: Array.from(contextPreviousWords),
					contextCurrentWords: Array.from(contextCurrentWords),
					newlyCompletedWords: newWords
				});
			}
		}
	}

	return newWords;
}

/**
 * Extract incremental content between two texts using advanced diff detection
 */
export function extractIncrementalContent(
	previousText: string,
	currentText: string
): { content: string; offset: number } | null {
	if (!previousText.trim()) {
		// If we had no previous text, all current text is new
		// Allow incremental for larger initial content (up to 5000 chars)
		return currentText.length > 5000 ? null : { content: currentText, offset: 0 };
	}

	// Calculate minimum change threshold based on document size
	// Extremely low threshold for real-time typing
	const minChangeThreshold = 1; // Always allow incremental detection for any single character change

	// Check if there's enough change to warrant incremental detection
	const lengthDifference = Math.abs(currentText.length - previousText.length);
	if (lengthDifference < minChangeThreshold) {
		return null; // Not enough change
	}

	// Find common prefix and suffix for better diff detection
	let commonPrefixEnd = 0;
	let commonSuffixLength = 0;
	const minLength = Math.min(previousText.length, currentText.length);

	// Find common prefix
	for (let i = 0; i < minLength; i++) {
		if (previousText[i] === currentText[i]) {
			commonPrefixEnd = i + 1;
		} else {
			break;
		}
	}

	// Find common suffix (working backwards)
	// Make sure we don't overlap with the prefix
	const maxSuffixCheck = minLength - commonPrefixEnd;
	for (let i = 0; i < maxSuffixCheck; i++) {
		const prevIndex = previousText.length - 1 - i;
		const currIndex = currentText.length - 1 - i;

		if (previousText[prevIndex] === currentText[currIndex]) {
			commonSuffixLength = i + 1;
		} else {
			break;
		}
	}

	// Calculate where the changed content ends (accounting for suffix)
	const commonSuffixStart = currentText.length - commonSuffixLength;

	// Extract the changed content (between prefix and suffix)
	const changedContent = currentText.substring(commonPrefixEnd, commonSuffixStart);

	// Calculate reasonable size limits based on document size
	const maxIncrementalSize = Math.max(2000, Math.min(10000, currentText.length * 0.3)); // 30% of doc, min 2k, max 10k
	const minIncrementalSize = 1; // Allow single character changes for real-time typing

	// Only use incremental if the changed content is a reasonable size
	if (
		changedContent.length >= minIncrementalSize &&
		changedContent.length <= maxIncrementalSize &&
		changedContent.trim()
	) {
		return { content: changedContent, offset: commonPrefixEnd };
	}

	// Additional fallback: ONLY for actual append operations (typing at the very end)
	// Check if the change is a true append (all previous content is unchanged)
	if (currentText.length > previousText.length && currentText.startsWith(previousText)) {
		const addedContent = currentText.substring(previousText.length);
		if (addedContent.length <= maxIncrementalSize && addedContent.trim()) {
			return { content: addedContent, offset: previousText.length };
		}
	}

	return null; // Fall back to full document detection
}

/**
 * Create a context snippet around a change for more meaningful PII detection
 * Always captures complete paragraphs for better context
 */
export function createContextSnippet(
	text: string,
	changeOffset: number,
	changeLength: number
): { content: string; offset: number } {
	const changeEnd = changeOffset + changeLength;

	// Find paragraph boundaries - paragraphs are separated by double newlines or single newlines with substantial content
	const paragraphSeparators = [
		/\n\s*\n/g, // Double newlines (clear paragraph breaks)
		/\n(?=\s*[A-Z])/g, // Single newline followed by capital letter (new sentence/paragraph)
		/\n(?=\s*\d+\.)/g, // Single newline followed by numbered list
		/\n(?=\s*[-•*])/g // Single newline followed by bullet points
	];

	// Find all paragraph break positions
	const breakPositions = new Set<number>([0, text.length]); // Always include start and end

	for (const regex of paragraphSeparators) {
		let match;
		regex.lastIndex = 0; // Reset regex
		while ((match = regex.exec(text)) !== null) {
			breakPositions.add(match.index + match[0].length);
		}
	}

	// Convert to sorted array
	const sortedBreaks = Array.from(breakPositions).sort((a, b) => a - b);

	// Find which paragraph contains the change
	let changeParagraphStart = 0;
	let changeParagraphEnd = text.length;

	for (let i = 0; i < sortedBreaks.length - 1; i++) {
		const start = sortedBreaks[i];
		const end = sortedBreaks[i + 1];

		if (changeOffset >= start && changeOffset < end) {
			changeParagraphStart = start;
			changeParagraphEnd = end;
			break;
		}
	}

	// Expand to include surrounding paragraphs for better context
	let contextStart = changeParagraphStart;
	let contextEnd = changeParagraphEnd;

	// Include previous paragraph if it exists and we're not at the start
	const prevParagraphIndex = sortedBreaks.indexOf(changeParagraphStart) - 1;
	if (prevParagraphIndex >= 0) {
		const prevParagraphStart = sortedBreaks[prevParagraphIndex];
		// Only include if the previous paragraph isn't too large
		if (changeParagraphStart - prevParagraphStart < 500) {
			contextStart = prevParagraphStart;
		}
	}

	// Include next paragraph if it exists and we're not at the end
	const nextParagraphIndex = sortedBreaks.indexOf(changeParagraphEnd) + 1;
	if (nextParagraphIndex < sortedBreaks.length) {
		const nextParagraphEnd = sortedBreaks[nextParagraphIndex];
		// Only include if the next paragraph isn't too large
		if (nextParagraphEnd - changeParagraphEnd < 500) {
			contextEnd = nextParagraphEnd;
		}
	}

	// Apply reasonable size limits to prevent massive context
	const maxContextSize = 1500; // Maximum characters for context
	if (contextEnd - contextStart > maxContextSize) {
		// If context is too large, prioritize the paragraph with the change
		const changeParagraphSize = changeParagraphEnd - changeParagraphStart;
		if (changeParagraphSize > maxContextSize) {
			// Even the single paragraph is too large, fall back to character-based approach
			const maxRadius = Math.floor(maxContextSize / 2);
			contextStart = Math.max(0, changeOffset - maxRadius);
			contextEnd = Math.min(text.length, changeEnd + maxRadius);
		} else {
			// Try to fit the change paragraph plus some surrounding content
			const remainingSpace = maxContextSize - changeParagraphSize;
			const beforeSpace = Math.floor(remainingSpace / 2);
			const afterSpace = remainingSpace - beforeSpace;

			contextStart = Math.max(0, changeParagraphStart - beforeSpace);
			contextEnd = Math.min(text.length, changeParagraphEnd + afterSpace);
		}
	}

	// Clean up the context boundaries to avoid cutting words
	if (contextStart > 0) {
		const nextSpace = text.indexOf(' ', contextStart);
		if (nextSpace !== -1 && nextSpace < changeOffset) {
			contextStart = nextSpace + 1;
		}
	}

	if (contextEnd < text.length) {
		const prevSpace = text.lastIndexOf(' ', contextEnd);
		if (prevSpace !== -1 && prevSpace > changeEnd) {
			contextEnd = prevSpace;
		}
	}

	const content = text.substring(contextStart, contextEnd).trim();

	console.log('PiiDetectionExtension: 📝 Created paragraph-aware context snippet', {
		changeOffset,
		changeLength,
		changeParagraphStart,
		changeParagraphEnd,
		contextStart,
		contextEnd,
		contextLength: content.length,
		includesPreviousParagraph: contextStart < changeParagraphStart,
		includesNextParagraph: contextEnd > changeParagraphEnd,
		paragraphsIncluded: content.split(/\n\s*\n/).length,
		contentPreview: content.length > 200 ? content.substring(0, 200) + '...' : content
	});

	return {
		content,
		offset: contextStart
	};
}

/**
 * Merge incremental PII entities with existing entities, avoiding duplicates
 */
export function mergeIncrementalEntities(
	existingEntities: ExtendedPiiEntity[],
	newEntities: PiiEntity[]
): ExtendedPiiEntity[] {
	const merged: ExtendedPiiEntity[] = [...existingEntities];

	newEntities.forEach((newEntity) => {
		const existingIndex = merged.findIndex((e) => e.label === newEntity.label);
		if (existingIndex >= 0) {
			// Update existing entity but preserve shouldMask state
			merged[existingIndex] = {
				...newEntity,
				shouldMask: merged[existingIndex].shouldMask
			};
		} else {
			// Add new entity with default masking enabled
			merged.push({ ...newEntity, shouldMask: true });
		}
	});

	return merged;
}

/**
 * Calculate smart debounce delay based on content significance
 */
export function getSmartDebounceDelay(
	newWords: string[],
	incrementalContent: string | null,
	baseDelay: number = 500
): number {
	// Factors that reduce delay (make detection faster):
	if (newWords.length > 10) return Math.max(baseDelay * 0.8, 400); // Faster for many new words
	if (incrementalContent && incrementalContent.length > 200) return Math.max(baseDelay * 0.9, 450); // Faster for large additions

	// Factors that increase delay (make detection slower):
	if (newWords.length <= 3) return baseDelay * 2; // Much slower for few words
	if (newWords.every((word) => word.length <= 4)) return baseDelay * 1.5; // Slower for short words

	return baseDelay; // Default delay
}

/**
 * Check if content has significant changes worthy of PII detection
 */
export function hasSignificantContent(newWords: string[]): boolean {
	// Filter out trivial content - require meaningful words
	const meaningfulWords = newWords.filter(
		(word) =>
			word.length >= 3 && // Require at least 3 characters
			/^[a-zA-Z]+$/.test(word) // AND pure alphabetic words (names, etc.)
	);

	return (
		meaningfulWords.length >= 1 || // At least one meaningful word
		newWords.length >= 2
	); // Or multiple words (even if short)
}

/**
 * Typing pause detection utility
 * Manages timer-based detection for catching missed changes after typing pauses
 * Only triggers after actual user keystrokes, not programmatic content changes
 */
export class TypingPauseDetector {
	private timer: NodeJS.Timeout | null = null;
	private lastApiCallText: string = '';
	private pauseThresholdMs: number = 1000; // 1 second default
	private lastUserKeystrokeTime: number = 0; // Track when user last typed
	private keystrokeTimeoutMs: number = 5000; // 5 seconds - only detect after recent user activity
	private recentTransactions: number[] = []; // Track transaction timestamps for rapid change detection
	private rapidChangeThresholdMs: number = 100; // Changes within 100ms are likely programmatic

	constructor(pauseThresholdMs: number = 1000, keystrokeTimeoutMs: number = 5000) {
		this.pauseThresholdMs = pauseThresholdMs;
		this.keystrokeTimeoutMs = keystrokeTimeoutMs;
	}

	/**
	 * Track a transaction to detect rapid changes (typical of programmatic loading)
	 */
	onTransaction(): boolean {
		const now = Date.now();

		// Clean up old transactions (keep only last 500ms)
		this.recentTransactions = this.recentTransactions.filter((time) => now - time < 500);

		// Add current transaction
		this.recentTransactions.push(now);

		// Check if we have multiple transactions in rapid succession
		const rapidTransactions = this.recentTransactions.filter(
			(time) => now - time < this.rapidChangeThresholdMs
		);
		const isRapidChange = rapidTransactions.length > 2; // More than 2 transactions in 100ms

		if (isRapidChange) {
			console.log('PiiDetectionExtension: 🚀 Rapid transactions detected (likely programmatic)', {
				recentTransactionsCount: this.recentTransactions.length,
				rapidTransactionsCount: rapidTransactions.length,
				rapidChangeThresholdMs: this.rapidChangeThresholdMs
			});
		}

		return isRapidChange;
	}

	/**
	 * Call this when a user keystroke is detected to mark user activity
	 */
	onUserKeystroke(): void {
		this.lastUserKeystrokeTime = Date.now();
		// Clear rapid transaction tracking when user types
		this.recentTransactions = [];
		console.log(
			'PiiDetectionExtension: 👤 User keystroke detected, activating typing pause detection'
		);
	}

	/**
	 * Call this on document changes - only activates pause timer if recent user activity
	 */
	onTextChange(
		currentText: string,
		onPauseDetected: (textDiff: { previous: string; current: string }) => void
	): void {
		// Clear existing timer
		if (this.timer) {
			clearTimeout(this.timer);
			this.timer = null;
		}

		// Only set timer if there was recent user keystroke activity
		const timeSinceLastKeystroke = Date.now() - this.lastUserKeystrokeTime;
		const hasRecentUserActivity = timeSinceLastKeystroke <= this.keystrokeTimeoutMs;

		if (hasRecentUserActivity) {
			console.log('PiiDetectionExtension: ⏰ Setting typing pause timer (recent user activity)', {
				timeSinceLastKeystroke,
				keystrokeTimeoutMs: this.keystrokeTimeoutMs
			});
			// Set new timer for pause detection
			this.timer = setTimeout(() => {
				this.handlePauseDetected(currentText, onPauseDetected);
			}, this.pauseThresholdMs);
		} else {
			console.log(
				'PiiDetectionExtension: ⏭️ Skipping typing pause timer (no recent user activity)',
				{
					timeSinceLastKeystroke,
					keystrokeTimeoutMs: this.keystrokeTimeoutMs,
					hasRecentUserActivity
				}
			);
		}
	}

	/**
	 * Call this when an API call is made to update the baseline
	 */
	onApiCallMade(textAtTimeOfCall: string): void {
		this.lastApiCallText = textAtTimeOfCall;
		console.log('PiiDetectionExtension: 📝 Updated API call baseline', {
			textLength: textAtTimeOfCall.length,
			textPreview: textAtTimeOfCall.substring(0, 100) + (textAtTimeOfCall.length > 100 ? '...' : '')
		});
	}

	/**
	 * Check if current text differs significantly from last API call
	 */
	hasSignificantTextDifference(currentText: string): boolean {
		if (!this.lastApiCallText) {
			// No previous API call, any text is significant
			return currentText.trim().length > 0;
		}

		// Check for length differences
		const lengthDiff = Math.abs(currentText.length - this.lastApiCallText.length);
		if (lengthDiff > 5) {
			// More than 5 characters different
			return true;
		}

		// Check for content differences using word comparison
		const previousWords = extractCompletedWords(this.lastApiCallText);
		const currentWords = extractCompletedWords(currentText);

		// Look for new words that weren't in the last API call
		for (const word of currentWords) {
			if (!previousWords.has(word)) {
				return true;
			}
		}

		// Look for removed words
		for (const word of previousWords) {
			if (!currentWords.has(word)) {
				return true;
			}
		}

		return false;
	}

	/**
	 * Force clear the timer (e.g., when component unmounts)
	 */
	cleanup(): void {
		if (this.timer) {
			clearTimeout(this.timer);
			this.timer = null;
		}
		// Clear transaction tracking
		this.recentTransactions = [];
		this.lastUserKeystrokeTime = 0;
		this.lastApiCallText = '';
	}

	/**
	 * Get current state for debugging
	 */
	getState(): {
		hasTimer: boolean;
		lastApiCallTextLength: number;
		pauseThresholdMs: number;
		lastUserKeystrokeTime: number;
		timeSinceLastKeystroke: number;
		hasRecentUserActivity: boolean;
		keystrokeTimeoutMs: number;
		recentTransactionsCount: number;
		rapidChangeThresholdMs: number;
	} {
		const timeSinceLastKeystroke = Date.now() - this.lastUserKeystrokeTime;
		const hasRecentUserActivity = timeSinceLastKeystroke <= this.keystrokeTimeoutMs;

		return {
			hasTimer: this.timer !== null,
			lastApiCallTextLength: this.lastApiCallText.length,
			pauseThresholdMs: this.pauseThresholdMs,
			lastUserKeystrokeTime: this.lastUserKeystrokeTime,
			timeSinceLastKeystroke,
			hasRecentUserActivity,
			keystrokeTimeoutMs: this.keystrokeTimeoutMs,
			recentTransactionsCount: this.recentTransactions.length,
			rapidChangeThresholdMs: this.rapidChangeThresholdMs
		};
	}

	private handlePauseDetected(
		currentText: string,
		onPauseDetected: (textDiff: { previous: string; current: string }) => void
	): void {
		console.log('PiiDetectionExtension: ⏱️ Typing pause detected, checking for changes', {
			pauseThresholdMs: this.pauseThresholdMs,
			currentTextLength: currentText.length,
			lastApiCallTextLength: this.lastApiCallText.length,
			hasSignificantDifference: this.hasSignificantTextDifference(currentText)
		});

		if (this.hasSignificantTextDifference(currentText)) {
			console.log(
				'PiiDetectionExtension: 🔍 Pause-triggered detection: text differs from last API call'
			);
			onPauseDetected({
				previous: this.lastApiCallText,
				current: currentText
			});
		} else {
			console.log(
				'PiiDetectionExtension: ⏭️ Pause detected but no significant changes, skipping API call'
			);
		}

		// Clear timer
		this.timer = null;
	}
}
