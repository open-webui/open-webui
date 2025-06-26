import { Extension } from '@tiptap/core';
import { Plugin, PluginKey, TextSelection } from 'prosemirror-state';
import { Decoration, DecorationSet } from 'prosemirror-view';
import type { Node as ProseMirrorNode } from 'prosemirror-model';
import type { ExtendedPiiEntity } from '$lib/utils/pii';
import type { PiiEntity } from '$lib/apis/pii';
import { maskPiiText, type KnownPiiEntity, type ShieldApiModifier } from '$lib/apis/pii';
import { debounce, PiiSessionManager } from '$lib/utils/pii';
import type { PiiModifier } from './PiiModifierExtension';
import { piiModifierExtensionKey } from './PiiModifierExtension';

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
						const decorationClass = modifier.action === 'mask' 
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

// Convert PiiModifier objects to ShieldApiModifier format
function convertModifiersToApiFormat(modifiers: PiiModifier[]): ShieldApiModifier[] {
	return modifiers.map(modifier => ({
		action: modifier.action,
		entity: modifier.entity,
		...(modifier.type && { type: modifier.type })
	}));
}

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
				const knownEntities = options.conversationId
					? piiSessionManager.getKnownEntitiesForApi(options.conversationId)
					: piiSessionManager.getGlobalKnownEntitiesForApi();

				const modifiers = piiSessionManager.getModifiersForApi(options.conversationId);
				const response = await maskPiiText(apiKey, [plainText], knownEntities, modifiers, false, false);
				
				if (response.pii && response.pii[0] && response.pii[0].length > 0) {
					const editorView = this.editor?.view;
					const state = piiDetectionPluginKey.getState(editorView?.state);
					
					if (!editorView || !state?.positionMapping) {
						console.warn('PiiDetectionExtension: No editor view or position mapping available');
						return;
					}

					// Pass existing entities to preserve shouldMask state
					const mappedEntities = mapPiiEntitiesToProseMirror(response.pii[0], state.positionMapping, state.entities);
					
					if (options.conversationId) {
						piiSessionManager.setConversationEntitiesPreservingModifiers(options.conversationId, response.pii[0]);
					} else {
						piiSessionManager.appendGlobalEntities(response.pii[0]);
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
						lastText: ''
					};
				},
				
				apply(tr, prevState): PiiDetectionState {
					let newState = { ...prevState };
					
					const meta = tr.getMeta(piiDetectionPluginKey);
					if (meta) {
						switch (meta.type) {
							case 'UPDATE_ENTITIES':
								newState.entities = meta.entities || [];
								break;
								
							case 'TOGGLE_ENTITY_MASKING':
								const { entityIndex, occurrenceIndex } = meta;
								if (newState.entities[entityIndex]) {
									const entity = { ...newState.entities[entityIndex] };
									entity.shouldMask = !entity.shouldMask;
									newState.entities = [...newState.entities];
									newState.entities[entityIndex] = entity;
									
									const piiSessionManager = PiiSessionManager.getInstance();
									if (options.conversationId) {
										piiSessionManager.toggleConversationEntityMasking(
											options.conversationId,
											entity.label,
											occurrenceIndex
										);
									} else {
										piiSessionManager.toggleEntityMasking(entity.label, occurrenceIndex);
									}
									
									if (options.onPiiToggled) {
										options.onPiiToggled(newState.entities);
									}
								}
								break;
								
							case 'TRIGGER_DETECTION':
							case 'TRIGGER_DETECTION_WITH_MODIFIERS':
								const currentMapping = buildPositionMapping(tr.doc);
								newState.positionMapping = currentMapping;
								
								if (currentMapping.plainText.trim()) {
									performPiiDetection(currentMapping.plainText);
								}
								break;
								
							case 'RELOAD_CONVERSATION_STATE':
								options.conversationId = meta.conversationId;
								
								const newMapping = buildPositionMapping(tr.doc);
								newState.positionMapping = newMapping;
								
								if (newMapping.plainText.trim()) {
									performPiiDetection(newMapping.plainText);
								}
								break;
						}
					}
					
					if (tr.docChanged) {
						newState.positionMapping = buildPositionMapping(tr.doc);
						
						if (!newState.isDetecting && newState.positionMapping.plainText !== newState.lastText) {
							newState.lastText = newState.positionMapping.plainText;
							if (newState.positionMapping.plainText.trim()) {
								debouncedDetection(newState.positionMapping.plainText);
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
					const modifiers = options.conversationId 
						? piiSessionManager.getConversationModifiers(options.conversationId)
						: piiSessionManager.getGlobalModifiers();
					
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
			unmaskAllEntities: () => ({ state, dispatch }: any) => {
				const pluginState = piiDetectionPluginKey.getState(state);
				if (!pluginState?.entities.length) {
					return false; // No entities to unmask
				}

				// Access extension options
				const extensionOptions = this.options;

				// Create new array with all entities unmasked
				const unmaskedEntities = pluginState.entities.map(entity => ({
					...entity,
					shouldMask: false
				}));

				// Update session manager directly
				const piiSessionManager = PiiSessionManager.getInstance();
				
				if (extensionOptions.conversationId) {
					// Get current entities from session manager
					const currentEntities = piiSessionManager.getConversationEntities(extensionOptions.conversationId);
					
					// Update all entities to shouldMask: false
					const updatedEntities = currentEntities.map(entity => ({
						...entity,
						shouldMask: false
					}));
					
					// Set the updated entities back to session manager
					piiSessionManager.setConversationEntities(extensionOptions.conversationId, updatedEntities);
				} else {
					// Get current global entities from session manager
					const currentEntities = piiSessionManager.getEntities();
					
					// Update all entities to shouldMask: false
					const updatedEntities = currentEntities.map(entity => ({
						...entity,
						shouldMask: false
					}));
					
					// Set the updated entities back to session manager
					piiSessionManager.setEntities(updatedEntities);
				}

				// Update plugin state
				if (dispatch) {
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'UPDATE_ENTITIES',
						entities: unmaskedEntities
					});
					dispatch(tr);

					// Trigger onPiiToggled callback
					if (extensionOptions.onPiiToggled) {
						extensionOptions.onPiiToggled(unmaskedEntities);
					}
				}

				return true;
			}
		} as any;
	}
}); 