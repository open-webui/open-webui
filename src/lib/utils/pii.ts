import type { PiiEntity } from '$lib/apis/pii';
import i18next from 'i18next';
import {
	PiiApiClient,
	createPiiApiClient,
	type PiiApiClientConfig,
	type ApiRequestOptions,
	PiiApiError,
	PiiApiTimeoutError,
	PiiApiNetworkError
} from '$lib/apis/pii/client';
import { PiiPerformanceTracker } from '$lib/components/common/RichTextInput/PiiPerformanceOptimizer';

// Extended PII entity with masking state
export interface ExtendedPiiEntity extends PiiEntity {
	shouldMask?: boolean;
	// Store original plain text positions for API calls
	// While 'occurrences' contains mapped ProseMirror positions for editor interactions
	originalOccurrences?: Array<{ start_idx: number; end_idx: number }>;
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

// File mapping for filename masking
export interface FilenameMapping {
	fileId: string;
	originalFilename: string;
	maskedFilename: string; // This will be the file ID for simplicity
}

// Conversation-specific PII state for storing with chat data
export interface ConversationPiiState {
	entities: ExtendedPiiEntity[];
	modifiers: PiiModifier[];
	filenameMappings: FilenameMapping[];
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
	private apiClient: PiiApiClient | null = null;

	// Error recovery backup for failed saves
	private errorBackup: Map<string, ConversationPiiState> = new Map();
	private pendingSaves: Set<string> = new Set();
	// Track conversations currently being loaded
	private loadingConversations = new Set<string>();

	private temporaryState: {
		entities: ExtendedPiiEntity[];
		modifiers: PiiModifier[];
		filenameMappings: FilenameMapping[];
		isActive: boolean;
		lastUpdated: number;
	} = {
		entities: [],
		modifiers: [],
		filenameMappings: [],
		isActive: false,
		lastUpdated: 0
	};

	private workingEntitiesForConversations: Map<string, ExtendedPiiEntity[]> = new Map();

	// Store current PII masking state
	private currentPiiMaskingEnabled: boolean = true;

	static getInstance(): PiiSessionManager {
		if (!PiiSessionManager.instance) {
			PiiSessionManager.instance = new PiiSessionManager();
		}
		return PiiSessionManager.instance;
	}

	/**
	 * Reset the singleton instance (for testing only)
	 */
	static resetInstance(): void {
		PiiSessionManager.instance = undefined as any;
	}

	setApiKey(apiKey: string) {
		this.apiKey = apiKey;

		// Initialize or update API client when API key changes
		if (apiKey) {
			this.initializeApiClient({
				apiKey,
				quiet: true // Default to quiet mode for session manager operations
			});
		}
	}

	/**
	 * Initialize the PII API client with configuration
	 */
	initializeApiClient(config: PiiApiClientConfig) {
		this.apiClient = createPiiApiClient(config);
		this.apiKey = config.apiKey;
	}

	/**
	 * Get the current API client instance
	 */
	getApiClient(): PiiApiClient | null {
		return this.apiClient;
	}

	/**
	 * Ensure API client is available and configured
	 */
	private ensureApiClient(): PiiApiClient {
		if (!this.apiClient || !this.apiKey) {
			throw new Error('PII API client not initialized. Call setApiKey() first.');
		}
		return this.apiClient;
	}

	activateTemporaryState() {
		this.temporaryState.isActive = true;
		this.temporaryState.entities = [];
		this.temporaryState.modifiers = [];
		this.temporaryState.filenameMappings = [];
	}

	isTemporaryStateActive(): boolean {
		return this.temporaryState.isActive;
	}

	/**
	 * Shared helper method to merge entities by text content with proper ID assignment
	 * @param existingEntities - Current entities to merge with
	 * @param incomingEntities - New entities to merge in
	 * @returns Merged entities with proper ID assignment and occurrence merging
	 */
	private mergeEntitiesByText(
		existingEntities: ExtendedPiiEntity[],
		incomingEntities: (ExtendedPiiEntity | PiiEntity)[]
	): ExtendedPiiEntity[] {
		const merged: ExtendedPiiEntity[] = [...existingEntities];
		const occurrenceKey = (o: { start_idx: number; end_idx: number }) =>
			`${o.start_idx}-${o.end_idx}`;

		// Helper function to check if ID is already used
		const isIdUsed = (id: number): boolean => {
			return merged.some((e) => e.id === id);
		};

		// Helper function to get next available ID for a given type
		const getNextIdForType = (type: string): number => {
			const existingOfType = merged.filter((e) => e.type === type);
			if (existingOfType.length === 0) return 1;

			const maxId = Math.max(...existingOfType.map((e) => e.id));
			return maxId + 1;
		};

		// Helper function to generate label from type and id
		const generateLabel = (type: string, id: number): string => {
			return `${type}_${id}`;
		};

		for (const incoming of incomingEntities) {
			// Cast to ExtendedPiiEntity for consistent access
			const incomingEntity = incoming as ExtendedPiiEntity;

			// Find existing entity by text content (not label)
			const idx = merged.findIndex((e) => e.text === incomingEntity.text);

			if (idx >= 0) {
				// Entity with same text already exists - merge occurrences
				const current = merged[idx];
				const currentOccKeys = new Set((current.occurrences || []).map(occurrenceKey));
				const newOcc = (incomingEntity.occurrences || []).filter(
					(o) => !currentOccKeys.has(occurrenceKey(o))
				);

				// Also merge originalOccurrences if they exist
				const currentOriginalOccKeys = new Set(
					(current.originalOccurrences || []).map(occurrenceKey)
				);
				const newOriginalOcc = (incomingEntity.originalOccurrences || []).filter(
					(o) => !currentOriginalOccKeys.has(occurrenceKey(o))
				);

				merged[idx] = {
					...current,
					// Keep existing shouldMask and other properties, just add new occurrences
					occurrences: [...(current.occurrences || []), ...newOcc],
					originalOccurrences: [...(current.originalOccurrences || []), ...newOriginalOcc]
				};
			} else {
				// New entity - preserve original ID/label if not in use, otherwise assign new ones
				let finalId = incomingEntity.id;
				let finalLabel = incomingEntity.label;

				if (isIdUsed(incomingEntity.id)) {
					// ID is already used, assign next available ID and generate label
					finalId = getNextIdForType(incomingEntity.type);
					finalLabel = generateLabel(incomingEntity.type, finalId);
				}

				merged.push({
					...incomingEntity,
					id: finalId,
					label: finalLabel,
					shouldMask: incomingEntity.shouldMask ?? true
				});
			}
		}

		return merged;
	}

	setTemporaryStateEntities(entities: ExtendedPiiEntity[]) {
		if (!this.temporaryState.isActive) {
			console.warn('PiiSessionManager: Attempted to set temporary state when not active');
			return;
		}

		// Merge new entities into temporary state using shared helper
		const existing = this.temporaryState.entities || [];
		this.temporaryState.entities = this.mergeEntitiesByText(existing, entities);
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
			filenameMappings: [...this.temporaryState.filenameMappings],
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

	// Simple methods to store and retrieve PII masking state
	setCurrentPiiMaskingEnabled(enabled: boolean) {
		this.currentPiiMaskingEnabled = enabled;
	}

	getCurrentPiiMaskingEnabled(): boolean {
		return this.currentPiiMaskingEnabled;
	}

	clearTemporaryState() {
		this.temporaryState.isActive = false;
		this.temporaryState.entities = [];
		this.temporaryState.modifiers = [];
		this.temporaryState.filenameMappings = [];
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
		// Track performance
		const tracker = PiiPerformanceTracker.getInstance();
		const startTime = performance.now();

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
				// Ensure backward compatibility for existing states without filenameMappings
				const normalizedState: ConversationPiiState = {
					...piiState,
					filenameMappings: piiState.filenameMappings || []
				};
				this.conversationStates.set(conversationId, normalizedState);
			}
		} finally {
			// Track loading completion
			const elapsed = performance.now() - startTime;
			if (elapsed > 50) {
				console.log(`PiiSessionManager: Slow conversation load: ${elapsed.toFixed(1)}ms`);
			}
			this.loadingConversations.delete(conversationId);
		}
	}

	// Removed getActiveModifiers() - use getModifiersForDisplay() instead

	// Get state for saving to localStorage (chat data)
	getConversationState(conversationId: string): ConversationPiiState | null {
		return this.conversationStates.get(conversationId) || null;
	}

	getTemporaryState(): ConversationPiiState | null {
		return this.temporaryState;
	}

	// Convert conversation entities to known entities format for API
	getKnownEntitiesForApi(
		conversationId?: string
	): Array<{ id: number; label: string; name: string; shouldMask?: boolean }> {
		const entities = this.getEntitiesForDisplay(conversationId);
		return entities.map((entity) => ({
			id: entity.id,
			label: entity.label,
			name: entity.text || entity.raw_text.toLowerCase(),
			shouldMask: entity.shouldMask
		}));
	}

	// Get full entities with original positions for updatePiiMasking API calls
	getEntitiesForApiWithOriginalPositions(conversationId?: string): PiiEntity[] {
		const entities = this.getEntitiesForDisplay(conversationId);
		return entities.map((entity) => ({
			id: entity.id,
			type: entity.type,
			label: entity.label,
			text: entity.text,
			raw_text: entity.raw_text,
			// CRITICAL: Use originalOccurrences (plain text positions) for API
			occurrences: entity.originalOccurrences
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
		const existingModifiers = existingState?.modifiers || [];
		const mergedModifiers = this.mergeModifiers(existingModifiers, modifiers);

		const newState: ConversationPiiState = {
			entities: existingState?.entities || [],
			modifiers: mergedModifiers,
			filenameMappings: existingState?.filenameMappings || [],
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
		// Merge new modifiers with existing ones instead of overwriting
		const existingModifiers = this.temporaryState.modifiers || [];
		const mergedModifiers = this.mergeModifiers(existingModifiers, modifiers);
		this.temporaryState.modifiers = mergedModifiers;
	}

	// Helper method to merge modifiers by entity text, avoiding duplicates
	private mergeModifiers(existing: PiiModifier[], newModifiers: PiiModifier[]): PiiModifier[] {
		const merged = [...existing];

		newModifiers.forEach((newModifier) => {
			// Check if a modifier for this entity already exists
			const existingIndex = merged.findIndex(
				(m) =>
					m.entity.toLowerCase() === newModifier.entity.toLowerCase() &&
					m.action === newModifier.action
			);

			if (existingIndex >= 0) {
				// Update existing modifier
				merged[existingIndex] = { ...newModifier };
			} else {
				// Add new modifier
				merged.push({ ...newModifier });
			}
		});

		return merged;
	}

	// Remove a specific modifier by ID from conversation state
	removeConversationModifier(conversationId: string, modifierId: string) {
		const existingState = this.conversationStates.get(conversationId);
		if (!existingState) return;

		const remainingModifiers = existingState.modifiers.filter((m) => m.id !== modifierId);

		const newState: ConversationPiiState = {
			...existingState,
			modifiers: remainingModifiers,
			lastUpdated: Date.now()
		};

		this.conversationStates.set(conversationId, newState);

		// Create backup and trigger save
		this.errorBackup.set(conversationId, { ...newState });
		this.triggerChatSave(conversationId);
	}

	// Remove a specific modifier by ID from temporary state
	removeTemporaryModifier(modifierId: string) {
		if (!this.temporaryState.isActive) return;

		this.temporaryState.modifiers = this.temporaryState.modifiers.filter(
			(m) => m.id !== modifierId
		);
	}

	// FILENAME MAPPING MANAGEMENT METHODS

	// Add a filename mapping for PII masking
	addFilenameMapping(conversationId: string | undefined, fileId: string, originalFilename: string) {
		const mapping: FilenameMapping = {
			fileId,
			originalFilename,
			maskedFilename: fileId // Use file ID as the masked filename
		};

		if (conversationId && this.conversationStates.has(conversationId)) {
			// Existing conversation - add to conversation state
			const state = this.conversationStates.get(conversationId)!;
			const existingMappings = state.filenameMappings || [];

			// Check if mapping already exists
			if (!existingMappings.find((m) => m.fileId === fileId)) {
				const newState: ConversationPiiState = {
					...state,
					filenameMappings: [...existingMappings, mapping],
					lastUpdated: Date.now()
				};
				this.conversationStates.set(conversationId, newState);
				this.triggerChatSave(conversationId);
			}
		} else {
			// New chat or no conversation - add to temporary state
			if (!this.temporaryState.isActive) {
				this.activateTemporaryState();
			}

			// Check if mapping already exists
			if (!this.temporaryState.filenameMappings.find((m) => m.fileId === fileId)) {
				this.temporaryState.filenameMappings.push(mapping);
			}
		}
	}

	// Get filename mappings for display
	getFilenameMappingsForDisplay(conversationId?: string): FilenameMapping[] {
		if (
			!conversationId ||
			conversationId.trim() === '' ||
			!this.conversationStates.has(conversationId)
		) {
			if (this.temporaryState.isActive) {
				return this.temporaryState.filenameMappings;
			}
			return [];
		}

		const state = this.conversationStates.get(conversationId);
		return state?.filenameMappings || [];
	}

	// Get temporary filename mappings (for new chats without conversation ID)
	getTemporaryFilenameMappings(): FilenameMapping[] {
		return this.temporaryState.filenameMappings;
	}

	// Get filename mappings for masking files before sending to model
	maskFilenames(files: any[], conversationId?: string): any[] {
		const mappings = this.getFilenameMappingsForDisplay(conversationId);
		if (!mappings.length) return files;

		return files.map((file) => {
			const mapping = mappings.find((m) => m.fileId === file.id);
			if (mapping) {
				return {
					...file,
					name: mapping.maskedFilename,
					originalName: mapping.originalFilename // Keep original for reference
				};
			}
			return file;
		});
	}

	// Remove a filename mapping
	removeFilenameMapping(conversationId: string | undefined, fileId: string) {
		if (conversationId && this.conversationStates.has(conversationId)) {
			const state = this.conversationStates.get(conversationId)!;
			const filteredMappings = (state.filenameMappings || []).filter((m) => m.fileId !== fileId);

			const newState: ConversationPiiState = {
				...state,
				filenameMappings: filteredMappings,
				lastUpdated: Date.now()
			};
			this.conversationStates.set(conversationId, newState);
			this.triggerChatSave(conversationId);
		} else if (this.temporaryState.isActive) {
			this.temporaryState.filenameMappings = this.temporaryState.filenameMappings.filter(
				(m) => m.fileId !== fileId
			);
		}
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
				if (entity) {
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
				if (workingEntity) {
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
			if (entity) {
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

		// Merge entities using shared helper
		const merged = this.mergeEntitiesByText(existingEntities, entities);

		const newState: ConversationPiiState = {
			entities: merged,
			modifiers: existingState?.modifiers || [],
			filenameMappings: existingState?.filenameMappings || [],
			sessionId: sessionId || existingState?.sessionId,
			apiKey: this.apiKey || existingState?.apiKey,
			lastUpdated: Date.now()
		};

		this.conversationStates.set(conversationId, newState);
		this.errorBackup.set(conversationId, { ...newState });
		this.triggerChatSave(conversationId);
	}

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
		const existingState = this.conversationStates.get(conversationId);
		const persistentEntities = existingState?.entities || [];

		// Merge occurrences for labels that already exist in persistent state
		let persistentChanged = false;
		const mergedPersistent: ExtendedPiiEntity[] = [...persistentEntities];

		const occurrenceKey = (o: { start_idx: number; end_idx: number }) =>
			`${o.start_idx}-${o.end_idx}`;

		for (const incoming of extendedEntities) {
			const idx = mergedPersistent.findIndex((e) => e.label === incoming.label);
			if (idx >= 0) {
				const current = mergedPersistent[idx];
				const currentOccKeys = new Set((current.occurrences || []).map(occurrenceKey));
				const newOcc = (incoming.occurrences || []).filter(
					(o) => !currentOccKeys.has(occurrenceKey(o))
				);

				// Also handle originalOccurrences
				const currentOriginalOccKeys = new Set(
					(current.originalOccurrences || []).map(occurrenceKey)
				);
				const newOriginalOcc = (incoming.originalOccurrences || []).filter(
					(o) => !currentOriginalOccKeys.has(occurrenceKey(o))
				);

				if (
					newOcc.length > 0 ||
					newOriginalOcc.length > 0 ||
					(incoming.shouldMask !== undefined && current.shouldMask === undefined)
				) {
					mergedPersistent[idx] = {
						...current,
						// Prefer existing shouldMask; otherwise adopt incoming
						shouldMask: current.shouldMask ?? incoming.shouldMask,
						// Prefer non-empty raw_text/type
						text: current.text || incoming.text,
						raw_text: current.raw_text || incoming.raw_text,
						type: current.type || incoming.type,
						occurrences: [...(current.occurrences || []), ...newOcc],
						originalOccurrences: [...(current.originalOccurrences || []), ...newOriginalOcc]
					};
					persistentChanged = true;
				}
			}
		}

		if (persistentChanged && existingState) {
			const newState: ConversationPiiState = {
				...existingState,
				entities: mergedPersistent,
				lastUpdated: Date.now()
			};
			this.conversationStates.set(conversationId, newState);
			this.errorBackup.set(conversationId, { ...newState });
			this.triggerChatSave(conversationId);
		}

		// Only store genuinely new labels in working state
		const newLabels = extendedEntities.filter(
			(entity) => !mergedPersistent.find((persistent) => persistent.label === entity.label)
		);
		this.workingEntitiesForConversations.set(conversationId, newLabels);
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

	// ==================================================
	// API CLIENT WRAPPER METHODS
	// ==================================================

	/**
	 * Create a PII detection session
	 */
	async createSession(ttl: string = '24h', options?: ApiRequestOptions) {
		const client = this.ensureApiClient();
		const session = await client.createSession(ttl, options);
		this.sessionId = session.session_id;
		return session;
	}

	/**
	 * Get current session information
	 */
	async getSessionInfo(options?: ApiRequestOptions) {
		const client = this.ensureApiClient();
		if (!this.sessionId) {
			throw new Error('No active session. Call createSession() first.');
		}
		return client.getSession(this.sessionId, options);
	}

	/**
	 * Delete the current session
	 */
	async deleteSession(options?: ApiRequestOptions) {
		const client = this.ensureApiClient();
		if (!this.sessionId) {
			throw new Error('No active session to delete.');
		}
		await client.deleteSession(this.sessionId, options);
		this.sessionId = null;
	}

	/**
	 * Mask PII in text (ephemeral - without session)
	 */
	async maskText(
		text: string[],
		conversationId?: string,
		createSession: boolean = false,
		options?: ApiRequestOptions
	) {
		const client = this.ensureApiClient();
		const knownEntities = this.getKnownEntitiesForApi(conversationId);
		const modifiers = this.getModifiersForApi(conversationId);

		return client.maskText(text, knownEntities, modifiers, createSession, options);
	}

	/**
	 * Unmask PII in text (ephemeral - without session)
	 */
	async unmaskText(text: string[], entities: PiiEntity[], options?: ApiRequestOptions) {
		const client = this.ensureApiClient();
		return client.unmaskText(text, entities, options);
	}

	/**
	 * Mask PII in text using current session
	 */
	async maskTextWithSession(text: string[], conversationId?: string, options?: ApiRequestOptions) {
		const client = this.ensureApiClient();
		if (!this.sessionId) {
			throw new Error('No active session. Call createSession() first.');
		}

		const knownEntities = this.getKnownEntitiesForApi(conversationId);
		const modifiers = this.getModifiersForApi(conversationId);

		return client.maskTextWithSession(this.sessionId, text, knownEntities, modifiers, options);
	}

	/**
	 * Unmask PII in text using current session
	 */
	async unmaskTextWithSession(text: string[], options?: ApiRequestOptions) {
		const client = this.ensureApiClient();
		if (!this.sessionId) {
			throw new Error('No active session. Call createSession() first.');
		}

		return client.unmaskTextWithSession(this.sessionId, text, options);
	}

	/**
	 * Cancel all pending API requests
	 */
	cancelAllRequests() {
		if (this.apiClient) {
			this.apiClient.cancelAllRequests();
		}
	}

	/**
	 * Get API client statistics
	 */
	getApiStats() {
		if (this.apiClient) {
			return this.apiClient.getStats();
		}
		return null;
	}

	/**
	 * Create a PII payload for API calls from current conversation entities
	 * This transforms entities into a map format where the entity text is the key
	 * and the value contains all entity details needed for API processing
	 *
	 * @param conversationId - The conversation ID to get entities for (optional)
	 * @returns Record<string, any> | null - PII payload map or null if no entities
	 */
	createPiiPayloadForApi(conversationId?: string): Record<string, any> | null {
		// Get current working entities (includes user modifications and persistent state)
		const currentEntities = this.getEntitiesForApiWithOriginalPositions(conversationId);

		// Use the static utility function to create payload
		return createPiiPayloadFromEntities(currentEntities);
	}

	/**
	 * Update API client configuration
	 */
	updateApiConfig(config: Partial<PiiApiClientConfig>) {
		if (this.apiClient) {
			this.apiClient.updateConfig(config);
		}
	}

	// DEBUG METHODS - For PII debug interface
	/**
	 * Get debug information about sync state for a conversation
	 */
	getDebugSyncState(conversationId?: string) {
		const conversationState = conversationId ? this.conversationStates.get(conversationId) : null;

		return {
			lastUpdated: conversationState?.lastUpdated || null,
			sessionId: conversationState?.sessionId || this.sessionId || null,
			apiKey: !!(conversationState?.apiKey || this.apiKey),
			isLoading: conversationId ? this.loadingConversations.has(conversationId) : false,
			hasPendingSave: conversationId ? this.pendingSaves.has(conversationId) : false
		};
	}

	/**
	 * Get debug information about data sources
	 */
	getDebugSources(conversationId?: string) {
		const conversationState = conversationId ? this.conversationStates.get(conversationId) : null;
		const workingEntities = conversationId
			? this.workingEntitiesForConversations.get(conversationId)
			: null;

		return {
			temporary: {
				entities: this.temporaryState.entities?.length || 0,
				modifiers: this.temporaryState.modifiers?.length || 0,
				active: this.temporaryState.isActive || false
			},
			conversation: {
				entities: conversationState?.entities?.length || 0,
				modifiers: conversationState?.modifiers?.length || 0,
				exists: !!conversationState
			},
			working: {
				entities: workingEntities?.length || 0
			},
			files: {
				mappings: this.temporaryState.filenameMappings?.length || 0
			}
		};
	}

	/**
	 * Get debug information about internal state
	 */
	getDebugStats() {
		return {
			totalConversations: this.conversationStates.size,
			loadingConversations: this.loadingConversations.size,
			pendingSaves: this.pendingSaves.size,
			errorBackups: this.errorBackup.size,
			hasApiClient: !!this.apiClient,
			temporaryStateActive: this.temporaryState.isActive
		};
	}
}

/**
 * Create a PII payload for API calls from a provided array of entities
 * This is a static utility function that can be used when you have entities directly
 * rather than needing to fetch them from the session manager
 *
 * @param entities - Array of PII entities to transform into payload format
 * @returns Record<string, any> | null - PII payload map or null if no entities
 */
export function createPiiPayloadFromEntities(
	entities: (PiiEntity | ExtendedPiiEntity)[]
): Record<string, any> | null {
	// Return null if no entities to process
	if (!entities || entities.length === 0) {
		return null;
	}

	// Create a map where entity text is the key for efficient API processing
	// TypeScript note: Record<string, any> means an object with string keys and any value type
	const map: Record<string, any> = {};

	entities.forEach((entity) => {
		// Use entity text as primary key, fallback to label for compatibility
		const key = entity.text || entity.label;
		if (!key) return; // Skip entities without text or label

		// Handle originalOccurrences vs regular occurrences
		// ExtendedPiiEntity may have originalOccurrences (plain text positions)
		const extendedEntity = entity as ExtendedPiiEntity;
		const occurrences =
			extendedEntity.originalOccurrences && extendedEntity.originalOccurrences.length > 0
				? extendedEntity.originalOccurrences
				: (entity.occurrences || []).map((o) => ({
						start_idx: o.start_idx,
						end_idx: o.end_idx
					}));

		// Create structured object with all entity details
		map[key] = {
			id: entity.id,
			label: entity.label,
			type: entity.type || 'PII',
			text: (entity.text || entity.label).toLowerCase(), // Lowercase for consistent matching
			raw_text: entity.raw_text || entity.label,
			occurrences
		};
	});

	return map;
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

// Function to unmask filenames in response text
export function unmaskFilenamesInText(text: string, mappings: FilenameMapping[]): string {
	if (!mappings.length || !text) return text;

	let result = text;

	// Replace file IDs with original filenames
	mappings.forEach((mapping) => {
		// Create a regex to match the file ID when mentioned in text
		// Look for patterns like the file ID mentioned as a word or in quotes
		const escapedFileId = mapping.fileId.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
		const fileIdRegex = new RegExp(`\\b${escapedFileId}\\b`, 'gi');

		result = result.replace(fileIdRegex, (match) => {
			// Replace file ID with highlighted filename
			return `<span class="filename-highlight" title="File: ${mapping.originalFilename}" data-file-id="${mapping.fileId}">${mapping.originalFilename}</span>`;
		});
	});

	return result;
}

// Enhanced function to unmask and highlight text with modifier awareness for display
export function unmaskAndHighlightTextForDisplay(
	text: string,
	entities: ExtendedPiiEntity[],
	filenameMappings?: FilenameMapping[]
): string {
	if (!entities.length && !filenameMappings?.length) return text;
	if (!text) return text;

	// Check if text is already processed to prevent double processing
	if (
		text.includes('<span class="pii-highlight') &&
		text.includes('<span class="filename-highlight')
	) {
		return text;
	}

	let processedText = text;

	// First, handle filename unmasking if mappings are provided
	if (filenameMappings?.length) {
		processedText = unmaskFilenamesInText(processedText, filenameMappings);
	}

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
