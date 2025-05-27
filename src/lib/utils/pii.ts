import type { PiiEntity } from '$lib/apis/pii';

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
function countBrTagsBeforePosition(html: string, plainTextPos: number): number {
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
export function convertMaskedTextToEditor(maskedText: string, originalHtml: string): string {
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
	let styles = `
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

	return styles;
}

// Convert hex color to rgba
function hexToRgba(hex: string, alpha: number): string {
	const r = parseInt(hex.slice(1, 3), 16);
	const g = parseInt(hex.slice(3, 5), 16);
	const b = parseInt(hex.slice(5, 7), 16);
	return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Conversation-specific PII state for storing with chat data
export interface ConversationPiiState {
	entities: ExtendedPiiEntity[];
	sessionId?: string;
	apiKey?: string;
	lastUpdated: number;
}

// Store for PII session management
export class PiiSessionManager {
	private static instance: PiiSessionManager;
	private sessionId: string | null = null;
	private entities: ExtendedPiiEntity[] = [];
	private apiKey: string | null = null;
	// Conversation-specific storage
	private conversationStates: Map<string, ConversationPiiState> = new Map();

	static getInstance(): PiiSessionManager {
		if (!PiiSessionManager.instance) {
			PiiSessionManager.instance = new PiiSessionManager();
		}
		return PiiSessionManager.instance;
	}

	setApiKey(apiKey: string) {
		this.apiKey = apiKey;
	}

	getApiKey(): string | null {
		return this.apiKey;
	}

	setSession(sessionId: string) {
		this.sessionId = sessionId;
	}

	getSession(): string | null {
		return this.sessionId;
	}

	// Set entities for the current global session (backwards compatibility)
	setEntities(entities: PiiEntity[]) {
		// Convert to extended entities with default masking enabled
		this.entities = entities.map((entity) => ({
			...entity,
			shouldMask: true // Default to masking enabled
		}));
	}

	// Get entities for the current global session (backwards compatibility)
	getEntities(): ExtendedPiiEntity[] {
		return this.entities;
	}

	// Conversation-specific methods
	setConversationEntities(conversationId: string, entities: PiiEntity[], sessionId?: string) {
		const newExtendedEntities = entities.map((entity) => ({
			...entity,
			shouldMask: true // Default to masking enabled
		}));

		// Get existing entities for this conversation
		const existingState = this.conversationStates.get(conversationId);
		const existingEntities = existingState?.entities || [];

		// Merge new entities with existing ones, avoiding duplicates by label
		const mergedEntities = [...existingEntities];

		console.log(
			`PiiSessionManager: Merging ${newExtendedEntities.length} new entities with ${existingEntities.length} existing entities for conversation: ${conversationId}`
		);

		newExtendedEntities.forEach((newEntity) => {
			const existingIndex = mergedEntities.findIndex((e) => e.label === newEntity.label);
			if (existingIndex >= 0) {
				// Update existing entity (preserve shouldMask state)
				console.log(`PiiSessionManager: Updating existing entity: ${newEntity.label}`);
				mergedEntities[existingIndex] = {
					...newEntity,
					shouldMask: mergedEntities[existingIndex].shouldMask
				};
			} else {
				// Add new entity
				console.log(`PiiSessionManager: Adding new entity: ${newEntity.label}`);
				mergedEntities.push(newEntity);
			}
		});

		console.log(`PiiSessionManager: Final merged entities count: ${mergedEntities.length}`);

		this.conversationStates.set(conversationId, {
			entities: mergedEntities,
			sessionId: sessionId || existingState?.sessionId,
			apiKey: this.apiKey || existingState?.apiKey,
			lastUpdated: Date.now()
		});

		// Also update global state for current conversation
		this.entities = mergedEntities;
		if (sessionId) {
			this.sessionId = sessionId;
		}
	}

	getConversationEntities(conversationId: string): ExtendedPiiEntity[] {
		const state = this.conversationStates.get(conversationId);
		return state?.entities || [];
	}

	getConversationState(conversationId: string): ConversationPiiState | null {
		return this.conversationStates.get(conversationId) || null;
	}

	// Load conversation state from localStorage (chat data)
	loadConversationState(conversationId: string, piiState?: ConversationPiiState) {
		if (piiState) {
			this.conversationStates.set(conversationId, piiState);
			// Set as current global state
			this.entities = piiState.entities;
			this.sessionId = piiState.sessionId || null;
			this.apiKey = piiState.apiKey || this.apiKey;
		}
	}

	// Get state for saving to localStorage (chat data)
	getConversationStateForStorage(conversationId: string): ConversationPiiState | null {
		return this.conversationStates.get(conversationId) || null;
	}

	// Convert conversation entities to known entities format for API
	getKnownEntitiesForApi(
		conversationId: string
	): Array<{ id: number; label: string; name: string }> {
		const entities = this.getConversationEntities(conversationId);
		return entities.map((entity) => ({
			id: entity.id,
			label: entity.label,
			name: entity.raw_text
		}));
	}

	// Toggle entity masking for specific conversation
	toggleConversationEntityMasking(
		conversationId: string,
		entityId: string,
		occurrenceIndex: number
	) {
		const state = this.conversationStates.get(conversationId);
		if (state) {
			const entity = state.entities.find((e) => e.label === entityId);
			if (entity && entity.occurrences[occurrenceIndex]) {
				entity.shouldMask = !entity.shouldMask;
				state.lastUpdated = Date.now();

				// Update global state if this is the current conversation
				const globalEntity = this.entities.find((e) => e.label === entityId);
				if (globalEntity) {
					globalEntity.shouldMask = entity.shouldMask;
				}
			}
		}
	}

	// Backwards compatibility
	toggleEntityMasking(entityId: string, occurrenceIndex: number) {
		const entity = this.entities.find((e) => e.label === entityId);
		if (entity && entity.occurrences[occurrenceIndex]) {
			entity.shouldMask = !entity.shouldMask;
		}
	}

	getEntityMaskingState(entityId: string): boolean {
		const entity = this.entities.find((e) => e.label === entityId);
		return entity?.shouldMask ?? true;
	}

	clearSession() {
		this.sessionId = null;
		this.entities = [];
	}

	// Clear conversation-specific state
	clearConversationState(conversationId: string) {
		this.conversationStates.delete(conversationId);
	}

	// Clear all conversation states
	clearAllConversationStates() {
		this.conversationStates.clear();
	}
}

// Get label variations to handle different spellings
function getLabelVariations(label: string): string {
	const labelMap: Record<string, string[]> = {
		ORGANIZATION: ['ORGANIZATION', 'ORGANISATION', 'ORGANIZACION'],
		PERSON: ['PERSON', 'PERSONS', 'PERSONNE'],
		LOCATION: ['LOCATION', 'LIEU', 'LUGAR']
		// Add more mappings as needed
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
	if (!text) return '';
	if (!entities || !entities.length) return text;

	// Replace each masked pattern with its original text
	let unmaskedText = text;
	entities.forEach((entity) => {
		const { label } = entity;
		// Use entity.raw_text as the raw text for unmasking
		const rawText = entity.raw_text;

		if (!label || !rawText) return;

		// Extract the base type and ID from the label (e.g., "PERSON_1" -> baseType="PERSON", labelId="1")
		const labelMatch = label.match(/^(.+)_(\d+)$/);
		if (!labelMatch) return; // Skip if label doesn't match expected format

		const [, baseType, labelId] = labelMatch;
		const labelVariations = getLabelVariations(baseType);

		// Create patterns for the exact label as it appears in masked text
		// The pattern should be {baseType_labelId}, not {baseType_entity.id}
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
	if (!entities.length) return text;

	let highlightedText = text;

	// Sort entities by text length (longest first) to avoid partial replacements
	const sortedEntities = [...entities].sort((a, b) => b.raw_text.length - a.raw_text.length);

	sortedEntities.forEach((entity) => {
		const escapedText = entity.raw_text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
		const regex = new RegExp(`\\b${escapedText}\\b`, 'gi');

		highlightedText = highlightedText.replace(regex, (match) => {
			const shouldMask = entity.shouldMask ?? true;
			const maskingClass = shouldMask ? 'pii-masked' : 'pii-unmasked';
			const statusText = shouldMask ? 'Was masked in input' : 'Was NOT masked in input';

			return `<span class="pii-highlight ${maskingClass}" title="${entity.label} (${entity.type}) - ${statusText}" data-pii-type="${entity.type}" data-pii-label="${entity.label}">${match}</span>`;
		});
	});

	return highlightedText;
}
