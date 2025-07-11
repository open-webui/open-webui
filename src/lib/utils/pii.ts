import type { PiiEntity } from '$lib/apis/pii';
import i18next from 'i18next';

// Extended PII entity with masking state
export interface ExtendedPiiEntity extends PiiEntity {
	shouldMask?: boolean;
}

// Debounce function for PII detection
export function debounce<T extends (...args: any[]) => any>(
	func: T,
	wait: number
): (...args: Parameters<T>) => void {
	let timeout: NodeJS.Timeout;
	return (...args: Parameters<T>) => {
		clearTimeout(timeout);
		timeout = setTimeout(() => func(...args), wait);
	};
}

// Convert PII entities to match text positions in the editor
export function adjustPiiEntitiesForEditor(
	entities: PiiEntity[],
	originalText: string,
	editorText: string
): PiiEntity[] {
	// If texts are identical, return as-is
	if (originalText === editorText) {
		return entities;
	}

	// For now, return entities as-is since we're working with plain text
	// In the future, this could handle markdown conversion differences
	return entities;
}

// Extract plain text from editor content for PII detection
export function extractPlainTextFromEditor(editorContent: string): string {
	// Remove HTML tags and convert to plain text
	const tempDiv = document.createElement('div');
	tempDiv.innerHTML = editorContent;
	return tempDiv.textContent || tempDiv.innerText || '';
}

// Count br tags before a given plain text position
export function countBrTagsBeforePosition(html: string, plainTextPos: number): number {
	// Extract plain text to find character positions
	const tempDiv = document.createElement('div');
	tempDiv.innerHTML = html;
	const plainText = tempDiv.textContent || tempDiv.innerText || '';

	if (plainTextPos >= plainText.length) {
		// Count all br tags if position is at or beyond end
		return (html.match(/<br\s*\/?>/gi) || []).length;
	}

	// Walk through the HTML and count br tags that appear before the target plain text position
	let currentPlainTextPos = 0;
	let brCount = 0;
	let htmlPos = 0;

	while (htmlPos < html.length && currentPlainTextPos < plainTextPos) {
		// Check if we're at a br tag
		const brMatch = html.slice(htmlPos).match(/^<br\s*\/?>/i);
		if (brMatch) {
			brCount++;
			htmlPos += brMatch[0].length;
			continue;
		}

		// Check if we're at the start of any tag
		const tagMatch = html.slice(htmlPos).match(/^<[^>]*>/);
		if (tagMatch) {
			htmlPos += tagMatch[0].length;
			continue;
		}

		// Regular character
		currentPlainTextPos++;
		htmlPos++;
	}

	return brCount;
}

// Simple position mapping that accounts for br tags
export function mapPlainTextPositionToProseMirror(
	plainTextPos: number,
	editorHtml: string
): number {
	// Count br tags that appear before this position in the plain text
	const brTagsBeforePosition = countBrTagsBeforePosition(editorHtml, plainTextPos);

	// ProseMirror positions start at 1, add 1 for document offset, plus br tag positions
	return plainTextPos + 1 + brTagsBeforePosition;
}

// Convert masked text back to editor format
export function convertMaskedTextToEditor(maskedText: string): string {
	// For now, return the masked text as-is
	// In the future, this could preserve formatting while masking content
	return maskedText;
}

// Get PII type color for highlighting
export function getPiiTypeColor(piiType: string): string {
	const colors: Record<string, string> = {
		PERSON: '#ff6b6b',
		EMAIL: '#4ecdc4',
		PHONE_NUMBER: '#45b7d1',
		PHONENUMBER: '#45b7d1',
		ADDRESS: '#96ceb4',
		SSN: '#feca57',
		CREDIT_CARD: '#ff9ff3',
		DATE_TIME: '#54a0ff',
		IP_ADDRESS: '#5f27cd',
		URL: '#00d2d3',
		IBAN: '#ff6348',
		MEDICAL_LICENSE: '#2ed573',
		US_PASSPORT: '#ffa502',
		US_DRIVER_LICENSE: '#3742fa',
		DEFAULT: '#ddd'
	};

	return colors[piiType.toUpperCase()] || colors.DEFAULT;
}

// Create CSS styles for PII highlighting
export function createPiiHighlightStyles(): string {
	return `
		.pii-highlight {
			border-radius: 3px;
			padding: 1px 2px;
			position: relative;
			cursor: pointer;
			transition: all 0.2s ease;
			border: 1px solid transparent;
		}
		
		.pii-highlight:hover {
			border: 1px solid #333;
			box-shadow: 0 1px 3px rgba(0,0,0,0.2);
		}
		
		/* Masked entities - green background */
		.pii-highlight.pii-masked {
			background-color: rgba(34, 197, 94, 0.2);
		}
		
		.pii-highlight.pii-masked:hover {
			background-color: rgba(34, 197, 94, 0.3);
		}
		
		/* Unmasked entities - red background */
		.pii-highlight.pii-unmasked {
			background-color: rgba(239, 68, 68, 0.2);
		}
		
		.pii-highlight.pii-unmasked:hover {
			background-color: rgba(239, 68, 68, 0.3);
		}
	`;
}

// Import PiiModifier type
import type { PiiModifier } from '$lib/components/common/RichTextInput/PiiModifierExtension';

// Conversation-specific PII state for storing with chat data
export interface ConversationPiiState {
	entities: ExtendedPiiEntity[];
	modifiers: PiiModifier[];
	sessionId?: string;
	apiKey?: string;
	lastUpdated: number;
}

// Store for PII session management
export class PiiSessionManager {
	private static instance: PiiSessionManager;
	private sessionId: string | null = null;
	private apiKey: string = '';
	private conversationStates: Map<string, ConversationPiiState> = new Map();

	// Error recovery backup for failed saves
	private errorBackup: Map<string, ConversationPiiState> = new Map();
	private pendingSaves: Set<string> = new Set();
	// Track conversations currently being loaded
	private loadingConversations = new Set<string>();

	private temporaryState: {
		entities: ExtendedPiiEntity[];
		modifiers: PiiModifier[];
		isActive: boolean;
	} = {
		entities: [],
		modifiers: [],
		isActive: false
	};

	private workingEntitiesForConversations: Map<string, ExtendedPiiEntity[]> = new Map();

	static getInstance(): PiiSessionManager {
		if (!PiiSessionManager.instance) {
			PiiSessionManager.instance = new PiiSessionManager();
		}
		return PiiSessionManager.instance;
	}

	setApiKey(apiKey: string) {
		this.apiKey = apiKey;
	}

	activateTemporaryState() {
		this.temporaryState.isActive = true;
		this.temporaryState.entities = [];
		this.temporaryState.modifiers = [];
	}

	isTemporaryStateActive(): boolean {
		return this.temporaryState.isActive;
	}

	setTemporaryStateEntities(entities: ExtendedPiiEntity[]) {
		if (!this.temporaryState.isActive) {
			console.warn('PiiSessionManager: Attempted to set temporary state when not active');
			return;
		}

		// Store the extended entities directly without recalculating shouldMask states
		// This preserves shouldMask states that were already calculated from plugin state
		this.temporaryState.entities = entities;
	}

	getTemporaryStateEntities(): ExtendedPiiEntity[] {
		return [...this.temporaryState.entities];
	}

	transferTemporaryToConversation(conversationId: string) {
		if (!this.temporaryState.isActive) {
			return;
		}

		// Create conversation state from final temporary entities
		const conversationState: ConversationPiiState = {
			entities: [...this.temporaryState.entities], // Use final entities only
			modifiers: [...this.temporaryState.modifiers],
			sessionId: this.sessionId || undefined,
			apiKey: this.apiKey || undefined,
			lastUpdated: Date.now()
		};

		this.conversationStates.set(conversationId, conversationState);

		// Deactivate temporary state
		this.clearTemporaryState();

		// Trigger save for the new conversation
		this.triggerChatSave(conversationId);
	}

	clearTemporaryState() {
		this.temporaryState.isActive = false;
		this.temporaryState.entities = [];
		this.temporaryState.modifiers = [];
	}

	getEntitiesForDisplay(conversationId?: string): ExtendedPiiEntity[] {
		// Phase 1: New Chat (No Conversation ID or Invalid/Empty ID) - Use temporary state
		if (
			!conversationId ||
			conversationId.trim() === '' ||
			!this.conversationStates.has(conversationId)
		) {
			if (this.temporaryState.isActive) {
				return this.temporaryState.entities;
			}
			return [];
		}

		// Phase 2: Existing Chat (Has Valid Conversation ID) - Use persistent + working entities
		const persistentEntities = this.conversationStates.get(conversationId)?.entities || [];
		const workingEntities = this.workingEntitiesForConversations.get(conversationId) || [];

		// Simple concatenation - working entities take precedence for display
		return [...persistentEntities, ...workingEntities];
	}

	getWorkingEntitiesForConversations(conversationId: string | undefined): ExtendedPiiEntity[] {
		// Only return working entities for existing conversations
		// Temporary state is handled by getEntitiesForDisplay()
		if (conversationId) {
			return this.workingEntitiesForConversations.get(conversationId) || [];
		}
		return [];
	}

	setSession(sessionId: string) {
		this.sessionId = sessionId;
	}

	getSession(): string | null {
		return this.sessionId;
	}

	// Trigger chat save method
	private async triggerChatSave(conversationId: string): Promise<void> {
		if (this.pendingSaves.has(conversationId)) {
			return; // Already saving
		}

		this.pendingSaves.add(conversationId);

		try {
			// Trigger the chat save handler
			const windowWithTrigger = window as Window & {
				triggerPiiChatSave?: (id: string) => Promise<void>;
			};
			if (windowWithTrigger.triggerPiiChatSave) {
				await windowWithTrigger.triggerPiiChatSave(conversationId);
			}

			// Success - remove backup
			this.errorBackup.delete(conversationId);
		} catch (error) {
			console.error('PII chat save failed, keeping backup:', error);
			// Keep backup for retry
		} finally {
			this.pendingSaves.delete(conversationId);
		}
	}

	// Load conversation state (now called from loadFromChatData)
	loadConversationState(conversationId: string, piiState?: ConversationPiiState) {
		// Prevent loading the same conversation multiple times simultaneously
		if (this.loadingConversations.has(conversationId)) {
			return;
		}

		// Check if conversation is already loaded
		if (this.conversationStates.has(conversationId) && !piiState) {
			return;
		}

		this.loadingConversations.add(conversationId);

		try {
			if (piiState) {
				this.conversationStates.set(conversationId, piiState);
			}
		} finally {
			this.loadingConversations.delete(conversationId);
		}
	}

	// Removed getActiveModifiers() - use getModifiersForDisplay() instead

	// Get state for saving to localStorage (chat data)
	getConversationState(conversationId: string): ConversationPiiState | null {
		return this.conversationStates.get(conversationId) || null;
	}

	// Convert conversation entities to known entities format for API
	getKnownEntitiesForApi(
		conversationId?: string
	): Array<{ id: number; label: string; name: string }> {
		const entities = this.getEntitiesForDisplay(conversationId);
		return entities.map((entity) => ({
			id: entity.id,
			label: entity.label,
			name: entity.raw_text
		}));
	}

	// MODIFIER MANAGEMENT METHODS
	getModifiersForDisplay(conversationId?: string): PiiModifier[] {
		// Phase 1: New Chat (No Conversation ID or Invalid/Empty ID) - Use temporary state
		if (
			!conversationId ||
			conversationId.trim() === '' ||
			!this.conversationStates.has(conversationId)
		) {
			if (this.temporaryState.isActive) {
				return this.temporaryState.modifiers;
			}
			return [];
		}

		// Phase 2: Existing Chat (Has Valid Conversation ID) - Use conversation state
		const state = this.conversationStates.get(conversationId);
		return state?.modifiers || [];
	}

	// Set conversation modifiers
	setConversationModifiers(conversationId: string, modifiers: PiiModifier[]) {
		const existingState = this.conversationStates.get(conversationId);
		const newState: ConversationPiiState = {
			entities: existingState?.entities || [],
			modifiers: modifiers,
			sessionId: existingState?.sessionId,
			apiKey: existingState?.apiKey || this.apiKey || undefined,
			lastUpdated: Date.now()
		};

		this.conversationStates.set(conversationId, newState);

		// Create backup and trigger save
		this.errorBackup.set(conversationId, { ...newState });
		this.triggerChatSave(conversationId);
	}

	// Set global modifiers (before conversation ID exists)
	setTemporaryModifiers(modifiers: PiiModifier[]) {
		this.temporaryState.modifiers = modifiers;
	}

	// Get modifiers for API (works for both global and conversation state)
	getModifiersForApi(
		conversationId?: string
	): Array<{ entity: string; action: 'string-mask' | 'ignore'; type?: string }> {
		const conversationModifiers = this.getModifiersForDisplay(conversationId);
		return conversationModifiers.map((m) => ({
			entity: m.entity,
			action: m.action as 'string-mask' | 'ignore',
			type: m.type || undefined
		}));
	}

	toggleEntityMasking(entityId: string, occurrenceIndex: number, conversationId?: string) {
		// Phase-based toggle: either conversation state OR temporary state, not both
		if (conversationId) {
			// Existing chat: first try to update conversation state (persistent entities)
			const state = this.conversationStates.get(conversationId);
			if (state) {
				const entity = state.entities.find((e) => e.label === entityId);
				if (entity && entity.occurrences[occurrenceIndex]) {
					entity.shouldMask = !entity.shouldMask;
					state.lastUpdated = Date.now();
					this.triggerChatSave(conversationId);
					console.log(
						`PiiSessionManager: Toggled persistent entity ${entityId} shouldMask to ${entity.shouldMask}`
					);
					return; // Successfully updated persistent state
				}
			}

			// If entity not found in persistent state, check working entities
			const workingEntities = this.workingEntitiesForConversations.get(conversationId);
			if (workingEntities) {
				const workingEntity = workingEntities.find((e) => e.label === entityId);
				if (workingEntity && workingEntity.occurrences[occurrenceIndex]) {
					workingEntity.shouldMask = !workingEntity.shouldMask;
					console.log(
						`PiiSessionManager: Toggled working entity ${entityId} shouldMask to ${workingEntity.shouldMask}`
					);
					return; // Successfully updated working state
				}
			}

			console.warn(
				`PiiSessionManager: Entity ${entityId} not found in persistent or working state for conversation ${conversationId}`
			);
		} else if (this.temporaryState.isActive) {
			// New chat: update temporary state
			const entity = this.temporaryState.entities.find((e) => e.label === entityId);
			if (entity && entity.occurrences[occurrenceIndex]) {
				entity.shouldMask = !entity.shouldMask;
				console.log(
					`PiiSessionManager: Toggled temporary entity ${entityId} shouldMask to ${entity.shouldMask}`
				);
			}
		}
	}

	setConversationEntitiesFromLatestDetection(
		conversationId: string,
		entities: PiiEntity[],
		sessionId?: string
	) {
		const existingState = this.conversationStates.get(conversationId);
		const existingEntities = existingState?.entities || [];

		// Convert new entities to extended format with default shouldMask: true
		const newExtendedEntities = entities.map((entity) => {
			// Preserve shouldMask state if entity already exists
			const existingEntity = existingEntities.find((e) => e.label === entity.label);
			return {
				...entity,
				shouldMask: existingEntity?.shouldMask ?? true
			};
		});

		// Update conversation state - simple replacement, no complex merging
		const newState: ConversationPiiState = {
			entities: newExtendedEntities,
			modifiers: existingState?.modifiers || [],
			sessionId: sessionId || existingState?.sessionId,
			apiKey: this.apiKey || existingState?.apiKey,
			lastUpdated: Date.now()
		};

		this.conversationStates.set(conversationId, newState);
		this.errorBackup.set(conversationId, { ...newState });
		this.triggerChatSave(conversationId);
	}

	// Removed getConversationEntitiesForDisplay() - functionality moved to getEntitiesForDisplay()

	clearConversationWorkingEntities(conversationId: string) {
		this.workingEntitiesForConversations.delete(conversationId);
	}

	commitConversationWorkingEntities(conversationId: string) {
		const workingEntities = this.workingEntitiesForConversations.get(conversationId);
		if (workingEntities && workingEntities.length > 0) {
			// Simple addition of new entities to persistent state
			const existingState = this.conversationStates.get(conversationId);
			if (existingState) {
				const updatedEntities = [...existingState.entities, ...workingEntities];
				const newState: ConversationPiiState = {
					...existingState,
					entities: updatedEntities,
					lastUpdated: Date.now()
				};

				this.conversationStates.set(conversationId, newState);
				this.errorBackup.set(conversationId, { ...newState });
				this.triggerChatSave(conversationId);
			}

			// Clear working entities since they're now persistent
			this.clearConversationWorkingEntities(conversationId);
		}
	}

	setConversationWorkingEntitiesWithMaskStates(
		conversationId: string,
		extendedEntities: ExtendedPiiEntity[]
	) {
		// Working state is purely additive - only store NEW entities not already in persistent state
		const persistentEntities = this.conversationStates.get(conversationId)?.entities || [];
		const newEntities = extendedEntities.filter(
			(entity) => !persistentEntities.find((persistent) => persistent.label === entity.label)
		);

		// Only store genuinely new entities in working state
		this.workingEntitiesForConversations.set(conversationId, newEntities);
	}

	setEntityMaskingState(conversationId: string, entityId: string, shouldMask: boolean) {
		// Only update the primary state for this conversation
		const state = this.conversationStates.get(conversationId);
		if (state) {
			const entity = state.entities.find((e) => e.label === entityId);
			if (entity) {
				entity.shouldMask = shouldMask;
				state.lastUpdated = Date.now();
				this.triggerChatSave(conversationId);
			}
		}
	}

	setTemporaryEntityMaskingState(entityId: string, shouldMask: boolean) {
		const entity = this.temporaryState.entities.find((e) => e.label === entityId);
		if (entity) {
			entity.shouldMask = shouldMask;
		}
	}
}

// Get label variations to handle different spellings
function getLabelVariations(label: string): string {
	const labelMap: Record<string, string[]> = {
		ORGANIZATION: ['ORGANIZATION', 'ORGANISATION', 'ORGANIZACION'],
		PERSON: ['PERSON', 'PERSONS', 'PERSONNE'],
		LOCATION: ['LOCATION', 'LIEU', 'LUGAR']
	};

	// Find the canonical form (first matching key or value in the map)
	const canonicalLabel =
		Object.entries(labelMap).find(([, variations]) =>
			variations.includes(label.toUpperCase())
		)?.[0] || label;

	return labelMap[canonicalLabel] ? `(?:${labelMap[canonicalLabel].join('|')})` : label;
}

// Function to detect masked patterns in text and unmask them
export function unmaskTextWithEntities(text: string, entities: ExtendedPiiEntity[]): string {
	if (!text || !entities?.length) return text;

	// Check if text is already highlighted (indicating it's been processed)
	if (text.includes('<span class="pii-highlight')) {
		return text;
	}

	// Replace each masked pattern with its original text
	let unmaskedText = text;
	entities.forEach((entity) => {
		const { label, raw_text: rawText } = entity;

		if (!label || !rawText) return;

		// Extract the base type and ID from the label (e.g., "PERSON_1" -> baseType="PERSON", labelId="1")
		const labelMatch = label.match(/^(.+)_(\d+)$/);
		if (!labelMatch) return;

		const [, baseType, labelId] = labelMatch;
		const labelVariations = getLabelVariations(baseType);

		// Create patterns for the exact label as it appears in masked text
		const labelRegex = new RegExp(
			`\\[\\{${labelVariations}_${labelId}\\}\\]|` + // [{TYPE_ID}]
				`\\[${labelVariations}_${labelId}\\]|` + // [TYPE_ID]
				`\\{${labelVariations}_${labelId}\\}|` + // {TYPE_ID}
				`\\b${labelVariations}_${labelId}\\b`, // TYPE_ID
			'g'
		);

		unmaskedText = unmaskedText.replace(labelRegex, rawText);
	});

	return unmaskedText;
}

// Function to highlight unmasked entities in response text
export function highlightUnmaskedEntities(text: string, entities: ExtendedPiiEntity[]): string {
	if (!entities.length || !text) return text;

	// Check if text is already highlighted to prevent double processing
	if (text.includes('<span class="pii-highlight')) {
		return text;
	}

	let highlightedText = text;

	// Sort entities by text length (longest first) to avoid partial replacements
	const sortedEntities = [...entities].sort((a, b) => b.raw_text.length - a.raw_text.length);

	sortedEntities.forEach((entity) => {
		// Skip entities with empty or invalid raw_text
		if (!entity.raw_text?.trim()) return;

		const escapedText = entity.raw_text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

		// Use global flag but be more careful about word boundaries
		const hasSpecialChars = /[^\w\s]/.test(entity.raw_text);
		const regex = hasSpecialChars
			? new RegExp(escapedText, 'gi')
			: new RegExp(`\\b${escapedText}\\b`, 'gi');

		highlightedText = highlightedText.replace(regex, (match) => {
			const shouldMask = entity.shouldMask ?? true;
			const maskingClass = shouldMask ? 'pii-masked' : 'pii-unmasked';
			const statusText = shouldMask
				? i18next.t('PII Modifier: Was masked in input')
				: i18next.t('PII Modifier: Was NOT masked in input');

			return `<span class="pii-highlight ${maskingClass}" title="${entity.label} - ${statusText}" data-pii-type="${entity.type}" data-pii-label="${entity.label}">${match}</span>`;
		});
	});

	return highlightedText;
}

// Adjust PII entity positions when br tags are removed from text
export function adjustPiiEntityPositionsForDisplay(
	entities: ExtendedPiiEntity[],
	originalHtmlText: string
): ExtendedPiiEntity[] {
	if (!entities.length || !originalHtmlText) return entities;

	// Extract plain text without br tags for comparison
	const textWithoutBrTags = originalHtmlText.replace(/<br\s*\/?>/gi, '');

	// If no br tags were present, no adjustment needed
	if (originalHtmlText === textWithoutBrTags) {
		return entities;
	}

	return entities.map((entity) => {
		const adjustedOccurrences = entity.occurrences.map((occurrence) => {
			// Count br tags before this position in the original text
			const brTagsBeforeStart = countBrTagsBeforePosition(originalHtmlText, occurrence.start_idx);
			const brTagsBeforeEnd = countBrTagsBeforePosition(originalHtmlText, occurrence.end_idx);

			// Each br tag that was removed shifts positions back
			// Estimate br tag length as 4 characters (e.g., "<br>")
			const averageBrTagLength = 4;
			const startAdjustment = brTagsBeforeStart * averageBrTagLength;
			const endAdjustment = brTagsBeforeEnd * averageBrTagLength;

			const adjustedStart = Math.max(0, occurrence.start_idx - startAdjustment);
			const adjustedEnd = Math.max(adjustedStart, occurrence.end_idx - endAdjustment);

			return {
				...occurrence,
				start_idx: adjustedStart,
				end_idx: adjustedEnd
			};
		});

		return {
			...entity,
			occurrences: adjustedOccurrences
		};
	});
}

// Enhanced function to unmask and highlight text with modifier awareness for display
export function unmaskAndHighlightTextForDisplay(
	text: string,
	entities: ExtendedPiiEntity[]
): string {
	if (!entities.length || !text) return text;

	// Check if text is already processed to prevent double processing
	if (text.includes('<span class="pii-highlight')) {
		return text;
	}

	let processedText = text;

	const sortedEntities = [...entities].sort((a, b) => b.raw_text.length - a.raw_text.length);

	// Step 1: Unmask all patterns and simultaneously replace with highlighted spans
	sortedEntities.forEach((entity) => {
		const { label, raw_text: rawText } = entity;

		if (!label || !rawText) {
			return;
		}

		if (entity.shouldMask) {
			// Extract the base type and ID from the label
			const labelMatch = label.match(/^(.+)_(\d+)$/);
			if (!labelMatch) {
				return;
			}

			const [, baseType, labelId] = labelMatch;
			const labelVariations = getLabelVariations(baseType);

			// Create comprehensive patterns for masked text
			const patterns = [
				`\\[\\{${labelVariations}_${labelId}\\}\\]`, // [{TYPE_ID}]
				`\\[${labelVariations}_${labelId}\\]`, // [TYPE_ID]
				`\\{${labelVariations}_${labelId}\\}`, // {TYPE_ID}
				`${labelVariations}_${labelId}(?=\\s|$|[^\\w])` // TYPE_ID as word boundary
			];

			// Use case-insensitive matching and global flag
			const labelRegex = new RegExp(patterns.join('|'), 'gi');

			// Replace masked patterns with highlighted spans containing the original text
			const beforeReplace = processedText;
			processedText = processedText.replace(labelRegex, () => {
				const shouldMask = entity.shouldMask ?? true;
				const maskingClass = shouldMask ? 'pii-masked' : 'pii-unmasked';
				const statusText = shouldMask
					? i18next.t('PII Modifier: Was masked in input')
					: i18next.t('PII Modifier: Was NOT masked in input');

				return `<span class="pii-highlight ${maskingClass}" title="${entity.label} - ${statusText}" data-pii-type="${entity.type}" data-pii-label="${entity.label}">${rawText}</span>`;
			});

			if (beforeReplace !== processedText) {
				//replacementsMade++;
			}
		} else {
			// Skip entities with empty or invalid raw_text
			if (!entity.raw_text?.trim()) {
				return;
			}

			// Escape special regex characters and create pattern
			const escapedText = entity.raw_text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

			// Use word boundaries for better matching, but handle special characters gracefully
			const hasSpecialChars = /[^\w\s]/.test(entity.raw_text);
			const regex = hasSpecialChars
				? new RegExp(escapedText, 'gi')
				: new RegExp(`\\b${escapedText}\\b`, 'gi');

			const beforeReplace = processedText;
			processedText = processedText.replace(regex, (match) => {
				const shouldMask = entity.shouldMask ?? true;
				const maskingClass = shouldMask ? 'pii-masked' : 'pii-unmasked';
				const statusText = shouldMask
					? i18next.t('PII Modifier: Was masked in input')
					: i18next.t('PII Modifier: Was NOT masked in input');

				return `<span class="pii-highlight ${maskingClass}" title="${entity.label} - ${statusText}" data-pii-type="${entity.type}" data-pii-label="${entity.label}">${match}</span>`;
			});

			if (beforeReplace !== processedText) {
				//replacementsMade++;
			}
		}
	});

	return processedText;
}
