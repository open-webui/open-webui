import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
import type { Node as ProseMirrorNode } from 'prosemirror-model';
import type { ExtendedPiiEntity } from '$lib/utils/pii';
import type { PiiEntity } from '$lib/apis/pii';
import { maskPiiText, updatePiiMasking } from '$lib/apis/pii';
import { debounce, PiiSessionManager } from '$lib/utils/pii';
import type { PiiModifier } from './PiiModifierExtension';
import { decodeHtmlEntities, countWords, extractWords } from './PiiTextUtils';
import { buildPositionMapping, type PositionMapping } from './PiiPositionMapping';
import { getPiiConfig, type PiiExtensionConfig } from './PiiExtensionConfig';
import { PiiPerformanceTracker } from './PiiPerformanceOptimizer';
import {
	extractCompletedWords,
	findNewWords,
	extractIncrementalContent,
	createContextSnippet,
	mergeIncrementalEntities,
	getSmartDebounceDelay,
	hasSignificantContent,
	TypingPauseDetector
} from './PiiDetectionUtils';

// Interface for PII entity occurrences
interface PiiOccurrence {
	start_idx: number;
	end_idx: number;
}

// PositionMapping interface moved to PiiPositionMapping.ts
// decodeHtmlEntities function moved to PiiTextUtils.ts

// Track text nodes and their content for reliable change detection
interface TextNodeInfo {
	nodeId: string; // Unique identifier for the node based on position and content
	content: string;
	startPos: number;
	endPos: number;
}

interface PiiDetectionState {
	entities: ExtendedPiiEntity[];
	positionMapping: PositionMapping | null;
	isDetecting: boolean;
	lastText: string;
	needsSync: boolean;
	userEdited?: boolean;
	textNodes: TextNodeInfo[]; // Track all text nodes in the document
	lastWordCount: number; // Track word count for more granular change detection
	cachedDecorations?: DecorationSet; // Cache decorations to prevent rebuilding on every keystroke
	lastDecorationHash?: string; // Hash to detect when decorations need updating
	dynamicallyEnabled?: boolean; // Track if PII detection is dynamically enabled/disabled
	temporarilyHiddenEntities: Set<string>; // Track entities temporarily hidden when modifiers are removed
	isFastMaskUpdate: boolean; // Track when we're performing a fast mask update to prevent regular detection
}

export interface PiiDetectionOptions {
	enabled: boolean;
	apiKey: string;
	conversationId?: string | undefined;
	getShouldMask?: () => boolean; // Dynamic function to get current masking state
	onPiiDetected?: (entities: ExtendedPiiEntity[], maskedText: string) => void;
	onPiiToggled?: (entities: ExtendedPiiEntity[]) => void;
	onPiiDetectionStateChanged?: (isDetecting: boolean) => void;
	debounceMs?: number;
	detectOnlyAfterUserEdit?: boolean; // If true, do not auto-detect on initial load; wait for user edits
	getMarkdownText?: () => string; // Function to get original markdown text instead of processed text
	useMarkdownForApi?: boolean; // If true, use markdown text for API calls instead of ProseMirror plain text
	disableModifierTriggeredDetection?: boolean; // If true, disable fast mask updates when modifiers change (for FileItemModal)
}

// Removed unused interfaces - let TypeScript infer TipTap command types

// Extract all text nodes from the document for change detection
function extractTextNodes(doc: ProseMirrorNode): TextNodeInfo[] {
	const textNodes: TextNodeInfo[] = [];
	let nodeCounter = 0;

	doc.nodesBetween(0, doc.content.size, (node, pos) => {
		if (node.isText && node.text) {
			const nodeId = `${pos}-${node.text.length}-${nodeCounter++}`;
			textNodes.push({
				nodeId,
				content: node.text,
				startPos: pos,
				endPos: pos + node.text.length
			});
		}
		return true;
	});

	return textNodes;
}

// countWords function moved to PiiTextUtils.ts

// extractWords function moved to PiiTextUtils.ts

// Note: Removed simple PII pattern pre-filtering as it was too simplistic
// and could miss real PII cases. Let the AI-powered API handle sophisticated detection.

// Check if new content has been added by comparing text nodes
function hasNewContent(
	previousNodes: TextNodeInfo[],
	currentNodes: TextNodeInfo[],
	previousWordCount: number,
	currentWordCount: number
): boolean {
	// Special case: if we had no content before and now have content, it's new
	// This handles initial content loading (e.g., in KnowledgeBase)
	if (previousWordCount === 0 && currentWordCount > 0) {
		console.log('PiiDetectionExtension: Initial content loaded', {
			wordCount: currentWordCount,
			nodeCount: currentNodes.length
		});
		return true;
	}

	// Quick check: if word count increased, we definitely have new content
	if (currentWordCount > previousWordCount) {
		console.log('PiiDetectionExtension: Word count increased', {
			previous: previousWordCount,
			current: currentWordCount
		});
		return true;
	}

	// If we have no previous nodes but have current nodes, it's new content
	if (previousNodes.length === 0 && currentNodes.length > 0) {
		console.log('PiiDetectionExtension: Content loaded into empty editor', {
			nodeCount: currentNodes.length
		});
		return true;
	}

	// If we have fewer nodes than before, content was removed (not new)
	if (currentNodes.length < previousNodes.length) {
		return false;
	}

	// If we have more nodes, we likely have new content
	if (currentNodes.length > previousNodes.length) {
		console.log('PiiDetectionExtension: New text nodes detected', {
			previous: previousNodes.length,
			current: currentNodes.length
		});
		return true;
	}

	// Special case: if content completely changed (like when switching files in KnowledgeBase)
	// Check if the majority of content is different
	if (previousNodes.length > 0 && currentNodes.length > 0) {
		let changedNodes = 0;
		const maxNodes = Math.max(previousNodes.length, currentNodes.length);

		for (let i = 0; i < maxNodes; i++) {
			const currentNode = currentNodes[i];
			const previousNode = previousNodes[i];

			if (!currentNode || !previousNode || currentNode.content !== previousNode.content) {
				changedNodes++;
			}
		}

		// If more than 50% of nodes changed, consider it new content
		const changeRatio = changedNodes / maxNodes;
		if (changeRatio > 0.5) {
			console.log('PiiDetectionExtension: Substantial content change detected', {
				changedNodes,
				totalNodes: maxNodes,
				changeRatio: Math.round(changeRatio * 100) + '%'
			});
			return true;
		}
	}

	// Same number of nodes - check if any node content has grown
	for (let i = 0; i < currentNodes.length; i++) {
		const currentNode = currentNodes[i];
		const previousNode = previousNodes[i];

		if (!previousNode) continue;

		// If current node content is longer and contains the previous content,
		// it's likely new content was added to this node
		if (
			currentNode.content.length > previousNode.content.length &&
			currentNode.content.includes(previousNode.content)
		) {
			console.log('PiiDetectionExtension: Node content expanded', {
				node: i,
				previous: previousNode.content.length,
				current: currentNode.content.length
			});
			return true;
		}

		// If node content changed completely, consider it new content
		if (currentNode.content !== previousNode.content && currentNode.content.trim() !== '') {
			console.log('PiiDetectionExtension: Node content changed', {
				node: i,
				previousLength: previousNode.content.length,
				currentLength: currentNode.content.length
			});
			return true;
		}
	}

	return false;
}

// Build position mapping between plain text and ProseMirror positions
// buildPositionMapping function moved to PiiPositionMapping.ts

// Convert PII entity positions from plain text to ProseMirror positions
// Preserves existing shouldMask state from current entities
// CRITICAL: Stores original plain text positions in originalOccurrences for API calls
function mapPiiEntitiesToProseMirror(
	entities: PiiEntity[],
	mapping: PositionMapping,
	existingEntities: ExtendedPiiEntity[] = [],
	defaultShouldMask: boolean = true
): ExtendedPiiEntity[] {
	return entities.map((entity) => {
		// Find existing entity with same label to preserve shouldMask state
		const existingEntity = existingEntities.find((existing) => existing.label === entity.label);
		const shouldMask = existingEntity?.shouldMask ?? defaultShouldMask; // Use defaultShouldMask if not found

		// Preserve original plain text positions for API calls
		const originalOccurrences = entity.occurrences.map((occurrence) => ({
			start_idx: occurrence.start_idx,
			end_idx: occurrence.end_idx
		}));

		return {
			...entity,
			shouldMask,
			originalOccurrences, // Store original plain text positions
			occurrences: entity.occurrences.map((occurrence: PiiOccurrence) => {
				const plainTextStart = occurrence.start_idx;
				const plainTextEnd = occurrence.end_idx;

				const proseMirrorStart =
					mapping.plainTextToProseMirror.get(plainTextStart) ?? plainTextStart;
				const proseMirrorEnd = mapping.plainTextToProseMirror.get(plainTextEnd - 1) ?? plainTextEnd;

				return {
					...occurrence,
					start_idx: proseMirrorStart,
					end_idx: proseMirrorEnd
				};
			})
		};
	});
}

// Validate entity positions and remove invalid ones
function validateAndFilterEntities(
	entities: ExtendedPiiEntity[],
	doc: ProseMirrorNode,
	mapping: PositionMapping
): ExtendedPiiEntity[] {
	return entities.filter((entity) => {
		// Check if entity still exists in the current text
		const entityText = decodeHtmlEntities(entity.raw_text).toLowerCase();
		const currentText = decodeHtmlEntities(mapping.plainText).toLowerCase();

		if (!currentText.includes(entityText)) {
			console.log(
				`PiiDetectionExtension: Entity "${entity.label}" no longer exists in text, removing`
			);
			return false;
		}

		// Validate all occurrences have valid positions
		const validOccurrences = entity.occurrences.filter((occurrence: PiiOccurrence) => {
			const { start_idx: from, end_idx: to } = occurrence;
			return from >= 0 && to <= doc.content.size && from < to;
		});

		if (validOccurrences.length === 0) {
			console.log(
				`PiiDetectionExtension: Entity "${entity.label}" has no valid positions, removing`
			);
			return false;
		}

		// Update entity with only valid occurrences
		entity.occurrences = validOccurrences;
		return true;
	});
}

// Resolve overlapping occurrences across all entities by preferring longer spans and stronger types
function resolveOverlaps(entities: ExtendedPiiEntity[], doc: ProseMirrorNode): ExtendedPiiEntity[] {
	interface SpanRef {
		entityIdx: number;
		occIdx: number;
		from: number;
		to: number;
		length: number;
		score: number;
	}
	// Entity priorities for overlap resolution
	const config = getPiiConfig();
	const typePriority = config.entityTypePriorities;

	const spans: SpanRef[] = [];
	entities.forEach((e, ei) => {
		(e.occurrences || []).forEach((o, oi) => {
			const length = o.end_idx - o.start_idx;
			const base = Math.max(length, (e.raw_text || '').length);
			const pri = typePriority[(e.type || '').toUpperCase()] || 1;
			// Penalty for very short/fragmentary entities
			const shortPenalty = (e.raw_text || '').trim().length <= 3 ? -5 : 0;
			spans.push({
				entityIdx: ei,
				occIdx: oi,
				from: o.start_idx,
				to: o.end_idx,
				length,
				score: base * 10 + pri + shortPenalty
			});
		});
	});

	spans.sort((a, b) => b.score - a.score);
	const kept: boolean[][] = entities.map((e) =>
		new Array((e.occurrences || []).length).fill(false)
	);
	const used: Array<{ from: number; to: number }> = [];

	for (const s of spans) {
		const overlaps = used.some((u) => s.from < u.to && s.to > u.from);
		if (!overlaps) {
			kept[s.entityIdx][s.occIdx] = true;
			used.push({ from: s.from, to: s.to });
		}
	}

	const result: ExtendedPiiEntity[] = [];
	entities.forEach((e, ei) => {
		const occ: PiiOccurrence[] = [] as any;
		(e.occurrences || []).forEach((o, oi) => {
			if (kept[ei][oi]) occ.push(o as any);
		});
		if (occ.length > 0) {
			result.push({ ...e, occurrences: occ });
		}
	});
	return result;
}

// Remap existing entities to current document positions
function remapEntitiesForCurrentDocument(
	entities: ExtendedPiiEntity[],
	mapping: PositionMapping,
	doc: ProseMirrorNode
): ExtendedPiiEntity[] {
	if (!entities.length || !mapping.plainText) {
		return [];
	}

	const remappedEntities = entities.map((entity) => {
		// Decode HTML entities in raw_text so matching aligns with rendered text
		let entityText = decodeHtmlEntities(entity.raw_text);

		// Normalize edges: strip table pipes, leading/trailing punctuation artifacts
		// Keep internal punctuation as-is
		entityText = entityText
			.normalize('NFKC')
			.replace(/^[\s\u00A0\t|:;.,\-_/\\]+/, '')
			.replace(/[\s\u00A0\t|:;.,\-_/\\]+$/, '');

		const searchSource = decodeHtmlEntities(mapping.plainText);

		// Build a whitespace-tolerant regex for the entity text
		const escaped = entityText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
		const pattern = escaped.replace(/\s+/g, '[\\s\\u00A0\\t]+');
		const regex = new RegExp(pattern, 'gi');

		const isAlnum = (ch: string) => /[A-Za-z0-9À-ÿ]/.test(ch);
		const startsAlpha = isAlnum(entityText[0] || '');
		const endsAlpha = isAlnum(entityText[entityText.length - 1] || '');

		const newOccurrences = [] as PiiOccurrence[];
		const newOriginalOccurrences = [] as { start_idx: number; end_idx: number }[];
		let match: RegExpExecArray | null;
		while ((match = regex.exec(searchSource)) !== null) {
			const foundIndex = match.index;
			const foundLength = match[0].length;
			const plainTextStart = foundIndex;
			const plainTextEnd = foundIndex + foundLength;

			// Enforce word boundaries to avoid mid-token matches
			const beforeChar = plainTextStart > 0 ? searchSource[plainTextStart - 1] : '';
			const afterChar = plainTextEnd < searchSource.length ? searchSource[plainTextEnd] : '';
			if (startsAlpha && beforeChar && isAlnum(beforeChar)) {
				continue; // starts inside a word
			}
			if (endsAlpha && afterChar && isAlnum(afterChar)) {
				continue; // ends inside a word
			}

			const proseMirrorStart = mapping.plainTextToProseMirror.get(plainTextStart);
			const proseMirrorEnd = mapping.plainTextToProseMirror.get(plainTextEnd - 1);

			if (proseMirrorStart !== undefined && proseMirrorEnd !== undefined) {
				const from = proseMirrorStart;
				const to = proseMirrorEnd + 1;
				if (from >= 0 && to <= doc.content.size && from < to) {
					// Store ProseMirror positions for editor use
					newOccurrences.push({ start_idx: from, end_idx: to });
					// Store original plain text positions for API calls
					newOriginalOccurrences.push({ start_idx: plainTextStart, end_idx: plainTextEnd });
				}
			}
		}

		return {
			...entity,
			occurrences: newOccurrences,
			// Preserve any existing originalOccurrences (e.g., from file state) if present
			originalOccurrences:
				entity.originalOccurrences && entity.originalOccurrences.length
					? entity.originalOccurrences
					: newOriginalOccurrences
		};
	});

	return remappedEntities.filter((entity) => entity.occurrences.length > 0);
}

// Sync plugin state with session manager
function syncWithSessionManager(
	conversationId: string | undefined,
	piiSessionManager: typeof PiiSessionManager.prototype,
	currentEntities: ExtendedPiiEntity[],
	mapping: PositionMapping,
	doc: ProseMirrorNode
): ExtendedPiiEntity[] {
	const tracker = PiiPerformanceTracker.getInstance();
	tracker.recordSyncOperation();
	// Get all entities from session manager using simplified display logic
	const sessionEntities = piiSessionManager.getEntitiesForDisplay(conversationId);

	// If session manager has fewer entities, some were removed
	if (sessionEntities.length < currentEntities.length) {
		// Don't filter entities if session manager is completely empty
		// This happens in new chat windows where session manager hasn't stored entities yet
		if (sessionEntities.length === 0) {
			// For new chats, just validate current entities without filtering
			return validateAndFilterEntities(currentEntities, doc, mapping);
		}

		// Filter current entities to only include those still in session manager
		const filteredEntities = currentEntities.filter((currentEntity) =>
			sessionEntities.find(
				(sessionEntity: ExtendedPiiEntity) => sessionEntity.label === currentEntity.label
			)
		);

		console.log('PiiDetectionExtension: Filtered entities:', {
			before: currentEntities.length,
			after: filteredEntities.length,
			removedCount: currentEntities.length - filteredEntities.length
		});

		// Validate positions for remaining entities
		return validateAndFilterEntities(filteredEntities, doc, mapping);
	}

	// Sync shouldMask state: Use session manager state as source of truth
	const updatedEntities = currentEntities.map((currentEntity) => {
		const sessionEntity = sessionEntities.find(
			(e: ExtendedPiiEntity) => e.label === currentEntity.label
		);
		if (sessionEntity) {
			// Use session manager's shouldMask state
			return {
				...currentEntity,
				shouldMask: sessionEntity.shouldMask ?? true
			};
		}
		return currentEntity;
	});

	return validateAndFilterEntities(updatedEntities, doc, mapping);
}

// Create decorations for PII entities and modifier-affected text
function createPiiDecorations(
	entities: ExtendedPiiEntity[],
	modifiers: PiiModifier[],
	doc: ProseMirrorNode
): Decoration[] {
	const decorations: Decoration[] = [];

	// Build a fresh mapping for this render pass
	const tracker = PiiPerformanceTracker.getInstance();
	const endTiming = tracker.startTiming();
	const mapping = buildPositionMapping(doc);
	const elapsed = endTiming();
	tracker.recordPositionRemap();
	if (elapsed > 10) {
		console.log(
			`PiiDetectionExtension: Slow position mapping in createPiiDecorations: ${elapsed.toFixed(1)}ms`
		);
	}

	const source = decodeHtmlEntities(mapping.plainText);

	// Helper for alnum
	const isAlnum = (ch: string) => /[A-Za-z0-9À-ÿ]/.test(ch);

	// Add PII entity decorations first (lower priority)
	type RawSpan = {
		type: string;
		label: string;
		shouldMask: boolean;
		from: number;
		to: number;
		entityIndex: number;
		occurrenceIndex: number;
	};
	const rawSpans: RawSpan[] = [];

	entities.forEach((entity, entityIndex) => {
		(entity.occurrences || []).forEach((occ, occurrenceIndex) => {
			const from = occ.start_idx;
			const to = occ.end_idx;
			if (from >= 0 && to <= doc.content.size && from < to) {
				rawSpans.push({
					type: entity.type,
					label: entity.label,
					shouldMask: entity.shouldMask ?? true,
					from,
					to,
					entityIndex,
					occurrenceIndex
				});
			}
		});
	});

	// Sort for stable rendering; do NOT merge spans to preserve indices for toggling
	rawSpans.sort((a, b) => (a.from === b.from ? a.to - b.to : a.from - b.from));
	rawSpans.forEach((span) => {
		const maskingClass = span.shouldMask ? 'pii-masked' : 'pii-unmasked';
		// Get the actual text content from the document for this span
		const spanText = doc.textBetween(span.from, span.to, '\n', '\0');
		decorations.push(
			Decoration.inline(span.from, span.to, {
				class: `pii-highlight ${maskingClass}`,
				'data-pii-type': span.type,
				'data-pii-label': span.label,
				'data-pii-text': spanText || '',
				'data-pii-occurrence': String(span.occurrenceIndex),
				'data-should-mask': span.shouldMask.toString(),
				'data-entity-index': String(span.entityIndex)
			})
		);
	});

	// Add modifier decorations using entity-based matching and fallback to text matching
	// Track applied ranges to prevent duplicates
	const appliedRanges = new Set<string>();

	(modifiers || []).forEach((modifier, modifierIndex) => {
		let decorationCreated = false;

		// Strategy 1: Try to find matching PII entity by text content
		// This handles cases where the modifier was created from an existing PII highlight
		entities.forEach((entity, entityIndex) => {
			entity.occurrences?.forEach((occurrence, occurrenceIndex) => {
				// Create range key to prevent duplicate decorations
				const rangeKey = `${occurrence.start_idx}-${occurrence.end_idx}-${modifier.id}`;
				if (appliedRanges.has(rangeKey)) return;

				// Get the actual text content from the document at this entity's position
				const entityText = doc
					.textBetween(occurrence.start_idx, occurrence.end_idx, '\n', '\0')
					.trim();

				// Check if this entity's text matches the modifier's entity text
				if (entityText.toLowerCase() === modifier.entity.toLowerCase()) {
					const decorationClass =
						modifier.action === 'string-mask'
							? 'pii-modifier-highlight pii-modifier-mask'
							: 'pii-modifier-highlight pii-modifier-ignore';

					decorations.push(
						Decoration.inline(occurrence.start_idx, occurrence.end_idx, {
							class: decorationClass,
							'data-modifier-entity': modifier.entity,
							'data-modifier-action': modifier.action,
							'data-modifier-type': modifier.type || '',
							'data-modifier-id': modifier.id,
							style: 'z-index: 10; position: relative;'
						})
					);
					appliedRanges.add(rangeKey);
					decorationCreated = true;
				}
			});
		});

		// Strategy 2: Fallback to plain text matching if no entity match found
		if (!decorationCreated) {
			// Normalize modifier entity
			let text = decodeHtmlEntities(modifier.entity || '');
			text = text
				.normalize('NFKC')
				.replace(/^[\s\u00A0\t|:;.,\-_/\\]+/, '')
				.replace(/[\s\u00A0\t|:;.,\-_/\\]+$/, '');
			if (!text) return;

			const escaped = text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			const pattern = escaped.replace(/\s+/g, '[\s\u00A0\t]+');
			const regex = new RegExp(pattern, 'gi');

			const startsAlpha = isAlnum(text[0] || '');
			const endsAlpha = isAlnum(text[text.length - 1] || '');

			// Helper: tolerant mapping from plain index to PM position
			const mapStartInRange = (startIdx: number, endIdx: number): number | undefined => {
				// Find first mappable plain index within [startIdx, endIdx)
				for (let i = startIdx; i < endIdx; i++) {
					const pm = mapping.plainTextToProseMirror.get(i);
					if (pm !== undefined) return pm;
				}
				return undefined;
			};
			const mapEndInRange = (startIdx: number, endIdx: number): number | undefined => {
				// Find last mappable plain index within [startIdx, endIdx)
				for (let i = endIdx - 1; i >= startIdx; i--) {
					const pm = mapping.plainTextToProseMirror.get(i);
					if (pm !== undefined) return pm;
				}
				return undefined;
			};

			let match: RegExpExecArray | null;
			while ((match = regex.exec(source)) !== null) {
				const start = match.index;
				const end = start + match[0].length;
				const before = start > 0 ? source[start - 1] : '';
				const after = end < source.length ? source[end] : '';
				if (startsAlpha && before && isAlnum(before)) continue;
				if (endsAlpha && after && isAlnum(after)) continue;

				const pmStart = mapStartInRange(start, end);
				const pmEnd = mapEndInRange(start, end);
				if (pmStart === undefined || pmEnd === undefined) continue;
				const from = pmStart;
				const to = pmEnd + 1;
				if (!(from >= 0 && to <= doc.content.size && from < to)) continue;

				// Check for duplicate ranges in fallback strategy too
				const rangeKey = `${from}-${to}-${modifier.id}`;
				if (appliedRanges.has(rangeKey)) continue;

				const decorationClass =
					modifier.action === 'string-mask'
						? 'pii-modifier-highlight pii-modifier-mask'
						: 'pii-modifier-highlight pii-modifier-ignore';

				decorations.push(
					Decoration.inline(from, to, {
						class: decorationClass,
						'data-modifier-entity': modifier.entity,
						'data-modifier-action': modifier.action,
						'data-modifier-type': modifier.type || '',
						'data-modifier-id': modifier.id,
						style: 'z-index: 10; position: relative;'
					})
				);
				appliedRanges.add(rangeKey);
				decorationCreated = true;
			}
		}
	});

	return decorations;
}

const piiDetectionPluginKey = new PluginKey<PiiDetectionState>('piiDetection');

// Export the plugin key so other extensions can communicate with this extension
export { piiDetectionPluginKey };

export const PiiDetectionExtension = Extension.create<PiiDetectionOptions>({
	name: 'piiDetection',

	addOptions() {
		return {
			enabled: false,
			apiKey: '',
			conversationId: '',
			getShouldMask: () => true, // Default to masked for backward compatibility
			onPiiDetected: undefined,
			onPiiToggled: undefined,
			onPiiDetectionStateChanged: undefined,
			debounceMs: getPiiConfig().timing.defaultDebounceMs,
			detectOnlyAfterUserEdit: false,
			getMarkdownText: undefined,
			useMarkdownForApi: false,
			disableModifierTriggeredDetection: false
		};
	},

	addProseMirrorPlugins() {
		const options = this.options;
		const { enabled, apiKey, onPiiDetected, debounceMs } = options;

		if (!enabled || !apiKey) {
			return [];
		}

		console.log('PiiDetectionExtension: initialized', {
			conversationId: options.conversationId,
			enabled,
			hasApiKey: !!apiKey,
			debounceMs: debounceMs || getPiiConfig().timing.defaultDebounceMs
		});

		const piiSessionManager = PiiSessionManager.getInstance();
		piiSessionManager.setApiKey(apiKey);

		// Initialize typing pause detector for catching missed changes after typing pauses
		const typingPauseDetector = new TypingPauseDetector(1000); // 1 second pause threshold

		// Store detector reference for command access
		if (this.editor) {
			(this.editor as any)._typingPauseDetector = typingPauseDetector;
		}

		// Handle pause-triggered detection
		const handlePauseTriggeredDetection = (textDiff: { previous: string; current: string }) => {
			console.log('PiiDetectionExtension: ⏰ Pause-triggered detection activated', {
				previousLength: textDiff.previous.length,
				currentLength: textDiff.current.length,
				lengthDiff: textDiff.current.length - textDiff.previous.length
			});

			// Use the full text for pause-triggered detection (more comprehensive than incremental)
			performPiiDetection(textDiff.current);
		};

		const performPiiDetection = async (plainText: string) => {
			if (!plainText.trim()) {
				return;
			}

			// Prevent race conditions - check if detection is already running
			const editorView = this.editor?.view;
			const currentState = editorView?.state ? plugin.getState(editorView.state) : null;
			if (currentState?.isDetecting) {
				console.log('PiiDetectionExtension: ⚠️ Full detection skipped - already detecting');
				return;
			}

			try {
				// Set detecting state to true at the start
				if (editorView) {
					const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'SET_DETECTING',
						isDetecting: true
					});
					editorView.dispatch(tr);
				}

				const knownEntities = piiSessionManager.getKnownEntitiesForApi(options.conversationId);

				const modifiers = piiSessionManager.getModifiersForApi(options.conversationId);

				// Determine text to send to API
				let textForApi = plainText;
				let isUsingMarkdown = false;

				if (options.useMarkdownForApi && options.getMarkdownText) {
					const markdownText = options.getMarkdownText();
					if (markdownText && markdownText.trim()) {
						textForApi = markdownText;
						isUsingMarkdown = true;
						console.log('PiiDetectionExtension: Using markdown text for API', {
							markdownLength: markdownText.length,
							proseMirrorLength: plainText.length,
							difference: markdownText.length - plainText.length
						});
					}
				}

				// Track API performance
				const tracker = PiiPerformanceTracker.getInstance();
				const apiStartTime = performance.now();
				tracker.recordApiCall();

				const response = await maskPiiText(
					apiKey,
					[textForApi],
					knownEntities,
					modifiers,
					false,
					false
				);

				// Track this API call for pause detection
				typingPauseDetector.onApiCallMade(plainText);

				// Track API completion
				const apiElapsed = performance.now() - apiStartTime;
				if (apiElapsed > 1000) {
					console.log(
						`PiiDetectionExtension: Slow full API call: ${apiElapsed.toFixed(0)}ms, text length: ${plainText.length}`
					);
				}

				if (response.pii && response.pii[0] && response.pii[0].length > 0) {
					const editorView = this.editor?.view;
					const state = piiDetectionPluginKey.getState(editorView?.state);

					if (!editorView || !state?.positionMapping) {
						console.warn('PiiDetectionExtension: No editor view or position mapping available');
						return;
					}

					// CRITICAL FIX: Load conversation entities for cross-message shouldMask persistence
					// This ensures that entities unmasked in previous messages stay unmasked in new messages
					// For new chats, load from temporary state instead of empty array
					const conversationEntities = piiSessionManager.getEntitiesForDisplay(
						options.conversationId
					);

					// CRITICAL FIX: Merge plugin state + conversation state for complete context
					// Plugin state takes precedence (for same-message interactions)
					// Conversation state provides fallback (for cross-message persistence)
					const pluginEntities = state.entities || [];
					const existingEntitiesForMapping = [...pluginEntities];

					// Add conversation entities that aren't already in plugin state
					conversationEntities.forEach((convEntity) => {
						if (!pluginEntities.find((pluginEntity) => pluginEntity.label === convEntity.label)) {
							existingEntitiesForMapping.push(convEntity);
						}
					});

					console.log('PiiDetectionExtension: Using existing entities for mapping:', {
						pluginEntities: pluginEntities.length,
						conversationEntities: conversationEntities.length,
						totalForMapping: existingEntitiesForMapping.length,
						labelsCount: existingEntitiesForMapping.length,
						usingMarkdown: isUsingMarkdown
					});

					let mappedEntities: ExtendedPiiEntity[];

					if (isUsingMarkdown) {
						// When using markdown, we need to remap entities from markdown positions to ProseMirror positions
						// This is more complex but provides better accuracy
						console.warn('PiiDetectionExtension: Markdown mode - positions may need remapping');

						// For now, use the remap function which will try to find the entities in the current document
						const remappedEntities = remapEntitiesForCurrentDocument(
							response.pii[0],
							state.positionMapping,
							editorView.state.doc
						);

						mappedEntities = remappedEntities.map((entity) => ({
							...entity,
							shouldMask:
								existingEntitiesForMapping.find((e) => e.label === entity.label)?.shouldMask ??
								(options.getShouldMask ? options.getShouldMask() : true)
						}));
					} else {
						// Standard position mapping from ProseMirror plain text
						mappedEntities = mapPiiEntitiesToProseMirror(
							response.pii[0],
							state.positionMapping,
							existingEntitiesForMapping,
							options.getShouldMask ? options.getShouldMask() : true
						);
					}

					// CRITICAL FIX: Sync the mapped entities back to session manager
					// This ensures session manager has the correct shouldMask states from plugin
					if (options.conversationId) {
						piiSessionManager.setConversationWorkingEntitiesWithMaskStates(
							options.conversationId,
							response.pii[0]
						);
					} else {
						// For new chats, use temporary state
						if (!piiSessionManager.isTemporaryStateActive()) {
							piiSessionManager.activateTemporaryState();
						}
						piiSessionManager.setTemporaryStateEntities(response.pii[0]);
					}

					const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'UPDATE_ENTITIES',
						entities: response.pii[0],
						clearTemporarilyHidden: true // Clear hidden entities when new detection results come in from user activity
					});

					editorView.dispatch(tr);

					if (onPiiDetected) {
						onPiiDetected(response.pii[0], response.text[0]);
					}
				}
			} catch (error) {
				console.error('PiiDetectionExtension: PII detection failed:', error);
			} finally {
				// Set detecting state to false when done (success or error)
				const editorView = this.editor?.view;
				if (editorView) {
					const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'SET_DETECTING',
						isDetecting: false
					});
					editorView.dispatch(tr);
				}
			}
		};

		const performFastMaskUpdate = async (
			plainText: string,
			currentEntities: ExtendedPiiEntity[]
		) => {
			if (!plainText.trim() || !currentEntities.length) {
				console.log('PiiDetectionExtension: Fast mask update skipped - no text or entities');
				return;
			}

			// Prevent race conditions - check if detection is already running
			const editorView = this.editor?.view;
			const currentState = editorView?.state ? plugin.getState(editorView.state) : null;
			if (currentState?.isDetecting) {
				console.log('PiiDetectionExtension: ⚠️ Fast mask update skipped - already detecting');
				return;
			}

			try {
				// Set detecting state to true at the start
				if (editorView) {
					const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'SET_DETECTING',
						isDetecting: true
					});
					editorView.dispatch(tr);
				}

				const modifiers = piiSessionManager.getModifiersForApi(options.conversationId);

				// Determine text to send to API
				let textForApi = plainText;
				let isUsingMarkdown = false;

				if (options.useMarkdownForApi && options.getMarkdownText) {
					const markdownText = options.getMarkdownText();
					if (markdownText && markdownText.trim()) {
						textForApi = markdownText;
						isUsingMarkdown = true;
						console.log('PiiDetectionExtension: Using markdown text for fast mask update', {
							markdownLength: markdownText.length,
							proseMirrorLength: plainText.length
						});
					}
				}

				// Convert ExtendedPiiEntity[] to PiiEntity[] for API call
				// IMPORTANT: Occurrence positions must align with the text sent to the API.
				// If using markdown mode, recompute occurrences against markdown text.
				const computeOccurrencesInText = (
					text: string,
					needle: string
				): Array<{ start_idx: number; end_idx: number }> => {
					if (!text || !needle) return [];
					// Decode any entities and normalize whitespace tolerance
					let target = decodeHtmlEntities(needle)
						.normalize('NFKC')
						.replace(/^[\s\u00A0\t|:;.,\-_/\\]+/, '')
						.replace(/[\s\u00A0\t|:;.,\-_/\\]+$/, '');
					if (!target) return [];

					const haystack = decodeHtmlEntities(text);
					const escaped = target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
					const pattern = escaped.replace(/\s+/g, '[\\s\\u00A0\\t]+');
					const regex = new RegExp(pattern, 'gi');

					const isAlnum = (ch: string) => /[A-Za-z0-9À-ÿ]/.test(ch);
					const startsAlpha = isAlnum(target[0] || '');
					const endsAlpha = isAlnum(target[target.length - 1] || '');

					const results: Array<{ start_idx: number; end_idx: number }> = [];
					let m: RegExpExecArray | null;
					while ((m = regex.exec(haystack)) !== null) {
						const start = m.index;
						const end = start + m[0].length;
						const before = start > 0 ? haystack[start - 1] : '';
						const after = end < haystack.length ? haystack[end] : '';
						if (startsAlpha && before && isAlnum(before)) continue;
						if (endsAlpha && after && isAlnum(after)) continue;
						results.push({ start_idx: start, end_idx: end });
					}
					return results;
				};

				const piiEntities: PiiEntity[] = currentEntities.map((entity) => {
					let occurrences = entity.originalOccurrences || entity.occurrences;
					if (isUsingMarkdown) {
						occurrences = computeOccurrencesInText(
							textForApi,
							entity.raw_text || entity.text || ''
						);
					}
					return {
						id: entity.id,
						type: entity.type,
						label: entity.label,
						text: entity.text,
						raw_text: entity.raw_text,
						occurrences
					};
				});

				// Track API performance
				const tracker = PiiPerformanceTracker.getInstance();
				const apiStartTime = performance.now();
				tracker.recordApiCall();

				console.log('PiiDetectionExtension: 🚀 Using fast mask-update API', {
					textLength: textForApi.length,
					entitiesCount: piiEntities.length,
					modifiersCount: modifiers.length,
					usingMarkdown: isUsingMarkdown
				});

				const response = await updatePiiMasking(apiKey, textForApi, piiEntities, modifiers, false);

				// Track API completion
				const apiElapsed = performance.now() - apiStartTime;
				console.log(
					`PiiDetectionExtension: Fast mask-update API call: ${apiElapsed.toFixed(0)}ms, text length: ${plainText.length}`
				);

				if (response.pii && response.pii.length > 0) {
					const editorView = this.editor?.view;
					const state = piiDetectionPluginKey.getState(editorView?.state);

					if (!editorView || !state?.positionMapping) {
						console.warn('PiiDetectionExtension: No editor view or position mapping available');
						return;
					}

					// Load conversation entities for cross-message shouldMask persistence
					const conversationEntities = piiSessionManager.getEntitiesForDisplay(
						options.conversationId
					);

					// Merge plugin state + conversation state for complete context
					const pluginEntities = state.entities || [];
					const existingEntitiesForMapping = [...pluginEntities];

					// Add conversation entities that aren't already in plugin state
					conversationEntities.forEach((convEntity) => {
						if (!pluginEntities.find((pluginEntity) => pluginEntity.label === convEntity.label)) {
							existingEntitiesForMapping.push(convEntity);
						}
					});

					// Pass merged entities to preserve shouldMask state across messages
					const mappedEntities = mapPiiEntitiesToProseMirror(
						response.pii,
						state.positionMapping,
						existingEntitiesForMapping,
						options.getShouldMask ? options.getShouldMask() : true
					);

					// CRITICAL FIX: Sync the mapped entities back to session manager with shouldMask states preserved
					// This ensures session manager has the correct shouldMask states from plugin
					if (options.conversationId) {
						piiSessionManager.setConversationWorkingEntitiesWithMaskStates(
							options.conversationId,
							mappedEntities
						);
					} else {
						// For new chats, use temporary state
						if (!piiSessionManager.isTemporaryStateActive()) {
							piiSessionManager.activateTemporaryState();
						}
						piiSessionManager.setTemporaryStateEntities(mappedEntities);
					}

					// Update plugin state via transaction
					const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'UPDATE_ENTITIES',
						entities: response.pii,
						clearTemporarilyHidden: true // Clear hidden entities when new detection results come in from user activity
					});
					editorView.dispatch(tr);

					// Notify parent component
					if (onPiiDetected) {
						onPiiDetected(response.pii, response.text);
					}

					// Clear the fast mask update flag after successful completion
					// Use requestAnimationFrame to ensure all DOM updates and reflows are complete
					requestAnimationFrame(() => {
						requestAnimationFrame(() => {
							if (editorView) {
								const clearFlagTr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
									type: 'CLEAR_FAST_MASK_UPDATE_FLAG'
								});
								editorView.dispatch(clearFlagTr);
							}
						});
					});
				}
			} catch (error) {
				console.error('PII fast mask update failed:', error);
				// Fallback to regular detection if fast update fails
				console.log('PiiDetectionExtension: Falling back to regular detection');
				performPiiDetection(plainText);

				// Clear the fast mask update flag after fallback
				if (editorView) {
					const clearFlagTr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'CLEAR_FAST_MASK_UPDATE_FLAG'
					});
					editorView.dispatch(clearFlagTr);
				}
			} finally {
				// Always clear detecting state
				if (editorView) {
					const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'SET_DETECTING',
						isDetecting: false
					});
					editorView.dispatch(tr);
				}

				// Notify parent component of state change
				if (options.onPiiDetectionStateChanged) {
					options.onPiiDetectionStateChanged(false);
				}
			}
		};

		// Smart debouncing based on content significance
		const getSmartDebounceDelay = (
			newWords: string[],
			incrementalContent: string | null
		): number => {
			const config = getPiiConfig();
			const baseDelay = debounceMs || config.timing.defaultDebounceMs;

			// Factors that reduce delay (make detection faster):
			if (newWords.length > config.textProcessing.manyWordsThreshold)
				return Math.max(
					baseDelay * config.timing.smartDebounce.fastMultiplier,
					config.timing.smartDebounce.minDelayMs
				);
			if (
				incrementalContent &&
				incrementalContent.length > config.textProcessing.largeContentThreshold
			)
				return Math.max(baseDelay * 0.9, 450); // Faster for large additions

			// Factors that increase delay (make detection slower):
			if (newWords.length <= config.textProcessing.fewWordsThreshold)
				return baseDelay * config.timing.smartDebounce.slowMultiplier;
			if (newWords.every((word) => word.length <= config.textProcessing.shortWordThreshold))
				return baseDelay * config.timing.smartDebounce.shortWordMultiplier;

			return baseDelay; // Default delay
		};

		// Debounced version with smart timing
		let smartDebouncedDetection: (text: string) => void;
		let smartDebouncedIncrementalDetection: (incrementalText: string, fullText: string) => void;

		// Incremental detection for better performance with large documents
		const performIncrementalPiiDetection = async (
			incrementalText: string,
			fullText: string,
			incrementalOffset?: number
		) => {
			if (!incrementalText.trim()) {
				return;
			}

			// Prevent race conditions - check if detection is already running
			const editorView = this.editor?.view;
			const currentState = editorView?.state ? plugin.getState(editorView.state) : null;
			if (currentState?.isDetecting) {
				console.log('PiiDetectionExtension: ⚠️ Incremental detection skipped - already detecting');
				return;
			}

			try {
				// Set detecting state to true at the start
				if (editorView) {
					const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'SET_DETECTING',
						isDetecting: true
					});
					editorView.dispatch(tr);
				}

				const knownEntities = piiSessionManager.getKnownEntitiesForApi(options.conversationId);
				const modifiers = piiSessionManager.getModifiersForApi(options.conversationId);

				// Determine text to send to API for incremental detection
				let textForApi = incrementalText;
				let isUsingMarkdown = false;

				// Note: For incremental detection, we typically still use the incremental snippet
				// even in markdown mode, as the context snippet is already extracted from markdown
				if (options.useMarkdownForApi && options.getMarkdownText && incrementalText === fullText) {
					// Only use full markdown if we're analyzing the full text
					const markdownText = options.getMarkdownText();
					if (markdownText && markdownText.trim()) {
						textForApi = markdownText;
						isUsingMarkdown = true;
					}
				}

				// Detect PII in the incremental content only
				console.log('PiiDetectionExtension: Analyzing context snippet for PII', {
					contextSnippetLength: incrementalText.length,
					fullLength: fullText.length,
					contextOffset: incrementalOffset || 0,
					contextLength: incrementalText.length,
					usingMarkdown: isUsingMarkdown
				});

				// Track incremental API performance
				const tracker = PiiPerformanceTracker.getInstance();
				const apiStartTime = performance.now();
				tracker.recordApiCall();

				const response = await maskPiiText(
					apiKey,
					[textForApi],
					knownEntities,
					modifiers,
					false,
					false
				);

				// Track this API call for pause detection (use full text as baseline, not just snippet)
				typingPauseDetector.onApiCallMade(fullText);

				// Track incremental API completion
				const apiElapsed = performance.now() - apiStartTime;
				if (apiElapsed > 500) {
					console.log(
						`PiiDetectionExtension: Slow incremental API call: ${apiElapsed.toFixed(0)}ms, text length: ${incrementalText.length}`
					);
				}

				if (response.pii && response.pii[0] && response.pii[0].length > 0) {
					console.log(
						'PiiDetectionExtension: ✅ Found PII in context snippet, processing with positioning adjustment',
						{
							piiEntitiesFound: response.pii[0].length,
							contextSnippetLength: incrementalText.length,
							contextOffset: incrementalOffset || 0,
							avoidedFullDetection: true
						}
					);

					// Calculate offset to map incremental positions to full document positions
					// Use provided offset if available, otherwise try to find it
					const calculatedOffset =
						incrementalOffset !== undefined ? incrementalOffset : fullText.indexOf(incrementalText);

					if (calculatedOffset >= 0) {
						// Adjust PII entity positions to match full document
						const adjustedEntities = response.pii[0].map((entity) => ({
							...entity,
							occurrences: entity.occurrences.map((occ) => ({
								start_idx: occ.start_idx + calculatedOffset,
								end_idx: occ.end_idx + calculatedOffset
							}))
						}));

						// Merge incremental results with existing entities
						const existingEntities = piiSessionManager.getEntitiesForDisplay(
							options.conversationId
						);
						const mergedEntities = mergeIncrementalEntities(existingEntities, adjustedEntities);
						piiSessionManager.setConversationWorkingEntitiesWithMaskStates(
							options.conversationId,
							mergedEntities
						);

						// Update plugin state with all merged entities (not just incremental)
						if (editorView) {
							const state = piiDetectionPluginKey.getState(editorView.state);
							if (state?.positionMapping) {
								// Map all merged entities to ProseMirror positions, preserving shouldMask states
								const allMappedEntities = mapPiiEntitiesToProseMirror(
									mergedEntities,
									state.positionMapping,
									state.entities, // Use existing plugin entities for shouldMask preservation
									options.getShouldMask ? options.getShouldMask() : true
								);

								const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
									type: 'UPDATE_ENTITIES',
									entities: allMappedEntities, // Send ALL entities to prevent clearing
									isIncrementalUpdate: true, // Mark as incremental to preserve existing entities
									clearTemporarilyHidden: true // Clear hidden entities when new detection results come in from user activity
								});
								editorView.dispatch(tr);

								// Notify parent component with all entities
								if (onPiiDetected) {
									onPiiDetected(allMappedEntities, fullText);
								}
							}
						}

						console.log(
							'PiiDetectionExtension: 🎉 Incremental detection completed successfully - saved API bandwidth!'
						);
					} else {
						console.log(
							'PiiDetectionExtension: ⚠️ Could not find context snippet in full text, falling back to full detection'
						);
						await performPiiDetection(fullText);
					}
				} else {
					console.log(
						'PiiDetectionExtension: ✅ No PII found in context snippet - context-aware detection complete'
					);
				}

				// Always update detecting state
				if (editorView) {
					const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'SET_DETECTING',
						isDetecting: false
					});
					editorView.dispatch(tr);
				}
			} catch (error) {
				console.error(
					'PiiDetectionExtension: Context snippet detection failed, falling back to full detection:',
					error
				);
				// Fall back to full detection on error
				await performPiiDetection(fullText);
			}
		};

		// Initialize with default debounce, will be updated dynamically
		const config = getPiiConfig();
		const defaultDebounce = debounceMs || config.timing.defaultDebounceMs;
		const debouncedDetection = debounce(performPiiDetection, defaultDebounce);
		const debouncedIncrementalDetection = debounce(performIncrementalPiiDetection, defaultDebounce);

		const plugin = new Plugin<PiiDetectionState>({
			key: piiDetectionPluginKey,

			state: {
				init(): PiiDetectionState {
					return {
						entities: [],
						positionMapping: null,
						isDetecting: false,
						lastText: '',
						needsSync: false,
						userEdited: false,
						textNodes: [],
						lastWordCount: 0,
						dynamicallyEnabled: options.enabled, // Initialize with the static enabled option
						temporarilyHiddenEntities: new Set(),
						isFastMaskUpdate: false
					};
				},

				apply(tr, prevState): PiiDetectionState {
					const tracker = PiiPerformanceTracker.getInstance();
					tracker.recordStateUpdate();

					const newState = { ...prevState };

					const meta = tr.getMeta(piiDetectionPluginKey);
					if (meta) {
						// Reduce verbose meta action logging - only log important actions
						if (
							meta.type === 'TRIGGER_DETECTION' ||
							meta.type === 'FORCE_DETECTION' ||
							meta.type === 'TEMPORARILY_HIDE_ENTITY'
						) {
							console.log('PiiDetectionExtension: meta action', meta.type, meta);
						}
						switch (meta.type) {
							case 'SET_USER_EDITED':
								newState.userEdited = true;
								break;

							case 'ENABLE_PII_DETECTION':
								newState.dynamicallyEnabled = true;
								// Trigger detection if we have content
								if (newState.positionMapping?.plainText.trim()) {
									debouncedDetection(newState.positionMapping.plainText);
								}
								break;

							case 'DISABLE_PII_DETECTION':
								newState.dynamicallyEnabled = false;
								newState.entities = []; // Clear all entities
								newState.isDetecting = false; // Stop any ongoing detection
								break;

							case 'CLEAR_PII_HIGHLIGHTS':
								newState.entities = []; // Clear all entities but keep detection enabled
								break;

							case 'TEMPORARILY_HIDE_ENTITY': {
								// Temporarily hide entity when modifier is removed
								const entityToHide = meta.entityText;
								if (entityToHide) {
									newState.temporarilyHiddenEntities = new Set(newState.temporarilyHiddenEntities);
									newState.temporarilyHiddenEntities.add(entityToHide.toLowerCase());
									// Clear decoration cache to force recreation without hidden entity
									newState.cachedDecorations = undefined;
									newState.lastDecorationHash = undefined;
									console.log('PiiDetectionExtension: Temporarily hiding entity');
									console.log(
										'PiiDetectionExtension: Current entities count:',
										newState.entities.length
									);
									console.log(
										'PiiDetectionExtension: Hidden entities count:',
										newState.temporarilyHiddenEntities.size
									);
								}
								break;
							}
							case 'SET_DETECTING':
								newState.isDetecting = meta.isDetecting;
								// Call the callback to notify parent component
								if (options.onPiiDetectionStateChanged) {
									options.onPiiDetectionStateChanged(meta.isDetecting);
								}
								break;

							case 'CLEAR_FAST_MASK_UPDATE_FLAG':
								newState.isFastMaskUpdate = false;
								console.log(
									'PiiDetectionExtension: ✅ Fast mask update completed, regular detection re-enabled'
								);
								break;

							case 'UPDATE_ENTITIES':
								// ANTI-FLICKER: Preserve current entities during mapping to prevent brief empty states
								const previousEntities = [...newState.entities];

								// Recompute occurrences against current document to avoid shifted offsets
								// (e.g., when original indices were based on markdown source rather than rendered doc)
								if (meta.entities && meta.entities.length) {
									let mapping = newState.positionMapping;
									if (!mapping) {
										const endTiming = tracker.startTiming();
										mapping = buildPositionMapping(tr.doc);
										const elapsed = endTiming();
										tracker.recordPositionRemap();
										if (elapsed > 5)
											console.log(
												`PiiDetectionExtension: Position mapping (UPDATE_ENTITIES): ${elapsed.toFixed(1)}ms`
											);
									}

									// Determine if this is a partial update (incremental) or full update
									const isIncrementalUpdate = meta.isIncrementalUpdate === true;

									if (isIncrementalUpdate) {
										// For incremental updates, merge with existing entities instead of replacing
										console.log('PiiDetectionExtension: Performing incremental entity update', {
											newEntities: meta.entities.length,
											existingEntities: newState.entities.length
										});

										// Remap new entities to current document positions
										const remappedNewEntities = remapEntitiesForCurrentDocument(
											meta.entities,
											mapping,
											tr.doc
										);
										const validatedNewEntities = validateAndFilterEntities(
											remappedNewEntities,
											tr.doc,
											mapping
										);

										// OPTIMIZED: Only update if we have valid new entities
										if (validatedNewEntities.length > 0) {
											// Merge new entities with existing ones
											const mergedEntities = [...newState.entities];
											validatedNewEntities.forEach((newEntity) => {
												const existingIndex = mergedEntities.findIndex(
													(e) => e.label === newEntity.label
												);
												if (existingIndex >= 0) {
													// Update existing entity but preserve shouldMask state
													mergedEntities[existingIndex] = {
														...newEntity,
														shouldMask:
															mergedEntities[existingIndex].shouldMask ?? newEntity.shouldMask
													};
												} else {
													// Add new entity
													mergedEntities.push(newEntity);
												}
											});

											newState.entities = resolveOverlaps(mergedEntities, tr.doc);
										}
										// else: keep previous entities if validation failed
									} else {
										// For full updates, replace all entities
										const remapped = remapEntitiesForCurrentDocument(
											meta.entities,
											mapping,
											tr.doc
										);
										const validated = validateAndFilterEntities(remapped, tr.doc, mapping);
										// ANTI-FLICKER: Only update if we have valid entities, otherwise keep previous
										if (validated.length > 0) {
											newState.entities = resolveOverlaps(validated, tr.doc);
										} else {
											console.log(
												'PiiDetectionExtension: No valid entities from update, preserving previous state'
											);
											newState.entities = previousEntities;
										}
									}
								} else if (meta.clearAllEntities === true) {
									// Only clear entities when explicitly requested
									console.log('PiiDetectionExtension: Explicitly clearing all entities');
									newState.entities = [];
								} else {
									// If no entities provided and not explicitly clearing, preserve existing entities
									// This prevents accidental clearing during partial updates
									console.log(
										'PiiDetectionExtension: No entities provided, preserving existing entities'
									);

									// Still validate existing entities against current document
									if (newState.entities.length > 0) {
										let mapping = newState.positionMapping;
										if (!mapping) {
											const endTiming = tracker.startTiming();
											mapping = buildPositionMapping(tr.doc);
											const elapsed = endTiming();
											tracker.recordPositionRemap();
										}
										const validated = validateAndFilterEntities(newState.entities, tr.doc, mapping);
										// ANTI-FLICKER: Only update if validation succeeds
										if (validated.length > 0) {
											newState.entities = validated;
										}
									}
								}
								// Only clear temporarily hidden entities if explicitly requested
								// This allows entities to stay hidden after modifier removal until user makes another edit
								if (meta.clearTemporarilyHidden === true) {
									console.log(
										'PiiDetectionExtension: Clearing temporarily hidden entities on API update'
									);
									newState.temporarilyHiddenEntities = new Set();
								} else {
									console.log(
										'PiiDetectionExtension: Keeping temporarily hidden entities through API update'
									);
									// Keep the existing temporarily hidden entities
								}
								// OPTIMIZED: Only clear cache if entities actually changed
								if (JSON.stringify(newState.entities) !== JSON.stringify(previousEntities)) {
									newState.cachedDecorations = undefined;
									newState.lastDecorationHash = undefined;
								}
								break;

							case 'SYNC_WITH_SESSION_MANAGER': {
								// Always sync from session manager to get latest state
								let currentMapping = newState.positionMapping;
								if (!currentMapping) {
									const endTiming = tracker.startTiming();
									currentMapping = buildPositionMapping(tr.doc);
									const elapsed = endTiming();
									tracker.recordPositionRemap();
									if (elapsed > 5)
										console.log(
											`PiiDetectionExtension: Position mapping (SYNC): ${elapsed.toFixed(1)}ms`
										);
								}
								const sessionEntities = piiSessionManager.getEntitiesForDisplay(
									options.conversationId
								);

								// Always use session entities as source of truth when syncing
								if (sessionEntities.length > 0) {
									// Remap session entities to current doc positions
									const remapped = remapEntitiesForCurrentDocument(
										sessionEntities,
										currentMapping,
										tr.doc
									);
									newState.entities = validateAndFilterEntities(remapped, tr.doc, currentMapping);
									newState.entities = resolveOverlaps(newState.entities, tr.doc);
								} else if (newState.entities.length > 0) {
									// If session is empty but we have entities, sync them to session
									newState.entities = syncWithSessionManager(
										options.conversationId,
										piiSessionManager,
										newState.entities,
										currentMapping,
										tr.doc
									);
									// Persist current plugin entities to session for future lookups
									if (options.conversationId) {
										piiSessionManager.setConversationWorkingEntitiesWithMaskStates(
											options.conversationId,
											newState.entities
										);
									} else {
										if (!piiSessionManager.isTemporaryStateActive()) {
											piiSessionManager.activateTemporaryState();
										}
										piiSessionManager.setTemporaryStateEntities(newState.entities);
									}
								}
								break;
							}

							case 'TOGGLE_ENTITY_MASKING': {
								const { entityIndex, occurrenceIndex, fromModifierRemoval } = meta;
								if (newState.entities[entityIndex]) {
									const entity = newState.entities[entityIndex];
									const piiSessionManager = PiiSessionManager.getInstance();

									// SYNCHRONOUS: Update both plugin and session manager together
									// This prevents state drift while maintaining performance
									const newShouldMask = !entity.shouldMask;

									// Update local plugin state immediately for visual feedback
									newState.entities = newState.entities.map((e, index) =>
										index === entityIndex ? { ...e, shouldMask: newShouldMask } : e
									);

									// Handle temporarily hidden entities
									const entityText = (entity.raw_text || entity.text || '').toLowerCase();
									if (!fromModifierRemoval && newState.temporarilyHiddenEntities.has(entityText)) {
										newState.temporarilyHiddenEntities = new Set(
											newState.temporarilyHiddenEntities
										);
										newState.temporarilyHiddenEntities.delete(entityText);
										console.log(
											'PiiDetectionExtension: Cleared temporarily hidden entity on regular toggle'
										);
									}

									// IMMEDIATE: Update session manager synchronously but efficiently
									try {
										if (options.conversationId) {
											// Handle persistent conversation
											const sessionEntities = piiSessionManager.getEntitiesForDisplay(
												options.conversationId
											);
											const sessionEntity = sessionEntities.find(
												(e: any) => e.label === entity.label
											);

											if (sessionEntity) {
												// Entity exists in session - direct toggle
												piiSessionManager.setEntityMaskingState(
													options.conversationId,
													entity.label,
													newShouldMask
												);
											} else {
												// Entity doesn't exist in session - add it with correct state
												const entityToAdd = { ...entity, shouldMask: newShouldMask };
												piiSessionManager.setConversationWorkingEntitiesWithMaskStates(
													options.conversationId,
													[entityToAdd]
												);
											}
										} else {
											// Handle temporary state (new chat)
											if (!piiSessionManager.isTemporaryStateActive()) {
												piiSessionManager.activateTemporaryState();
											}

											const tempEntities = piiSessionManager.getEntitiesForDisplay(undefined);
											const tempEntity = tempEntities.find((e: any) => e.label === entity.label);

											if (tempEntity) {
												// Entity exists in temp state - direct toggle
												piiSessionManager.setTemporaryEntityMaskingState(
													entity.label,
													newShouldMask
												);
											} else {
												// Entity doesn't exist in temp state - add it with correct state
												const entityToAdd = { ...entity, shouldMask: newShouldMask };
												piiSessionManager.setTemporaryStateEntities([entityToAdd]);
											}
										}
									} catch (error) {
										console.warn('PiiDetectionExtension: Session manager update failed:', error);
										// Continue with plugin state - don't let session errors break UI
									}

									// OPTIMIZED: Clear decoration cache for immediate visual update
									newState.cachedDecorations = undefined;
									newState.lastDecorationHash = undefined;

									// Trigger callback with updated local state
									if (options.onPiiToggled) {
										options.onPiiToggled(newState.entities);
									}
								}
								break;
							}

							case 'TRIGGER_DETECTION':
							case 'TRIGGER_DETECTION_WITH_MODIFIERS': {
								const currentMapping = buildPositionMapping(tr.doc);
								const currentTextNodes = extractTextNodes(tr.doc);
								const currentWordCount = countWords(currentMapping.plainText);

								newState.positionMapping = currentMapping;
								newState.textNodes = currentTextNodes;
								newState.lastWordCount = currentWordCount;

								if (currentMapping.plainText.trim()) {
									newState.lastText = currentMapping.plainText;

									// Check if a fast mask update is in progress
									if (newState.isFastMaskUpdate) {
										console.log(
											'PiiDetectionExtension: Skipping regular detection - fast mask update in progress'
										);
									} else {
										performPiiDetection(currentMapping.plainText);
									}
								}
								break;
							}

							case 'TRIGGER_FAST_MASK_UPDATE': {
								// Skip fast mask update if disabled (e.g., for FileItemModal where component handles API calls)
								if (options.disableModifierTriggeredDetection) {
									console.log(
										'PiiDetectionExtension: Fast mask update skipped - disabled by disableModifierTriggeredDetection flag'
									);
									break;
								}

								// Use the fast mask-update API when modifiers are added/removed
								const currentMapping = buildPositionMapping(tr.doc);
								const currentTextNodes = extractTextNodes(tr.doc);
								const currentWordCount = countWords(currentMapping.plainText);

								newState.positionMapping = currentMapping;
								newState.textNodes = currentTextNodes;
								newState.lastWordCount = currentWordCount;
								newState.isFastMaskUpdate = true; // Set flag to prevent regular detection
								console.log(
									'PiiDetectionExtension: 🚀 Starting fast mask update, blocking regular detection'
								);

								if (currentMapping.plainText.trim()) {
									newState.lastText = currentMapping.plainText;
									performFastMaskUpdate(currentMapping.plainText, newState.entities);
								}
								break;
							}

							case 'RELOAD_CONVERSATION_STATE': {
								options.conversationId = meta.conversationId;

								const newMapping = buildPositionMapping(tr.doc);
								const currentTextNodes = extractTextNodes(tr.doc);
								const currentWordCount = countWords(newMapping.plainText);

								newState.positionMapping = newMapping;
								newState.textNodes = currentTextNodes;
								newState.lastWordCount = currentWordCount;
								newState.lastText = newMapping.plainText;

								// Populate entities from session immediately without triggering detection
								const sessionEntities = piiSessionManager.getEntitiesForDisplay(
									options.conversationId
								);
								if (sessionEntities.length) {
									const remapped = remapEntitiesForCurrentDocument(
										sessionEntities,
										newMapping,
										tr.doc
									);
									newState.entities = validateAndFilterEntities(remapped, tr.doc, newMapping);
									newState.entities = resolveOverlaps(newState.entities, tr.doc);
								}
								break;
							}

							case 'FORCE_DETECTION': {
								// Update state to indicate content has changed and should be detected
								const newMapping = buildPositionMapping(tr.doc);
								const currentTextNodes = extractTextNodes(tr.doc);
								const currentWordCount = countWords(newMapping.plainText);

								newState.positionMapping = newMapping;
								newState.textNodes = currentTextNodes;
								newState.lastWordCount = currentWordCount;
								newState.lastText = newMapping.plainText;
								newState.userEdited = true; // Mark as user edited to bypass edit checks

								console.log('PiiDetectionExtension: Force detection triggered for content:', {
									wordCount: currentWordCount,
									nodeCount: currentTextNodes.length
								});
								break;
							}
						}
					}

					if (tr.docChanged) {
						const newMapping = buildPositionMapping(tr.doc);
						const currentTextNodes = extractTextNodes(tr.doc);
						const currentWordCount = countWords(newMapping.plainText);

						// Track this transaction for rapid change detection
						const isRapidChange = typingPauseDetector.onTransaction();

						// Reset typing pause timer on every content change
						typingPauseDetector.onTextChange(newMapping.plainText, handlePauseTriggeredDetection);

						// Detect if this is a user edit vs programmatic change
						// Be more restrictive: only consider it a user edit if there's clear evidence of user interaction
						const isPiiPluginTransaction = !!tr.getMeta(piiDetectionPluginKey);
						const hasInputMeta = !!(
							tr.getMeta('inputType') ||
							tr.getMeta('paste') ||
							tr.getMeta('uiEvent')
						);
						const hasReplaceSteps = tr.steps.some(
							(step) => step.jsonID === 'replace' || step.jsonID === 'replaceAround'
						);

						// Calculate the size of changes to distinguish between user typing and bulk loading
						const totalChangeSize = tr.steps.reduce((size, step) => {
							if (step.jsonID === 'replace') {
								// Approximate change size - this isn't perfect but gives us an indication
								return (
									size +
									((step as any).to - (step as any).from) +
									((step as any).slice?.content?.size || 0)
								);
							}
							return size;
						}, 0);

						// Consider it a user edit ONLY if:
						// 1. Not from our plugin AND
						// 2. Has clear input metadata (paste, inputType, uiEvent)
						//
						// NOTE: Removed change size detection because decoration updates, entity remapping,
						// and other internal operations can create small replace steps that aren't user edits
						const isUserEdit = !isPiiPluginTransaction && hasInputMeta;

						if (isUserEdit) {
							console.log('PiiDetectionExtension: Detected user edit transaction', {
								hasReplaceSteps,
								hasInputMeta,
								totalChangeSize,
								isRapidChange,
								steps: tr.steps.map((s) => s.jsonID),
								previousWordCount: prevState.lastWordCount
							});
							newState.userEdited = true;
							// Clear temporarily hidden entities on genuine user edits
							if (newState.temporarilyHiddenEntities.size > 0) {
								console.log(
									'PiiDetectionExtension: Clearing temporarily hidden entities due to user edit'
								);
								newState.temporarilyHiddenEntities = new Set();
								newState.cachedDecorations = undefined;
								newState.lastDecorationHash = undefined;
							}
							// Mark user activity for typing pause detection
							typingPauseDetector.onUserKeystroke();
						} else if (tr.docChanged && !isPiiPluginTransaction) {
							// Log programmatic changes for debugging
							console.log(
								'PiiDetectionExtension: Programmatic content change detected (not user edit)',
								{
									hasReplaceSteps,
									hasInputMeta,
									totalChangeSize,
									isRapidChange,
									steps: tr.steps.map((s) => s.jsonID),
									previousWordCount: prevState.lastWordCount,
									reason: hasInputMeta
										? 'Has input meta but failed other checks'
										: 'No input meta (decoration/internal update)'
								}
							);
						}

						// Update position mapping and tracking data
						newState.positionMapping = newMapping;

						// Check if we have new content using node-based detection
						const hasNewTextContent = hasNewContent(
							prevState.textNodes,
							currentTextNodes,
							prevState.lastWordCount,
							currentWordCount
						);

						// Update text node tracking
						newState.textNodes = currentTextNodes;
						newState.lastWordCount = currentWordCount;

						// CRITICAL: Always update lastText when document changes to prevent circular word detection failure
						newState.lastText = newMapping.plainText;

						// Smart API call filtering - only call API when there's actually significant new content
						const newWords = findNewWords(prevState.lastText, newMapping.plainText);
						const hasSignificantNewContent = hasSignificantContent(newWords);

						// Only log when filtering decisions are interesting (new words found but blocked)
						if (hasNewTextContent && newWords.length > 0 && !hasSignificantNewContent) {
							console.log('PiiDetectionExtension: 🔍 Filtering blocked detection', {
								newWordsCount: newWords.length,
								reason: 'No meaningful words (3+ chars, alphabetic)'
							});
						}

						// Determine if we should trigger detection
						// Only call API if:
						// 1. We have new text content
						// 2. The new content contains new words (not just formatting changes)
						// 3. We're not already detecting
						// 4. We're not in the middle of a fast mask update
						// 5. User edit requirements are met
						const shouldTriggerDetection =
							hasNewTextContent &&
							hasSignificantNewContent &&
							!newState.isDetecting &&
							!newState.isFastMaskUpdate &&
							(!options.detectOnlyAfterUserEdit || newState.userEdited) &&
							newMapping.plainText.trim().length > 0;

						// Debug why detection might be skipped
						if (hasNewTextContent && hasSignificantNewContent && !shouldTriggerDetection) {
							console.log(
								'PiiDetectionExtension: 🔍 Detection blocked despite significant content',
								{
									hasNewTextContent,
									hasSignificantNewContent,
									isDetecting: newState.isDetecting,
									isFastMaskUpdate: newState.isFastMaskUpdate,
									detectOnlyAfterUserEdit: options.detectOnlyAfterUserEdit,
									userEdited: newState.userEdited,
									textLength: newMapping.plainText.trim().length,
									userEditRequirement: !options.detectOnlyAfterUserEdit || newState.userEdited,
									allConditions: {
										hasNewTextContent,
										hasSignificantNewContent,
										notDetecting: !newState.isDetecting,
										notFastMaskUpdate: !newState.isFastMaskUpdate,
										userEditOk: !options.detectOnlyAfterUserEdit || newState.userEdited,
										hasText: newMapping.plainText.trim().length > 0
									}
								}
							);
						}

						if (shouldTriggerDetection) {
							// Try incremental detection first for better performance
							const incrementalResult = extractIncrementalContent(
								prevState.lastText,
								newMapping.plainText
							);
							// Use more flexible criteria for larger documents
							const documentSize = newMapping.plainText.length;
							const maxIncrementalRatio =
								documentSize < 1000
									? 0.5 // 50% for small docs
									: documentSize < 10000
										? 0.4 // 40% for medium docs
										: 0.3; // 30% for large docs
							const useIncremental =
								incrementalResult !== null &&
								incrementalResult.content.length < documentSize * maxIncrementalRatio;

							console.log('PiiDetectionExtension: 🚀 Triggering PII detection', {
								newWordsCount: newWords.length,
								useIncremental,
								textLength: newMapping.plainText.trim().length
							});

							// Calculate smart debounce delay based on content significance
							const smartDelay = getSmartDebounceDelay(
								newWords,
								incrementalResult?.content || null
							);

							if (useIncremental && incrementalResult) {
								// Create context snippet around the change for more meaningful PII detection
								const contextSnippet = createContextSnippet(
									newMapping.plainText,
									incrementalResult.offset,
									incrementalResult.content.length
								);

								// Use context snippet detection for better performance with smart timing
								console.log(
									'PiiDetectionExtension: Using context snippet detection with smart timing',
									{
										originalIncrementalLength: incrementalResult.content.length,
										contextSnippetLength: contextSnippet.content.length,
										contextSnippetOffset: contextSnippet.offset,
										originalOffset: incrementalResult.offset,
										fullLength: newMapping.plainText.length,
										savingsPercent: Math.round(
											(1 - contextSnippet.content.length / newMapping.plainText.length) * 100
										),
										smartDelay,
										defaultDelay: debounceMs || config.timing.defaultDebounceMs,
										contextLength: contextSnippet.content.length
									}
								);

								// Create a one-time debounced function with smart delay and pass the context snippet offset
								const smartIncrementalDetection = debounce(
									(text: string, fullText: string) =>
										performIncrementalPiiDetection(text, fullText, contextSnippet.offset),
									smartDelay
								);
								smartIncrementalDetection(contextSnippet.content, newMapping.plainText);
							} else {
								// Fall back to full document detection with smart timing
								console.log('PiiDetectionExtension: Using full detection with smart timing', {
									smartDelay,
									defaultDelay: debounceMs || config.timing.defaultDebounceMs,
									newWordsCount: newWords.length,
									incrementalFailed: incrementalResult === null,
									incrementalTooLarge:
										incrementalResult &&
										incrementalResult.content.length >= documentSize * maxIncrementalRatio
								});

								// Create a one-time debounced function with smart delay
								const smartDetection = debounce(performPiiDetection, smartDelay);
								smartDetection(newMapping.plainText);
							}
						} else if (hasNewTextContent && newWords.length === 0) {
							console.log('PiiDetectionExtension: ⏭️ No new words detected, skipping API call');
						}

						// Always remap existing entities when document changes
						if (newState.entities.length > 0) {
							// First, try to remap entities to current positions
							const remappedEntities = remapEntitiesForCurrentDocument(
								newState.entities,
								newState.positionMapping,
								tr.doc
							);

							// Then sync with session manager for external changes
							newState.entities = syncWithSessionManager(
								options.conversationId,
								piiSessionManager,
								remappedEntities,
								newState.positionMapping,
								tr.doc
							);
							newState.entities = resolveOverlaps(newState.entities, tr.doc);
						} else {
							// If we have no entities yet, populate from session if available
							const sessionEntities = piiSessionManager.getEntitiesForDisplay(
								options.conversationId
							);
							if (sessionEntities.length) {
								const remapped = remapEntitiesForCurrentDocument(
									sessionEntities,
									newState.positionMapping,
									tr.doc
								);
								newState.entities = validateAndFilterEntities(
									remapped,
									tr.doc,
									newState.positionMapping
								);
								newState.entities = resolveOverlaps(newState.entities, tr.doc);
							}
						}

						// Handle sync flag for consistency
						if (newState.needsSync) {
							newState.entities = syncWithSessionManager(
								options.conversationId,
								piiSessionManager,
								newState.entities,
								newState.positionMapping,
								tr.doc
							);
							newState.needsSync = false;
						}

						// Trigger detection if text changed significantly
						if (
							newState.dynamicallyEnabled &&
							!newState.isDetecting &&
							newMapping.plainText !== newState.lastText &&
							(!options.detectOnlyAfterUserEdit || newState.userEdited)
						) {
							newState.lastText = newMapping.plainText;

							if (newMapping.plainText.trim()) {
								debouncedDetection(newMapping.plainText);
							} else {
								// If text is empty, clear entities
								newState.entities = [];
								newState.textNodes = [];
								newState.lastWordCount = 0;
								newState.lastText = '';
							}
						} else if (!newState.dynamicallyEnabled) {
							// If detection is disabled, clear entities
							newState.entities = [];
						}
					}
					return newState;
				}
			},

			props: {
				decorations(state) {
					const pluginState = piiDetectionPluginKey.getState(state);

					// Only show decorations if PII detection is dynamically enabled
					if (!pluginState?.dynamicallyEnabled) {
						return DecorationSet.empty;
					}

					// Get modifiers from session manager (not ProseMirror extension state)
					const piiSessionManager = PiiSessionManager.getInstance();
					const modifiers = piiSessionManager.getModifiersForDisplay(options.conversationId);

					// OPTIMIZED: Create a more stable hash that doesn't include occurrences (which change frequently)
					// This reduces unnecessary decoration rebuilds during position remapping
					const entitiesHash = JSON.stringify(
						(pluginState.entities || []).map((e) => ({
							label: e.label,
							shouldMask: e.shouldMask,
							text: e.raw_text || e.text // Use text content rather than positions
						}))
					);
					const modifiersHash = JSON.stringify(
						modifiers.map((m) => ({ id: m.id, entity: m.entity, action: m.action }))
					);
					const currentHash = `${entitiesHash}-${modifiersHash}-${state.doc.content.size}`;

					// IMPROVED: More aggressive caching to prevent flickering
					// Return cached decorations if hash matches, regardless of selection state
					// Only rebuild when content or entity state actually changes
					if (pluginState.cachedDecorations && pluginState.lastDecorationHash === currentHash) {
						return pluginState.cachedDecorations;
					}

					// SIMPLIFIED: Use plugin entities as primary source to reduce complexity and flickering
					// Plugin entities should already be synced with session manager via other mechanisms
					let entities = pluginState.entities || [];
					const sessionEntities = piiSessionManager.getEntitiesForDisplay(options.conversationId);

					// LIGHTWEIGHT: Only fall back to session entities if plugin is completely empty
					// This prevents expensive remapping operations during decoration rendering
					if (!entities.length && sessionEntities.length) {
						const mapping = buildPositionMapping(state.doc);
						const remapped = remapEntitiesForCurrentDocument(sessionEntities, mapping, state.doc);
						entities = validateAndFilterEntities(remapped, state.doc, mapping);
						console.log('PiiDetectionExtension: Fallback to session entities for decorations', {
							sessionEntities: sessionEntities.length,
							remappedEntities: entities.length
						});
					}

					// CONSERVATIVE: Only sync shouldMask from session when plugin state is clearly stale
					// This prevents overriding fresh toggle states from user interactions
					if (entities.length > 0 && sessionEntities.length > 0) {
						// Check if plugin state might be stale (significant difference in entity count)
						const significantDifference = Math.abs(entities.length - sessionEntities.length) > 2;

						// Only sync if there's a significant state difference, not for minor toggles
						if (significantDifference) {
							console.log(
								'PiiDetectionExtension: Syncing shouldMask due to significant state difference'
							);
							entities = entities.map((pluginEntity) => {
								const sessionEntity = sessionEntities.find(
									(se: ExtendedPiiEntity) => se.label === pluginEntity.label
								);
								if (sessionEntity && sessionEntity.shouldMask !== pluginEntity.shouldMask) {
									return { ...pluginEntity, shouldMask: sessionEntity.shouldMask };
								}
								return pluginEntity;
							});
						}
						// Otherwise, trust the plugin state (it's fresher from user interactions)
					}

					// Filter out temporarily hidden entities
					const temporarilyHidden = pluginState.temporarilyHiddenEntities || new Set();
					if (temporarilyHidden.size > 0) {
						entities = entities.filter((entity) => {
							const entityText = (entity.raw_text || '').toLowerCase();
							// Check for exact match first
							if (temporarilyHidden.has(entityText)) {
								console.log('PiiDetectionExtension: Hiding entity (exact match)');
								return false;
							}
							// Check if any hidden text matches this entity
							for (const hiddenText of temporarilyHidden) {
								if (
									entityText === hiddenText ||
									entityText.includes(hiddenText) ||
									hiddenText.includes(entityText)
								) {
									console.log('PiiDetectionExtension: Hiding entity (partial match)');
									return false;
								}
							}
							return true;
						});
					}

					if (!entities.length && !modifiers.length) {
						return DecorationSet.empty;
					}

					// Create new decorations
					const decorations = createPiiDecorations(entities, modifiers, state.doc);
					const decorationSet = DecorationSet.create(state.doc, decorations);

					// Cache the decorations in plugin state for next time
					// Note: This is a bit of a hack since we're modifying state in a read-only function
					// but it's necessary to prevent cursor jumping
					(pluginState as any).cachedDecorations = decorationSet;
					(pluginState as any).lastDecorationHash = currentHash;

					return decorationSet;
				},

				handleClick(view, pos, event) {
					const target = event.target as HTMLElement;

					if (target.classList.contains('pii-highlight')) {
						const entityIndex = parseInt(target.getAttribute('data-entity-index') || '0');
						const occurrenceIndex = parseInt(target.getAttribute('data-pii-occurrence') || '0');

						const tr = view.state.tr.setMeta(piiDetectionPluginKey, {
							type: 'TOGGLE_ENTITY_MASKING',
							entityIndex,
							occurrenceIndex
						});

						view.dispatch(tr);
						event.preventDefault();
						return true;
					}

					return false;
				}
			}
		});

		return [plugin];
	},

	addCommands() {
		const options = this.options;

		// Get access to the typing pause detector from the extension storage
		const getTypingPauseDetector = () => {
			// Access the detector from the editor instance if available
			return (this.editor as any)?._typingPauseDetector;
		};

		// Helper function to update all entity masking states (DRY)
		// eslint-disable-next-line @typescript-eslint/no-explicit-any
		const updateAllEntityMaskingStates =
			(shouldMask: boolean) =>
			({ state, dispatch }: any) => {
				const pluginState = piiDetectionPluginKey.getState(state);
				if (!pluginState?.entities.length) {
					return false; // No entities to update
				}

				const piiSessionManager = PiiSessionManager.getInstance();

				// Get current entities using the proper display method
				const currentEntities = piiSessionManager.getEntitiesForDisplay(options.conversationId);

				if (!currentEntities.length) {
					return false; // No entities in session manager
				}

				// Update session manager based on state type
				if (piiSessionManager.isTemporaryStateActive()) {
					// Handle temporary state (new chats)
					const updatedEntities = currentEntities.map((entity: ExtendedPiiEntity) => ({
						...entity,
						shouldMask
					}));
					piiSessionManager.setTemporaryStateEntities(updatedEntities);
				} else if (options.conversationId) {
					// Handle conversation state - update each entity individually for proper persistence
					currentEntities.forEach((entity: ExtendedPiiEntity) => {
						piiSessionManager.setEntityMaskingState(
							options.conversationId!,
							entity.label,
							shouldMask
						);
					});
				}

				// Create updated entities for plugin state
				const updatedPluginEntities = pluginState.entities.map((entity: ExtendedPiiEntity) => ({
					...entity,
					shouldMask
				}));

				// Update plugin state
				if (dispatch) {
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'UPDATE_ENTITIES',
						entities: updatedPluginEntities,
						clearTemporarilyHidden: false // Don't clear when just updating masking states
					});
					dispatch(tr);

					// Trigger onPiiToggled callback
					if (options.onPiiToggled) {
						options.onPiiToggled(updatedPluginEntities);
					}
				}

				return true;
			};

		return {
			// Mark that the user edited the document (used to gate auto-detection on load)
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			markUserEdited:
				() =>
				({ state, dispatch }: any) => {
					if (!dispatch) return false;
					const tr = state.tr.setMeta(piiDetectionPluginKey, { type: 'SET_USER_EDITED' });
					dispatch(tr);
					return true;
				},

			// Get current plugin state (useful for debugging)
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			getPluginState:
				() =>
				({ state }: any) => {
					return piiDetectionPluginKey.getState(state);
				},
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			triggerDetection:
				() =>
				({ state, dispatch }: any) => {
					if (dispatch) {
						const tr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'TRIGGER_DETECTION'
						});
						dispatch(tr);
						return true;
					}
					return false;
				},

			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			triggerDetectionForModifiers:
				() =>
				({ state, dispatch }: any) => {
					if (dispatch) {
						const tr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'TRIGGER_DETECTION_WITH_MODIFIERS'
						});
						dispatch(tr);
						return true;
					}
					return false;
				},

			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			syncWithSessionManager:
				() =>
				({ state, dispatch }: any) => {
					if (dispatch) {
						const tr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'SYNC_WITH_SESSION_MANAGER'
						});
						dispatch(tr);
						return true;
					}
					return false;
				},

			// Force immediate entity remapping and decoration update
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			forceEntityRemapping:
				() =>
				({ state, dispatch }: any) => {
					const pluginState = piiDetectionPluginKey.getState(state);

					if (!pluginState?.entities.length || !dispatch) {
						return false;
					}

					// Build current position mapping
					const mapping = buildPositionMapping(state.doc);

					// Remap entities to current positions
					const remappedEntities = remapEntitiesForCurrentDocument(
						pluginState.entities,
						mapping,
						state.doc
					);

					// Update plugin state with remapped entities
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'UPDATE_ENTITIES',
						entities: remappedEntities,
						clearTemporarilyHidden: false // Don't clear when just remapping positions
					});

					dispatch(tr);
					return true;
				},

			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			reloadConversationState:
				(newConversationId: string) =>
				({ state, dispatch }: any) => {
					if (dispatch) {
						const tr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'RELOAD_CONVERSATION_STATE',
							conversationId: newConversationId
						});
						dispatch(tr);
						return true;
					}
					return false;
				},

			// Unmask all PII entities
			unmaskAllEntities: () => updateAllEntityMaskingStates(false),

			// Mask all PII entities
			maskAllEntities: () => updateAllEntityMaskingStates(true),

			// Force PII detection (useful for programmatically loaded content)
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			forceDetection:
				() =>
				({ state, dispatch }: any) => {
					const mapping = buildPositionMapping(state.doc);

					if (!mapping.plainText.trim()) {
						return false; // No content to detect
					}

					// Force detection by updating the plugin state to mark content as changed
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'FORCE_DETECTION',
						plainText: mapping.plainText
					});

					if (dispatch) {
						dispatch(tr);

						// Trigger detection immediately (bypass debounce for forced detection)
						performPiiDetection(mapping.plainText);
						return true;
					}

					return false;
				},

			// Cleanup typing pause detector (call when component unmounts)
			cleanup: () => {
				const detector = getTypingPauseDetector();
				if (detector) {
					detector.cleanup();
					console.log('PiiDetectionExtension: Cleaned up typing pause detector');
				}
			},

			// Debug command to get typing pause detector state
			getTypingPauseDetectorState: () => {
				const detector = getTypingPauseDetector();
				if (detector) {
					const state = detector.getState();
					console.log('PiiDetectionExtension: Typing pause detector state:', state);
					return state;
				} else {
					console.warn('PiiDetectionExtension: typingPauseDetector not available');
					return null;
				}
			},

			// Manually mark user activity (for explicit user interaction tracking)
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			markUserActivity:
				() =>
				({ state, dispatch }: any) => {
					console.log('PiiDetectionExtension: User activity manually marked');

					// Access the typing pause detector
					const detector = getTypingPauseDetector();
					if (detector) {
						detector.onUserKeystroke();
					} else {
						console.warn(
							'PiiDetectionExtension: typingPauseDetector not available in command context'
						);
					}

					// Also mark the document as user-edited
					if (dispatch) {
						const tr = state.tr.setMeta(piiDetectionPluginKey, { type: 'SET_USER_EDITED' });
						dispatch(tr);
					}
					return true;
				},
			enablePiiDetection:
				() =>
				({ state, dispatch }: any) => {
					if (dispatch) {
						const tr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'ENABLE_PII_DETECTION'
						});
						dispatch(tr);
						return true;
					}
					return false;
				},

			// Disable PII detection dynamically
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			disablePiiDetection:
				() =>
				({ state, dispatch }: any) => {
					if (dispatch) {
						const tr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'DISABLE_PII_DETECTION'
						});
						dispatch(tr);
						return true;
					}
					return false;
				},

			// Clear all PII highlights but keep detection enabled
			// eslint-disable-next-line @typescript-eslint/no-explicit-any
			clearAllPiiHighlights:
				() =>
				({ state, dispatch }: any) => {
					if (dispatch) {
						const tr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'UPDATE_ENTITIES',
							entities: [],
							clearAllEntities: true // Explicitly clear all entities
						});
						dispatch(tr);
						return true;
					}
					return false;
				}
		};
	}
});
