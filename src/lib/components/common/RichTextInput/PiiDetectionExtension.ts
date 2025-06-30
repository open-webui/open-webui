import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
import type { Node as ProseMirrorNode } from 'prosemirror-model';
import type { ExtendedPiiEntity } from '$lib/utils/pii';
import type { PiiEntity } from '$lib/apis/pii';
import { maskPiiText } from '$lib/apis/pii';
import { debounce, PiiSessionManager } from '$lib/utils/pii';
import type { PiiModifier } from './PiiModifierExtension';

interface PositionMapping {
	plainTextToProseMirror: Map<number, number>;
	proseMirrorToPlainText: Map<number, number>;
	plainText: string;
}

interface PiiDetectionState {
	entities: ExtendedPiiEntity[];
	positionMapping: PositionMapping | null;
	isDetecting: boolean;
	lastText: string;
	needsSync: boolean;
}

export interface PiiDetectionOptions {
	enabled: boolean;
	apiKey: string;
	conversationId?: string | undefined;
	onPiiDetected?: (entities: ExtendedPiiEntity[], maskedText: string) => void;
	onPiiToggled?: (entities: ExtendedPiiEntity[]) => void;
	debounceMs?: number;
}

// Build position mapping between plain text and ProseMirror positions
function buildPositionMapping(doc: ProseMirrorNode): PositionMapping {
	const plainTextToProseMirror = new Map<number, number>();
	const proseMirrorToPlainText = new Map<number, number>();
	let plainTextOffset = 0;
	let plainText = '';

	doc.nodesBetween(0, doc.content.size, (node, pos) => {
		if (node.isText && node.text) {
			// Map each character in the text node
			for (let i = 0; i < node.text.length; i++) {
				const proseMirrorPos = pos + i;
				const plainTextPos = plainTextOffset + i;
				
				plainTextToProseMirror.set(plainTextPos, proseMirrorPos);
				proseMirrorToPlainText.set(proseMirrorPos, plainTextPos);
			}
			
			plainText += node.text;
			plainTextOffset += node.text.length;
		} else if (node.type.name === 'paragraph' && plainTextOffset > 0) {
			// Add line breaks between paragraphs (but not at the very beginning)
			plainText += '\n';
			plainTextOffset += 1;
		} else if (node.type.name === 'hard_break') {
			// Add line breaks for hard breaks
			plainText += '\n';
			plainTextOffset += 1;
		}
		
		return true; // Continue traversing
	});

	return {
		plainTextToProseMirror,
		proseMirrorToPlainText,
		plainText: plainText.trim()
	};
}

// Convert PII entity positions from plain text to ProseMirror positions
// Preserves existing shouldMask state from current entities
function mapPiiEntitiesToProseMirror(
	entities: PiiEntity[],
	mapping: PositionMapping,
	existingEntities: ExtendedPiiEntity[] = []
): ExtendedPiiEntity[] {
	return entities.map(entity => {
		// Find existing entity with same label to preserve shouldMask state
		const existingEntity = existingEntities.find(existing => existing.label === entity.label);
		const shouldMask = existingEntity?.shouldMask ?? true; // Default to true if not found
		
		return {
			...entity,
			shouldMask,
			occurrences: entity.occurrences.map((occurrence: any) => {
				const plainTextStart = occurrence.start_idx;
				const plainTextEnd = occurrence.end_idx;
				
				const proseMirrorStart = mapping.plainTextToProseMirror.get(plainTextStart) ?? plainTextStart + 1;
				const proseMirrorEnd = mapping.plainTextToProseMirror.get(plainTextEnd - 1) ?? (plainTextEnd - 1 + 1);
				
				return {
					...occurrence,
					start_idx: proseMirrorStart,
					end_idx: proseMirrorEnd + 1
				};
			})
		};
	});
}

// Validate entity positions and remove invalid ones
function validateAndFilterEntities(entities: ExtendedPiiEntity[], doc: ProseMirrorNode, mapping: PositionMapping): ExtendedPiiEntity[] {
	return entities.filter(entity => {
		// Check if entity still exists in the current text
		const entityText = entity.raw_text.toLowerCase();
		const currentText = mapping.plainText.toLowerCase();
		
		if (!currentText.includes(entityText)) {
			console.log(`PiiDetectionExtension: Entity "${entity.label}" no longer exists in text, removing`);
			return false;
		}
		
		// Validate all occurrences have valid positions
		const validOccurrences = entity.occurrences.filter((occurrence: any) => {
			const { start_idx: from, end_idx: to } = occurrence;
			return from >= 0 && to <= doc.content.size && from < to;
		});
		
		if (validOccurrences.length === 0) {
			console.log(`PiiDetectionExtension: Entity "${entity.label}" has no valid positions, removing`);
			return false;
		}
		
		// Update entity with only valid occurrences
		entity.occurrences = validOccurrences;
		return true;
	});
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
	
	const remappedEntities = entities.map(entity => {
		const entityText = entity.raw_text;
		const searchText = entityText.toLowerCase();
		const plainText = mapping.plainText.toLowerCase();
		
		// Find all occurrences of this entity in the current text
		const newOccurrences = [];
		let searchIndex = 0;
		
		// Use word boundary matching for better accuracy
		const entityWords = entityText.split(/\s+/);
		const isMultiWord = entityWords.length > 1;
		
		while (searchIndex < plainText.length) {
			const foundIndex = plainText.indexOf(searchText, searchIndex);
			if (foundIndex === -1) break;
			
			// Check word boundaries for single words to avoid partial matches
			if (!isMultiWord) {
				const beforeChar = foundIndex > 0 ? plainText[foundIndex - 1] : ' ';
				const afterChar = foundIndex + searchText.length < plainText.length 
					? plainText[foundIndex + searchText.length] : ' ';
				
				// Skip if not at word boundary (unless it's punctuation)
				if (/\w/.test(beforeChar) || /\w/.test(afterChar)) {
					searchIndex = foundIndex + 1;
					continue;
				}
			}
			
			const plainTextStart = foundIndex;
			const plainTextEnd = foundIndex + entityText.length;
			
			// Convert to ProseMirror positions
			const proseMirrorStart = mapping.plainTextToProseMirror.get(plainTextStart);
			const proseMirrorEnd = mapping.plainTextToProseMirror.get(plainTextEnd - 1);
			
			if (proseMirrorStart !== undefined && proseMirrorEnd !== undefined) {
				const from = proseMirrorStart;
				const to = proseMirrorEnd + 1;
				
				// Validate the range
				if (from >= 0 && to <= doc.content.size && from < to) {
					newOccurrences.push({
						start_idx: from,
						end_idx: to
					});
				}
			}
			
			searchIndex = foundIndex + 1;
		}
		
		// Return entity with new occurrences, or mark for removal if none found
		return {
			...entity,
			occurrences: newOccurrences
		};
	});
	
	return remappedEntities.filter(entity => entity.occurrences.length > 0);
}

// Sync plugin state with session manager
function syncWithSessionManager(
	conversationId: string | undefined,
	piiSessionManager: typeof PiiSessionManager.prototype,
	currentEntities: ExtendedPiiEntity[],
	mapping: PositionMapping,
	doc: ProseMirrorNode
): ExtendedPiiEntity[] {
	// CRITICAL FIX: Get entities from both persistent and working state
	// This prevents newly detected entities from being filtered out during periodic syncs
	const persistentEntities = piiSessionManager.getEntitiesForDisplay(conversationId); // No global entities for non-conversation contexts
	
	const workingEntities = conversationId
		? piiSessionManager.getConversationEntitiesForDisplay(conversationId)
		: piiSessionManager.getEntitiesForDisplay();
		
	// CRITICAL FIX: For new chats, also include temporary state entities
	const temporaryEntities = !conversationId ? piiSessionManager.getTemporaryStateEntities() : [];
	
	// Merge persistent + working + temporary entities (working/temporary takes precedence for same labels)
	const allSessionEntities = [...persistentEntities];
	[...workingEntities, ...temporaryEntities].forEach((entity: ExtendedPiiEntity) => {
		if (!persistentEntities.find((p: ExtendedPiiEntity) => p.label === entity.label)) {
			allSessionEntities.push(entity);
		}
	});
	
	console.log('PiiDetectionExtension: Sync check:', {
		currentEntities: currentEntities.length,
		persistentEntities: persistentEntities.length,
		workingEntities: workingEntities.length,
		temporaryEntities: temporaryEntities.length,
		allSessionEntities: allSessionEntities.length
	});
	
	// If session manager has fewer entities, some were removed
	if (allSessionEntities.length < currentEntities.length) {
		// CRITICAL FIX: Don't filter entities if session manager is completely empty
		// This happens in new chat windows where session manager hasn't stored entities yet
		if (allSessionEntities.length === 0) {
			// For new chats, just validate current entities without filtering
			return validateAndFilterEntities(currentEntities, doc, mapping);
		}
		
		// Filter current entities to only include those still in session manager (persistent OR working)
		const filteredEntities = currentEntities.filter(currentEntity => 
			allSessionEntities.find((sessionEntity: ExtendedPiiEntity) => sessionEntity.label === currentEntity.label)
		);
		
		console.log('PiiDetectionExtension: Filtered entities:', {
			before: currentEntities.length,
			after: filteredEntities.length,
			removed: currentEntities.filter(c => !filteredEntities.find(f => f.label === c.label)).map(e => e.label)
		});
		
		// Validate positions for remaining entities
		return validateAndFilterEntities(filteredEntities, doc, mapping);
	}
	
	// CRITICAL FIX: Always prioritize plugin state shouldMask over session manager state
	// This ensures user interactions in the editor take precedence
	const updatedEntities = currentEntities.map(currentEntity => {
		const sessionEntity = allSessionEntities.find((e: ExtendedPiiEntity) => e.label === currentEntity.label);
		if (sessionEntity) {
			// CRITICAL FIX: Update session manager to match plugin state, not the other way around
			// This preserves user's toggle actions made in the editor
			if (sessionEntity.shouldMask !== currentEntity.shouldMask) {
				console.log(`PiiDetectionExtension: Syncing shouldMask state for ${currentEntity.label}: ${sessionEntity.shouldMask} → ${currentEntity.shouldMask}`);
				
				// Update session manager to match plugin state
				if (conversationId) {
					piiSessionManager.setEntityMaskingState(conversationId, currentEntity.label, currentEntity.shouldMask ?? true);
				} else {
					piiSessionManager.setGlobalEntityMaskingState(currentEntity.label, currentEntity.shouldMask ?? true);
				}
			}
			// Return current entity (plugin state takes precedence)
			return currentEntity;
		}
		return currentEntity;
	});
	
	return validateAndFilterEntities(updatedEntities, doc, mapping);
}

// Create decorations for PII entities and modifier-affected text
function createPiiDecorations(entities: ExtendedPiiEntity[], modifiers: PiiModifier[], doc: ProseMirrorNode): Decoration[] {
	const decorations: Decoration[] = [];
	const modifiersByEntity = new Map<string, PiiModifier>();
	
	modifiers.forEach(modifier => {
		modifiersByEntity.set(modifier.entity.toLowerCase(), modifier);
	});

	// Add PII entity decorations (lower priority)
	entities.forEach((entity, entityIndex) => {
		entity.occurrences.forEach((occurrence: any, occurrenceIndex) => {
			const { start_idx: from, end_idx: to } = occurrence;
			
			if (from >= 0 && to <= doc.content.size && from < to) {
				const hasModifier = modifiersByEntity.has(entity.raw_text.toLowerCase());
				
				if (!hasModifier) {
					const shouldMask = entity.shouldMask ?? true;
					const maskingClass = shouldMask ? 'pii-masked' : 'pii-unmasked';
					
					decorations.push(
						Decoration.inline(from, to, {
							class: `pii-highlight ${maskingClass}`,
							'data-pii-type': entity.type,
							'data-pii-label': entity.label,
							'data-pii-text': entity.raw_text,
							'data-pii-occurrence': occurrenceIndex.toString(),
							'data-should-mask': shouldMask.toString(),
							'data-entity-index': entityIndex.toString()
						})
					);
				}
			}
		});
	});

	// Add modifier decorations (higher priority)
	modifiers.forEach(modifier => {
		doc.nodesBetween(0, doc.content.size, (node, pos) => {
			if (node.isText && node.text) {
				const entityText = modifier.entity.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
				const regex = new RegExp(`\\b${entityText}\\b`, 'gi');
				let match;
				
				while ((match = regex.exec(node.text)) !== null) {
					const matchStart = pos + match.index;
					const matchEnd = matchStart + match[0].length;
					
					if (matchStart >= 0 && matchEnd <= doc.content.size && matchStart < matchEnd) {
											const decorationClass = modifier.action === 'string-mask' 
						? 'pii-modifier-highlight pii-modifier-mask'
						: 'pii-modifier-highlight pii-modifier-ignore';
						
						decorations.push(
							Decoration.inline(matchStart, matchEnd, {
								class: decorationClass,
								'data-modifier-entity': modifier.entity,
								'data-modifier-action': modifier.action,
								'data-modifier-type': modifier.type || '',
								'data-modifier-id': modifier.id,
								style: 'z-index: 10; position: relative;'
							})
						);
					}
				}
			}
		});
	});

	return decorations;
}

const piiDetectionPluginKey = new PluginKey<PiiDetectionState>('piiDetection');

export const PiiDetectionExtension = Extension.create<PiiDetectionOptions>({
	name: 'piiDetection',

	addOptions() {
		return {
			enabled: false,
			apiKey: '',
			conversationId: '',
			onPiiDetected: undefined,
			onPiiToggled: undefined,
			debounceMs: 500
		};
	},

	addProseMirrorPlugins() {
		const options = this.options;
		const { enabled, apiKey, onPiiDetected, onPiiToggled, debounceMs } = options;

		if (!enabled || !apiKey) {
			return [];
		}

		const piiSessionManager = PiiSessionManager.getInstance();
		piiSessionManager.setApiKey(apiKey);

		const performPiiDetection = async (plainText: string) => {
			if (!plainText.trim()) {
				return;
			}

			try {
				const knownEntities = piiSessionManager.getKnownEntitiesForApi(options.conversationId);

				const modifiers = piiSessionManager.getModifiersForApi(options.conversationId);
				const response = await maskPiiText(apiKey, [plainText], knownEntities, modifiers, false, false);
				
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
					const conversationEntities = options.conversationId
						? piiSessionManager.getConversationEntitiesForDisplay(options.conversationId)
						: piiSessionManager.getTemporaryStateEntities(); // ✅ Load temporary state for new chats
					
					// CRITICAL FIX: Merge plugin state + conversation state for complete context
					// Plugin state takes precedence (for same-message interactions)
					// Conversation state provides fallback (for cross-message persistence)
					const pluginEntities = state.entities || [];
					const existingEntitiesForMapping = [...pluginEntities];
					
					// Add conversation entities that aren't already in plugin state
					conversationEntities.forEach(convEntity => {
						if (!pluginEntities.find(pluginEntity => pluginEntity.label === convEntity.label)) {
							existingEntitiesForMapping.push(convEntity);
						}
					});
					
					console.log('PiiDetectionExtension: Using existing entities for mapping:', {
						pluginEntities: pluginEntities.length,
						conversationEntities: conversationEntities.length,
						totalForMapping: existingEntitiesForMapping.length,
						labels: existingEntitiesForMapping.map(e => `${e.label}:${e.shouldMask}`)
					});
					
					// Pass merged entities to preserve shouldMask state across messages
					const mappedEntities = mapPiiEntitiesToProseMirror(response.pii[0], state.positionMapping, existingEntitiesForMapping);
					
					// CRITICAL FIX: Sync the mapped entities back to session manager
					// This ensures session manager has the correct shouldMask states from plugin
					if (options.conversationId) {
						piiSessionManager.setConversationWorkingEntitiesWithMaskStates(options.conversationId, mappedEntities);
					} else {
						// For new chats, use temporary state
						if (!piiSessionManager.isTemporaryStateActive()) {
							piiSessionManager.activateTemporaryState();
						}
						piiSessionManager.setTemporaryStateEntities(mappedEntities);
					}

					const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'UPDATE_ENTITIES',
						entities: mappedEntities
					});
					
					editorView.dispatch(tr);

					if (onPiiDetected) {
						onPiiDetected(mappedEntities, response.text[0]);
					}
				}
			} catch (error) {
				console.error('PiiDetectionExtension: PII detection failed:', error);
			}
		};

		// Debounced version
		const debouncedDetection = debounce(performPiiDetection, debounceMs || 500);

		const plugin = new Plugin<PiiDetectionState>({
			key: piiDetectionPluginKey,
			
			state: {
				init(): PiiDetectionState {
					return {
						entities: [],
						positionMapping: null,
						isDetecting: false,
						lastText: '',
						needsSync: false
					};
				},
				
				apply(tr, prevState): PiiDetectionState {
					const newState = { ...prevState };
					
					const meta = tr.getMeta(piiDetectionPluginKey);
					if (meta) {
						switch (meta.type) {
							case 'UPDATE_ENTITIES':
								newState.entities = meta.entities || [];
								break;
								
							case 'SYNC_WITH_SESSION_MANAGER': {
								// Sync plugin state with session manager
								if (newState.positionMapping) {
									newState.entities = syncWithSessionManager(
										options.conversationId,
										piiSessionManager,
										newState.entities,
										newState.positionMapping,
										tr.doc
									);
								}
								break;
							}
								
							case 'TOGGLE_ENTITY_MASKING':
								const { entityIndex, occurrenceIndex } = meta;
								if (newState.entities[entityIndex]) {
									const entity = { ...newState.entities[entityIndex] };
									entity.shouldMask = !entity.shouldMask;
									newState.entities = [...newState.entities];
									newState.entities[entityIndex] = entity;
									
									const piiSessionManager = PiiSessionManager.getInstance();
									
									piiSessionManager.toggleEntityMasking(entity.label, occurrenceIndex, options.conversationId);
									
									
									// CRITICAL FIX: Mark that we need to sync with session manager on next transaction
									// This ensures that subsequent detections use the correct shouldMask state
									newState.needsSync = true;
									
									if (options.onPiiToggled) {
										options.onPiiToggled(newState.entities);
									}
								}
								break;
								
							case 'TRIGGER_DETECTION':
							case 'TRIGGER_DETECTION_WITH_MODIFIERS': {
								const currentMapping = buildPositionMapping(tr.doc);
								newState.positionMapping = currentMapping;
								
								if (currentMapping.plainText.trim()) {
									performPiiDetection(currentMapping.plainText);
								}
								break;
							}
								
							case 'RELOAD_CONVERSATION_STATE': {
								options.conversationId = meta.conversationId;
								
								const newMapping = buildPositionMapping(tr.doc);
								newState.positionMapping = newMapping;
								
								if (newMapping.plainText.trim()) {
									performPiiDetection(newMapping.plainText);
								}
								break;
							}
						}
					}
					
					if (tr.docChanged) {
						const newMapping = buildPositionMapping(tr.doc);
						newState.positionMapping = newMapping;
						
						// Remap existing entities to current document positions immediately
						if (newState.entities.length > 0) {
							// First, try to remap entities to current positions
							const remappedEntities = remapEntitiesForCurrentDocument(
								newState.entities,
								newMapping,
								tr.doc
							);
							
							// Then sync with session manager for external changes
							newState.entities = syncWithSessionManager(
								options.conversationId,
								piiSessionManager,
								remappedEntities,
								newMapping,
								tr.doc
							);
						}
						
						// CRITICAL FIX: If we need to sync after toggle, do it now BEFORE detection
						// This ensures shouldMask state is consistent before next detection
						if (newState.needsSync) {
							newState.entities = syncWithSessionManager(
								options.conversationId,
								piiSessionManager,
								newState.entities,
								newMapping,
								tr.doc
							);
							newState.needsSync = false;
						}
						
						// Trigger detection if text changed significantly
						if (!newState.isDetecting && newMapping.plainText !== newState.lastText) {
							newState.lastText = newMapping.plainText;
							
							if (newMapping.plainText.trim()) {
								debouncedDetection(newMapping.plainText);
							} else {
								// If text is empty, clear entities
								newState.entities = [];
							}
						}
					}
					
					return newState;
				}
			},

			props: {
				decorations(state) {
					const pluginState = piiDetectionPluginKey.getState(state);
					
					// Get modifiers from session manager (not ProseMirror extension state)
					const piiSessionManager = PiiSessionManager.getInstance();
					const modifiers = piiSessionManager.getModifiersForDisplay(options.conversationId);
					
					if (!pluginState?.entities.length && !modifiers.length) {
						return DecorationSet.empty;
					}
					
					const decorations = createPiiDecorations(pluginState?.entities || [], modifiers, state.doc);
					return DecorationSet.create(state.doc, decorations);
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
		// Helper function to update all entity masking states (DRY)
		const updateAllEntityMaskingStates = (shouldMask: boolean) => ({ state, dispatch }: any) => {
			const pluginState = piiDetectionPluginKey.getState(state);
			if (!pluginState?.entities.length) {
				return false; // No entities to update
			}

			const extensionOptions = this.options;
			const piiSessionManager = PiiSessionManager.getInstance();

			// Get current entities using the proper display method
			const currentEntities = piiSessionManager.getEntitiesForDisplay(extensionOptions.conversationId);
			
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
			} else if (extensionOptions.conversationId) {
				// Handle conversation state - update each entity individually for proper persistence
				currentEntities.forEach((entity: ExtendedPiiEntity) => {
					piiSessionManager.setEntityMaskingState(
						extensionOptions.conversationId!,
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
					entities: updatedPluginEntities
				});
				dispatch(tr);

				// Trigger onPiiToggled callback
				if (extensionOptions.onPiiToggled) {
					extensionOptions.onPiiToggled(updatedPluginEntities);
				}
			}

			return true;
		};

		return {
			triggerDetection: () => ({ state, dispatch }: any) => {
				if (dispatch) {
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'TRIGGER_DETECTION'
					});
					dispatch(tr);
					return true;
				}
				return false;
			},

			triggerDetectionForModifiers: () => ({ state, dispatch }: any) => {
				if (dispatch) {
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'TRIGGER_DETECTION_WITH_MODIFIERS'
					});
					dispatch(tr);
					return true;
				}
				return false;
			},

			syncWithSessionManager: () => ({ state, dispatch }: any) => {
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
			forceEntityRemapping: () => ({ state, dispatch }: any) => {
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
					entities: remappedEntities
				});
				
				dispatch(tr);
				return true;
			},

			reloadConversationState: (newConversationId: string) => ({ state, dispatch }: any) => {
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
			maskAllEntities: () => updateAllEntityMaskingStates(true)
		} as any;
	}
}); 