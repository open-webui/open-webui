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

// Import PiiModifier type
import type { PiiModifier } from '$lib/components/common/RichTextInput/PiiModifierExtension';

// Conversation-specific PII state for storing with chat data
export interface ConversationPiiState {
	entities: ExtendedPiiEntity[];
	modifiers: PiiModifier[];  // Add modifiers to conversation state
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
	// Global state for before conversation ID exists
	private globalModifiers: PiiModifier[] = [];
	// Conversation-specific storage
	private conversationStates: Map<string, ConversationPiiState> = new Map();
	// Initialization guards
	private localStorageInitialized = false;
	private loadingConversations = new Set<string>(); // Track conversations currently being loaded

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
		// Save to localStorage
		this.saveGlobalEntitiesToLocalStorage();
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
			modifiers: existingState?.modifiers || [],
			sessionId: sessionId || existingState?.sessionId,
			apiKey: this.apiKey || existingState?.apiKey,
			lastUpdated: Date.now()
		});

		// Also update global state for current conversation
		this.entities = mergedEntities;
		if (sessionId) {
			this.sessionId = sessionId;
		}
		
		// Save to localStorage
		this.saveConversationToLocalStorage(conversationId);
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
		// Prevent loading the same conversation multiple times simultaneously
		if (this.loadingConversations.has(conversationId)) {
			console.log(`PiiSessionManager: Already loading conversation ${conversationId}, skipping`);
			return;
		}
		
		// Check if conversation is already loaded
		if (this.conversationStates.has(conversationId) && !piiState) {
			console.log(`PiiSessionManager: Conversation ${conversationId} already loaded, skipping`);
			return;
		}
		
		this.loadingConversations.add(conversationId);
		
		try {
			let stateToLoad = piiState;
			
			// If no piiState provided, try loading from localStorage
			if (!stateToLoad) {
				stateToLoad = this.loadConversationFromLocalStorage(conversationId) || undefined;
			}
			
			if (stateToLoad) {
				this.conversationStates.set(conversationId, stateToLoad);
				// Set as current global state
				this.entities = stateToLoad.entities;
				this.sessionId = (stateToLoad.sessionId as string) || null;
				this.apiKey = stateToLoad.apiKey || this.apiKey;
				console.log(`PiiSessionManager: Loaded conversation ${conversationId} state - ${stateToLoad.entities.length} entities, ${stateToLoad.modifiers.length} modifiers`);
			} else {
				console.log(`PiiSessionManager: No state found for conversation ${conversationId}`);
			}
		} finally {
			this.loadingConversations.delete(conversationId);
		}
	}

	// Activate conversation - loads conversation-specific modifiers and entities into working state
	activateConversation(conversationId: string): boolean {
		console.log(`PiiSessionManager: Activating conversation ${conversationId}`);
		
		// First ensure the conversation state is loaded
		this.loadConversationState(conversationId);
		
		const conversationState = this.conversationStates.get(conversationId);
		if (!conversationState) {
			console.log(`PiiSessionManager: No state available for conversation ${conversationId}`);
			return false;
		}
		
		// Load conversation's entities and modifiers into working state
		this.entities = [...conversationState.entities]; // Copy to avoid reference issues
		
		// Clear global modifiers and set conversation modifiers as active
		// This ensures extensions work with the correct conversation-specific modifiers
		this.globalModifiers = []; // Clear global modifiers
		
		console.log(`PiiSessionManager: Activated conversation ${conversationId} - ${conversationState.entities.length} entities, ${conversationState.modifiers.length} modifiers loaded into working state`);
		
		return true;
	}

	// Get active modifiers (for extensions to use)
	// This should be used by extensions instead of getGlobalModifiers/getConversationModifiers
	getActiveModifiers(conversationId?: string): PiiModifier[] {
		if (conversationId) {
			const conversationState = this.conversationStates.get(conversationId);
			if (conversationState) {
				console.log(`PiiSessionManager: Retrieved ${conversationState.modifiers.length} active modifiers for conversation ${conversationId}`);
				return conversationState.modifiers;
			}
		}
		
		// Fallback to global modifiers
		console.log(`PiiSessionManager: Retrieved ${this.globalModifiers.length} global modifiers as fallback`);
		return this.globalModifiers;
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
		const knownEntities = entities.map((entity) => ({
			id: entity.id,
			label: entity.label,
			name: entity.raw_text
		}));
		console.log(`PiiSessionManager: Retrieved ${knownEntities.length} known entities for conversation ${conversationId}`);
		return knownEntities;
	}

	// Convert global entities to known entities format for API
	getGlobalKnownEntitiesForApi(): Array<{ id: number; label: string; name: string }> {
		const entities = this.getEntities();
		const knownEntities = entities.map((entity) => ({
			id: entity.id,
			label: entity.label,
			name: entity.raw_text
		}));
		console.log(`PiiSessionManager: Retrieved ${knownEntities.length} global known entities`);
		return knownEntities;
	}

	// MODIFIER MANAGEMENT METHODS

	// Get modifiers for conversation
	getConversationModifiers(conversationId: string): PiiModifier[] {
		const state = this.conversationStates.get(conversationId);
		return state?.modifiers || [];
	}

	// Get global modifiers (before conversation ID exists)
	getGlobalModifiers(): PiiModifier[] {
		return this.globalModifiers;
	}

	// Set conversation modifiers
	setConversationModifiers(conversationId: string, modifiers: PiiModifier[]) {
		const existingState = this.conversationStates.get(conversationId);
		this.conversationStates.set(conversationId, {
			entities: existingState?.entities || [],
			modifiers: modifiers,
			sessionId: existingState?.sessionId,
			apiKey: existingState?.apiKey || this.apiKey || undefined,
			lastUpdated: Date.now()
		});
		console.log(`PiiSessionManager: Set ${modifiers.length} modifiers for conversation ${conversationId}`);
		// Save to localStorage
		this.saveConversationToLocalStorage(conversationId);
	}

	// Set global modifiers (before conversation ID exists)
	setGlobalModifiers(modifiers: PiiModifier[]) {
		this.globalModifiers = modifiers;
		console.log(`PiiSessionManager: Set ${modifiers.length} global modifiers`);
		// Save to localStorage
		this.saveGlobalModifiersToLocalStorage();
	}

	// Transfer global state to conversation state when conversation ID becomes available
	transferGlobalToConversation(conversationId: string) {
		console.log(`PiiSessionManager: Transferring global state to conversation ${conversationId}`);
		
		// Create initial conversation state with global data
		this.conversationStates.set(conversationId, {
			entities: [...this.entities], // Copy global entities
			modifiers: [...this.globalModifiers], // Copy global modifiers
			sessionId: this.sessionId || undefined,
			apiKey: this.apiKey || undefined,
			lastUpdated: Date.now()
		});

		console.log(`PiiSessionManager: Transferred ${this.entities.length} entities and ${this.globalModifiers.length} modifiers to conversation ${conversationId}`);

		// Save the conversation state to localStorage first
		this.saveConversationToLocalStorage(conversationId);

		// Clear global state since we now have a conversation ID
		this.globalModifiers = [];
		// Keep entities as they might be needed for display

		// Clear global localStorage keys after successful transfer
		this.clearGlobalLocalStorage();
		console.log(`PiiSessionManager: Cleared global localStorage keys after transfer to conversation ${conversationId}`);
	}

	// Ensure conversation state is loaded (synchronous)
	private ensureConversationLoaded(conversationId: string): boolean {
		if (this.conversationStates.has(conversationId)) {
			return true;
		}
		
		console.log(`PiiSessionManager: Loading conversation ${conversationId} from localStorage`);
		
		// Try to load from localStorage
		const stateFromStorage = this.loadConversationFromLocalStorage(conversationId);
		if (stateFromStorage) {
			this.conversationStates.set(conversationId, stateFromStorage);
			return true;
		}
		
		console.warn(`PiiSessionManager: No state found for conversation ${conversationId}`);
		return false;
	}

	// Get modifiers for API (works for both global and conversation state)
	getModifiersForApi(conversationId?: string): any[] {
		if (conversationId) {
			// Ensure conversation is loaded
			this.ensureConversationLoaded(conversationId);
			
			const conversationModifiers = this.getConversationModifiers(conversationId);
			console.log(`PiiSessionManager: Retrieved ${conversationModifiers.length} conversation modifiers for ${conversationId}`);
			return conversationModifiers.map(m => ({
				entity: m.entity,
				action: m.action,
				type: m.type || undefined
			}));
		} else {
			const globalModifiers = this.getGlobalModifiers();
			console.log(`PiiSessionManager: Retrieved ${globalModifiers.length} global modifiers`);
			return globalModifiers.map(m => ({
				entity: m.entity,
				action: m.action,
				type: m.type || undefined
			}));
		}
	}

	// Add entities from API response that includes modifier-created entities
	// This ensures modifier-created entities become known entities for future calls
	appendConversationEntities(conversationId: string, newEntities: PiiEntity[], sessionId?: string) {
		const existingState = this.conversationStates.get(conversationId);
		const existingEntities = existingState?.entities || [];
		
		console.log(`PiiSessionManager: Appending ${newEntities.length} entities to conversation ${conversationId}`);
		
		// Convert new entities to extended format
		const newExtendedEntities = newEntities.map((entity) => ({
			...entity,
			shouldMask: true // Default to masking enabled for new entities
		}));

		// Create a map of existing entities by label for quick lookup
		const existingEntityMap = new Map<string, ExtendedPiiEntity>();
		existingEntities.forEach(entity => {
			existingEntityMap.set(entity.label, entity);
		});

		// Merge new entities, preserving shouldMask state for existing ones
		const mergedEntities: ExtendedPiiEntity[] = [];
		
		// Add all existing entities first
		existingEntities.forEach(entity => {
			mergedEntities.push(entity);
		});

		// Add new entities, updating existing ones or adding truly new ones
		newExtendedEntities.forEach((newEntity) => {
			const existingEntity = existingEntityMap.get(newEntity.label);
			if (existingEntity) {
				// Update existing entity but preserve shouldMask state
				console.log(`PiiSessionManager: Updating existing entity: ${newEntity.label}`);
				const existingIndex = mergedEntities.findIndex(e => e.label === newEntity.label);
				if (existingIndex >= 0) {
					mergedEntities[existingIndex] = {
						...newEntity,
						shouldMask: existingEntity.shouldMask // Preserve existing shouldMask state
					};
				}
			} else {
				// Add truly new entity
				console.log(`PiiSessionManager: Adding new entity: ${newEntity.label} (possibly from modifier)`);
				mergedEntities.push(newEntity);
			}
		});

		console.log(`PiiSessionManager: Final entity count after append: ${mergedEntities.length}`);

		// Update conversation state
		this.conversationStates.set(conversationId, {
			entities: mergedEntities,
			modifiers: existingState?.modifiers || [],
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

	// Append entities to global state (backwards compatibility)
	appendGlobalEntities(newEntities: PiiEntity[]) {
		const newExtendedEntities = newEntities.map((entity) => ({
			...entity,
			shouldMask: true
		}));

		// Create a map of existing entities by label for quick lookup
		const existingEntityMap = new Map<string, ExtendedPiiEntity>();
		this.entities.forEach(entity => {
			existingEntityMap.set(entity.label, entity);
		});

		// Merge entities, preserving shouldMask state for existing ones
		const mergedEntities: ExtendedPiiEntity[] = [...this.entities];
		
		newExtendedEntities.forEach((newEntity) => {
			const existingEntity = existingEntityMap.get(newEntity.label);
			if (existingEntity) {
				// Update existing entity but preserve shouldMask state
				const existingIndex = mergedEntities.findIndex(e => e.label === newEntity.label);
				if (existingIndex >= 0) {
					mergedEntities[existingIndex] = {
						...newEntity,
						shouldMask: existingEntity.shouldMask
					};
				}
			} else {
				// Add new entity
				mergedEntities.push(newEntity);
			}
		});

		this.entities = mergedEntities;
		// Save to localStorage
		this.saveGlobalEntitiesToLocalStorage();
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
				
				// Save to localStorage
				this.saveConversationToLocalStorage(conversationId);
				this.saveGlobalEntitiesToLocalStorage();
			}
		}
	}

	// Backwards compatibility
	toggleEntityMasking(entityId: string, occurrenceIndex: number) {
		const entity = this.entities.find((e) => e.label === entityId);
		if (entity && entity.occurrences[occurrenceIndex]) {
			entity.shouldMask = !entity.shouldMask;
			// Save to localStorage
			this.saveGlobalEntitiesToLocalStorage();
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

	// ==== LOCALSTORAGE PERSISTENCE METHODS ====

	/**
	 * Save global entities to localStorage
	 */
	private saveGlobalEntitiesToLocalStorage(): void {
		try {
			localStorage.setItem('pii-known-entities', JSON.stringify(this.entities));
			console.log(`PiiSessionManager: Saved ${this.entities.length} global entities to localStorage`);
		} catch (error) {
			console.error('PiiSessionManager: Failed to save global entities to localStorage:', error);
		}
	}

	/**
	 * Load global entities from localStorage
	 */
	private loadGlobalEntitiesFromLocalStorage(): void {
		try {
			const stored = localStorage.getItem('pii-known-entities');
			if (stored) {
				this.entities = JSON.parse(stored);
				console.log(`PiiSessionManager: Loaded ${this.entities.length} global entities from localStorage`);
			}
		} catch (error) {
			console.error('PiiSessionManager: Failed to load global entities from localStorage:', error);
			this.entities = [];
		}
	}

	/**
	 * Save global modifiers to localStorage
	 */
	private saveGlobalModifiersToLocalStorage(): void {
		try {
			localStorage.setItem('pii-modifiers', JSON.stringify(this.globalModifiers));
			console.log(`PiiSessionManager: Saved ${this.globalModifiers.length} global modifiers to localStorage`);
		} catch (error) {
			console.error('PiiSessionManager: Failed to save global modifiers to localStorage:', error);
		}
	}

	/**
	 * Load global modifiers from localStorage
	 */
	private loadGlobalModifiersFromLocalStorage(): void {
		try {
			const stored = localStorage.getItem('pii-modifiers');
			if (stored) {
				this.globalModifiers = JSON.parse(stored);
				console.log(`PiiSessionManager: Loaded ${this.globalModifiers.length} global modifiers from localStorage`);
			}
		} catch (error) {
			console.error('PiiSessionManager: Failed to load global modifiers from localStorage:', error);
			this.globalModifiers = [];
		}
	}

	/**
	 * Save conversation-specific state to localStorage
	 */
	private saveConversationToLocalStorage(conversationId: string): void {
		const state = this.conversationStates.get(conversationId);
		if (!state) return;

		try {
			// Save entities
			localStorage.setItem(
				`pii-known-entities-${conversationId}`, 
				JSON.stringify(state.entities)
			);
			
			// Save modifiers
			localStorage.setItem(
				`pii-modifiers-${conversationId}`, 
				JSON.stringify(state.modifiers)
			);
			
			console.log(`PiiSessionManager: Saved conversation ${conversationId} to localStorage - ${state.entities.length} entities, ${state.modifiers.length} modifiers`);
		} catch (error) {
			console.error(`PiiSessionManager: Failed to save conversation ${conversationId} to localStorage:`, error);
		}
	}

	/**
	 * Load conversation-specific state from localStorage
	 */
	private loadConversationFromLocalStorage(conversationId: string): ConversationPiiState | null {
		try {
			const entitiesStored = localStorage.getItem(`pii-known-entities-${conversationId}`);
			const modifiersStored = localStorage.getItem(`pii-modifiers-${conversationId}`);
			
			console.log(`PiiSessionManager: Loading conversation ${conversationId} from localStorage`);
			console.log(`PiiSessionManager: Entities localStorage key exists:`, !!entitiesStored);
			console.log(`PiiSessionManager: Modifiers localStorage key exists:`, !!modifiersStored);
			
			if (modifiersStored) {
				console.log(`PiiSessionManager: Raw modifiers from localStorage:`, modifiersStored);
			}
			
			if (entitiesStored || modifiersStored) {
				const entities: ExtendedPiiEntity[] = entitiesStored ? JSON.parse(entitiesStored) : [];
				const modifiers: PiiModifier[] = modifiersStored ? JSON.parse(modifiersStored) : [];
				
				console.log(`PiiSessionManager: Loaded conversation ${conversationId} from localStorage - ${entities.length} entities, ${modifiers.length} modifiers`);
				console.log(`PiiSessionManager: Loaded modifiers:`, modifiers);
				
				return {
					entities,
					modifiers,
					sessionId: this.sessionId ?? undefined,
					apiKey: this.apiKey ?? undefined,
					lastUpdated: Date.now()
				};
			}
		} catch (error) {
			console.error(`PiiSessionManager: Failed to load conversation ${conversationId} from localStorage:`, error);
		}
		
		console.log(`PiiSessionManager: No localStorage data found for conversation ${conversationId}`);
		return null;
	}

	/**
	 * Clear localStorage for specific conversation
	 */
	clearConversationLocalStorage(conversationId: string): void {
		try {
			localStorage.removeItem(`pii-known-entities-${conversationId}`);
			localStorage.removeItem(`pii-modifiers-${conversationId}`);
			console.log(`PiiSessionManager: Cleared localStorage for conversation ${conversationId}`);
		} catch (error) {
			console.error(`PiiSessionManager: Failed to clear localStorage for conversation ${conversationId}:`, error);
		}
	}

	/**
	 * Clear global localStorage
	 */
	clearGlobalLocalStorage(): void {
		try {
			localStorage.removeItem('pii-known-entities');
			localStorage.removeItem('pii-modifiers');
			console.log('PiiSessionManager: Cleared global localStorage');
		} catch (error) {
			console.error('PiiSessionManager: Failed to clear global localStorage:', error);
		}
	}

	/**
	 * Initialize localStorage state - call this on app startup
	 */
	initializeFromLocalStorage(): void {
		if (this.localStorageInitialized) {
			console.log('PiiSessionManager: localStorage already initialized, skipping');
			return;
		}
		
		console.log('PiiSessionManager: Initializing from localStorage');
		this.loadGlobalEntitiesFromLocalStorage();
		this.loadGlobalModifiersFromLocalStorage();
		this.localStorageInitialized = true;
	}

	/**
	 * Force sync conversation state from localStorage
	 */
	syncConversationFromLocalStorage(conversationId: string): void {
		console.log(`PiiSessionManager: Force syncing conversation ${conversationId} from localStorage`);
		const state = this.loadConversationFromLocalStorage(conversationId);
		if (state) {
			this.conversationStates.set(conversationId, state);
			// Update global state to match
			this.entities = state.entities;
			console.log(`PiiSessionManager: Synced conversation ${conversationId} - ${state.entities.length} entities, ${state.modifiers.length} modifiers`);
		} else {
			console.log(`PiiSessionManager: No localStorage data found for conversation ${conversationId}`);
		}
	}

	/**
	 * Initialize conversation-specific localStorage keys (mirrors chat-input pattern)
	 * Call this when conversation ID becomes available to create the localStorage keys
	 */
	initializeConversationLocalStorage(conversationId: string): void {
		console.log(`PiiSessionManager: Initializing localStorage keys for conversation ${conversationId}`);
		
		// Check if conversation-specific keys already exist
		const existingEntities = localStorage.getItem(`pii-known-entities-${conversationId}`);
		const existingModifiers = localStorage.getItem(`pii-modifiers-${conversationId}`);
		
		if (!existingEntities && !existingModifiers) {
			// No conversation-specific data exists, transfer global state
			console.log(`PiiSessionManager: Creating new localStorage keys for conversation ${conversationId}`);
			
			// Transfer global state to conversation state 
			this.transferGlobalToConversation(conversationId);
			
			// Ensure the localStorage keys are created (even if empty)
			this.saveConversationToLocalStorage(conversationId);
		} else {
			// Conversation data exists, load it
			console.log(`PiiSessionManager: Loading existing localStorage data for conversation ${conversationId}`);
			this.loadConversationState(conversationId);
		}
		
		console.log(`PiiSessionManager: Conversation ${conversationId} localStorage keys initialized`);
	}

	/**
	 * Verify that conversation localStorage keys exist (useful for testing)
	 */
	verifyConversationKeys(conversationId: string): { entities: boolean; modifiers: boolean } {
		const entitiesExist = localStorage.getItem(`pii-known-entities-${conversationId}`) !== null;
		const modifiersExist = localStorage.getItem(`pii-modifiers-${conversationId}`) !== null;
		
		console.log(`PiiSessionManager: Conversation ${conversationId} localStorage keys:`, {
			entities: entitiesExist ? '✅' : '❌',
			modifiers: modifiersExist ? '✅' : '❌'
		});
		
		return { entities: entitiesExist, modifiers: modifiersExist };
	}

	/**
	 * Debug method to check localStorage contents
	 */
	debugLocalStorage(conversationId?: string): void {
		console.log('=== PII localStorage Debug ===');
		
		// Global state
		const globalEntities = localStorage.getItem('pii-known-entities');
		const globalModifiers = localStorage.getItem('pii-modifiers');
		
		console.log('Global entities in localStorage:', globalEntities ? JSON.parse(globalEntities).length : 0);
		console.log('Global modifiers in localStorage:', globalModifiers ? JSON.parse(globalModifiers).length : 0);
		
		// Memory state
		console.log('Entities in memory:', this.entities.length);
		console.log('Global modifiers in memory:', this.globalModifiers.length);
		
		// Conversation-specific state
		if (conversationId) {
			const convEntities = localStorage.getItem(`pii-known-entities-${conversationId}`);
			const convModifiers = localStorage.getItem(`pii-modifiers-${conversationId}`);
			
			console.log(`Conversation ${conversationId} entities in localStorage:`, convEntities ? JSON.parse(convEntities).length : 0);
			console.log(`Conversation ${conversationId} modifiers in localStorage:`, convModifiers ? JSON.parse(convModifiers).length : 0);
			
			const convState = this.conversationStates.get(conversationId);
			console.log(`Conversation ${conversationId} state in memory:`, convState ? {
				entities: convState.entities.length,
				modifiers: convState.modifiers.length
			} : 'not loaded');
		}
		
		console.log('=== End Debug ===');
	}

	/**
	 * Test method to verify the full transfer flow
	 */
	testTransferFlow(conversationId: string): void {
		console.log(`=== Testing Transfer Flow for ${conversationId} ===`);
		
		// Step 1: Check initial global state
		console.log('Step 1 - Initial global state:');
		console.log('- Global modifiers:', this.globalModifiers.length);
		console.log('- Global entities:', this.entities.length);
		
		// Step 2: Transfer to conversation
		console.log('Step 2 - Transferring to conversation...');
		this.transferGlobalToConversation(conversationId);
		
		// Step 3: Check conversation state in memory
		console.log('Step 3 - Conversation state in memory:');
		const memoryState = this.conversationStates.get(conversationId);
		console.log('- Memory state exists:', !!memoryState);
		if (memoryState) {
			console.log('- Memory modifiers:', memoryState.modifiers.length);
			console.log('- Memory entities:', memoryState.entities.length);
		}
		
		// Step 4: Check localStorage
		console.log('Step 4 - localStorage state:');
		const storageState = this.loadConversationFromLocalStorage(conversationId);
		console.log('- Storage state exists:', !!storageState);
		if (storageState) {
			console.log('- Storage modifiers:', storageState.modifiers.length);
			console.log('- Storage entities:', storageState.entities.length);
		}
		
		// Step 5: Test API access
		console.log('Step 5 - API access test:');
		const apiModifiers = this.getModifiersForApi(conversationId);
		console.log('- API modifiers returned:', apiModifiers.length);
		
		console.log('=== End Transfer Flow Test ===');
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

	// Check if text is already highlighted (indicating it's been processed)
	if (text.includes('<span class="pii-highlight')) {
		console.log('PII: Text already highlighted, skipping unmasking');
		return text;
	}

	// Replace each masked pattern with its original text
	let unmaskedText = text;
	entities.forEach((entity) => {
		const { label } = entity;
		// Use entity.raw_text as the raw text for unmasking
		const rawText = entity.raw_text;

		if (!label || !rawText) {
			console.log('PII: Skipping entity with missing label or rawText:', { label, rawText });
			return;
		}

		// Extract the base type and ID from the label (e.g., "PERSON_1" -> baseType="PERSON", labelId="1")
		const labelMatch = label.match(/^(.+)_(\d+)$/);
		if (!labelMatch) {
			console.log('PII: Skipping entity with invalid label format:', label);
			return; // Skip if label doesn't match expected format
		}

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
		
		console.log('PII: Unmasking entity', label, 'pattern:', labelRegex.source, 'with text:', rawText);
		const originalLength = unmaskedText.length;
		unmaskedText = unmaskedText.replace(labelRegex, rawText);
		
		if (unmaskedText.length !== originalLength) {
			console.log('PII: Successfully unmasked', label);
		}
	});

	return unmaskedText;
}

// Function to highlight unmasked entities in response text
export function highlightUnmaskedEntities(text: string, entities: ExtendedPiiEntity[]): string {
	if (!entities.length || !text) return text;

	// Check if text is already highlighted to prevent double processing
	if (text.includes('<span class="pii-highlight')) {
		console.log('PII: Text already highlighted, skipping');
		return text;
	}

	let highlightedText = text;

	// Sort entities by text length (longest first) to avoid partial replacements
	const sortedEntities = [...entities].sort((a, b) => b.raw_text.length - a.raw_text.length);

	sortedEntities.forEach((entity) => {
		// Skip entities with empty or invalid raw_text
		if (!entity.raw_text || entity.raw_text.trim() === '') {
			console.log('PII: Skipping entity with empty raw_text:', entity.label);
			return;
		}

		const escapedText = entity.raw_text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
		
		// Use global flag but be more careful about word boundaries
		// Don't use word boundaries if the text contains special characters
		const hasSpecialChars = /[^\w\s]/.test(entity.raw_text);
		const regex = hasSpecialChars 
			? new RegExp(escapedText, 'gi')
			: new RegExp(`\\b${escapedText}\\b`, 'gi');

		console.log('PII: Highlighting entity', entity.label, 'with text:', entity.raw_text);

		highlightedText = highlightedText.replace(regex, (match) => {
			const shouldMask = entity.shouldMask ?? true;
			const maskingClass = shouldMask ? 'pii-masked' : 'pii-unmasked';
			const statusText = shouldMask ? 'Was masked in input' : 'Was NOT masked in input';

			return `<span class="pii-highlight ${maskingClass}" title="${entity.label} (${entity.type}) - ${statusText}" data-pii-type="${entity.type}" data-pii-label="${entity.label}">${match}</span>`;
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

	console.log('PII: Adjusting entity positions for br tag removal', {
		originalLength: originalHtmlText.length,
		newLength: textWithoutBrTags.length,
		brTagsRemoved: (originalHtmlText.match(/<br\s*\/?>/gi) || []).length
	});

	return entities.map(entity => {
		const adjustedOccurrences = entity.occurrences.map(occurrence => {
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
			
			console.log('PII: Position adjustment for entity', entity.label, {
				original: { start: occurrence.start_idx, end: occurrence.end_idx },
				adjusted: { start: adjustedStart, end: adjustedEnd },
				brTagsRemoved: { beforeStart: brTagsBeforeStart, beforeEnd: brTagsBeforeEnd }
			});

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
// Handles both regular PII entities and modifier-created entities
export function unmaskAndHighlightTextForDisplay(text: string, entities: ExtendedPiiEntity[], modifiers?: any[]): string {
	if (!entities.length || !text) return text;

	// Check if text is already processed to prevent double processing
	if (text.includes('<span class="pii-highlight')) {
		console.log('PII: Text already highlighted for display, skipping');
		return text;
	}

	let processedText = text;
	let replacementsMade = 0;

	console.log('PII: Starting unmask and highlight for display. Original text:', text.substring(0, 200));
	console.log('PII: Available entities:', entities.map(e => ({ label: e.label, rawText: e.raw_text })));

	// Step 1: Unmask all patterns and simultaneously replace with highlighted spans
	entities.forEach((entity) => {
		const { label } = entity;
		const rawText = entity.raw_text;

		if (!label || !rawText) {
			console.log('PII: Skipping entity with missing label or rawText:', { label, rawText });
			return;
		}

		// Extract the base type and ID from the label (e.g., "PERSON_1" -> baseType="PERSON", labelId="1")
		const labelMatch = label.match(/^(.+)_(\d+)$/);
		if (!labelMatch) {
			console.log('PII: Skipping entity with invalid label format:', label);
			return;
		}

		const [, baseType, labelId] = labelMatch;
		const labelVariations = getLabelVariations(baseType);

		// Create more comprehensive patterns for the exact label as it appears in masked text
		const patterns = [
			`\\[\\{${labelVariations}_${labelId}\\}\\]`,  // [{TYPE_ID}]
			`\\[${labelVariations}_${labelId}\\]`,        // [TYPE_ID]
			`\\{${labelVariations}_${labelId}\\}`,        // {TYPE_ID}
			`${labelVariations}_${labelId}(?=\\s|$|[^\\w])` // TYPE_ID as word boundary
		];
		
		// Use case-insensitive matching and global flag
		const labelRegex = new RegExp(patterns.join('|'), 'gi');

		console.log('PII: Processing entity for display', label, 'patterns:', patterns);
		console.log('PII: Looking for patterns in text:', processedText.substring(0, 300));

		// Count matches before replacement
		const matches = processedText.match(labelRegex);
		if (matches) {
			console.log('PII: Found', matches.length, 'matches for entity', label, ':', matches);
		} else {
			console.log('PII: No pattern matches found for entity', label);
		}

		// Replace masked patterns with highlighted spans containing the original text
		const beforeLength = processedText.length;
		processedText = processedText.replace(labelRegex, (match) => {
			const shouldMask = entity.shouldMask ?? true;
			const maskingClass = shouldMask ? 'pii-masked' : 'pii-unmasked';
			const statusText = shouldMask ? 'Was masked in input' : 'Was NOT masked in input';

			console.log('PII: Replacing pattern', match, 'with highlighted span for', label, 'using raw text:', rawText);
			replacementsMade++;
			return `<span class="pii-highlight ${maskingClass}" title="${entity.label} (${entity.type}) - ${statusText}" data-pii-type="${entity.type}" data-pii-label="${entity.label}">${rawText}</span>`;
		});

		if (processedText.length !== beforeLength) {
			console.log('PII: Successfully replaced patterns for', label, 'text length changed from', beforeLength, 'to', processedText.length);
		}
	});

	console.log('PII: After pattern replacement, made', replacementsMade, 'replacements. Text:', processedText.substring(0, 300));

	// Step 2: If no masked patterns were found, highlight any remaining raw text instances
	// This handles cases where text was already unmasked but not highlighted
	if (replacementsMade === 0) {
		console.log('PII: No masked patterns found, checking for raw text to highlight');
		
		// Sort entities by text length (longest first) to avoid partial replacements
		const sortedEntities = [...entities].sort((a, b) => b.raw_text.length - a.raw_text.length);

		sortedEntities.forEach((entity) => {
			// Skip entities with empty or invalid raw_text
			if (!entity.raw_text || entity.raw_text.trim() === '') {
				return;
			}

			// Escape special regex characters and create pattern
			const escapedText = entity.raw_text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
			
			// Use word boundaries for better matching, but handle special characters gracefully
			const hasSpecialChars = /[^\w\s]/.test(entity.raw_text);
			const regex = hasSpecialChars 
				? new RegExp(escapedText, 'gi')
				: new RegExp(`\\b${escapedText}\\b`, 'gi');

			console.log('PII: Highlighting raw text for entity', entity.label, 'with text:', entity.raw_text, 'pattern:', regex.source);

			// Count matches before replacement
			const matches = processedText.match(regex);
			if (matches) {
				console.log('PII: Found', matches.length, 'raw text matches for entity', entity.label, ':', matches);
			}

			processedText = processedText.replace(regex, (match) => {
				const shouldMask = entity.shouldMask ?? true;
				const maskingClass = shouldMask ? 'pii-masked' : 'pii-unmasked';
				const statusText = shouldMask ? 'Was masked in input' : 'Was NOT masked in input';

				console.log('PII: Highlighting raw text match:', match, 'for entity', entity.label);
				replacementsMade++;
				return `<span class="pii-highlight ${maskingClass}" title="${entity.label} (${entity.type}) - ${statusText}" data-pii-type="${entity.type}" data-pii-label="${entity.label}">${match}</span>`;
			});
		});
	}

	console.log('PII: Final result after', replacementsMade, 'total replacements:', processedText.substring(0, 300));
	
	// Detect potential issues in the final result
	if (processedText.includes('</span>') && processedText.match(/[a-zA-Z]+\s*<\/span>\s*[a-zA-Z]+/)) {
		console.warn('PII: WARNING - Detected potential incomplete replacement in final text:', processedText.substring(0, 200));
	}

	return processedText;
}
