/**
 * Proposed: Unified State Management for PII System
 * Single source of truth with reactive updates and clear data flow
 */

import type { ExtendedPiiEntity, PiiModifier } from '$lib/utils/pii';
import type { PositionMapping } from './PiiPositionMapping';

// Centralized state interface
export interface PiiState {
	// Core data
	entities: ExtendedPiiEntity[];
	modifiers: PiiModifier[];

	// Context
	conversationId?: string;
	sessionId?: string;

	// Editor state
	positionMapping?: PositionMapping;
	isDetecting: boolean;
	lastDocumentHash?: string;

	// Performance
	cachedDecorations?: any; // DecorationSet
	lastDecorationHash?: string;

	// Metadata
	lastUpdated: number;
	version: number; // For optimistic updates
}

// State change events
export type PiiStateEvent =
	| { type: 'ENTITIES_UPDATED'; entities: ExtendedPiiEntity[] }
	| { type: 'MODIFIERS_UPDATED'; modifiers: PiiModifier[] }
	| { type: 'ENTITY_TOGGLED'; entityLabel: string; shouldMask: boolean }
	| { type: 'DETECTION_STARTED' }
	| { type: 'DETECTION_COMPLETED'; entities: ExtendedPiiEntity[] }
	| { type: 'CONVERSATION_SWITCHED'; conversationId: string }
	| { type: 'STATE_PERSISTED'; conversationId: string };

// State update result
export interface StateUpdateResult {
	success: boolean;
	newState: PiiState;
	events: PiiStateEvent[];
	error?: Error;
}

// Proposed: Event-driven state manager
export interface PiiStateManager {
	// State access (read-only)
	getCurrentState(conversationId?: string): Readonly<PiiState>;

	// State updates (returns events + new state)
	updateEntities(entities: ExtendedPiiEntity[], conversationId?: string): StateUpdateResult;
	updateModifiers(modifiers: PiiModifier[], conversationId?: string): StateUpdateResult;
	toggleEntityMasking(
		entityLabel: string,
		shouldMask: boolean,
		conversationId?: string
	): StateUpdateResult;

	// Conversation management
	switchConversation(conversationId: string): StateUpdateResult;
	loadConversationState(conversationId: string): Promise<StateUpdateResult>;
	persistConversationState(conversationId: string): Promise<StateUpdateResult>;

	// Event subscription
	subscribe(listener: (event: PiiStateEvent, state: Readonly<PiiState>) => void): () => void;

	// Performance
	invalidateCache(conversationId?: string): void;
	getPerformanceMetrics(): { cacheHits: number; stateSyncs: number; persistTime: number };
}

/**
 * Benefits of this approach:
 *
 * 1. **Single Source of Truth**: One state object per conversation
 * 2. **Event-Driven**: Clear communication via events
 * 3. **Immutable Updates**: No shared mutable state
 * 4. **Performance Tracking**: Built-in metrics
 * 5. **Type Safety**: Full TypeScript support
 * 6. **Testable**: Clear interfaces for mocking
 */

// Usage example in extensions:
export const usePiiState = (conversationId?: string) => {
	const stateManager = PiiStateManager.getInstance();

	// Read current state
	const currentState = stateManager.getCurrentState(conversationId);

	// Subscribe to changes
	const unsubscribe = stateManager.subscribe((event, newState) => {
		switch (event.type) {
			case 'ENTITIES_UPDATED':
				// Update plugin decorations
				updateDecorations(newState.entities);
				break;
			case 'MODIFIERS_UPDATED':
				// Update modifier highlights
				updateModifierDecorations(newState.modifiers);
				break;
			case 'CONVERSATION_SWITCHED':
				// Reload plugin state
				reloadPluginState(newState);
				break;
		}
	});

	return {
		state: currentState,
		updateEntities: (entities: ExtendedPiiEntity[]) =>
			stateManager.updateEntities(entities, conversationId),
		updateModifiers: (modifiers: PiiModifier[]) =>
			stateManager.updateModifiers(modifiers, conversationId),
		toggleEntity: (label: string, shouldMask: boolean) =>
			stateManager.toggleEntityMasking(label, shouldMask, conversationId),
		unsubscribe
	};
};
