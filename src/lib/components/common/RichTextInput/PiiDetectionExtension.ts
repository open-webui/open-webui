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

	console.log('PiiDetectionExtension: Built position mapping:', {
		plainTextLength: plainText.length,
		plainTextPreview: plainText.substring(0, 200),
		mappingSize: plainTextToProseMirror.size
	});

	return {
		plainTextToProseMirror,
		proseMirrorToPlainText,
		plainText: plainText.trim()
	};
}

// Convert PII entity positions from plain text to ProseMirror positions
function mapPiiEntitiesToProseMirror(
	entities: PiiEntity[],
	mapping: PositionMapping
): ExtendedPiiEntity[] {
	return entities.map(entity => ({
		...entity,
		shouldMask: true,
		occurrences: entity.occurrences.map((occurrence: any) => {
			const plainTextStart = occurrence.start_idx;
			const plainTextEnd = occurrence.end_idx;
			
			// Get ProseMirror positions (with fallback)
			const proseMirrorStart = mapping.plainTextToProseMirror.get(plainTextStart) ?? plainTextStart + 1;
			// For end position, ensure we include the last character (PII API uses exclusive end, ProseMirror uses inclusive)
			const proseMirrorEnd = mapping.plainTextToProseMirror.get(plainTextEnd - 1) ?? (plainTextEnd - 1 + 1);
			
			// Extract the actual text for verification
			const originalText = mapping.plainText.substring(plainTextStart, plainTextEnd);
			
			console.log('PiiDetectionExtension: Mapping entity position:', {
				entity: entity.label,
				plainText: { start: plainTextStart, end: plainTextEnd },
				proseMirror: { start: proseMirrorStart, end: proseMirrorEnd + 1 }, // +1 for inclusive end
				originalText,
				expectedText: entity.raw_text
			});
			
			return {
				...occurrence,
				start_idx: proseMirrorStart,
				end_idx: proseMirrorEnd + 1 // Make end position inclusive for ProseMirror
			};
		})
	}));
}

// Create decorations for PII entities and modifier-affected text
function createPiiDecorations(entities: ExtendedPiiEntity[], modifiers: PiiModifier[], doc: ProseMirrorNode): Decoration[] {
	const decorations: Decoration[] = [];

	// Group modifiers by entity text for efficient lookup
	const modifiersByEntity = new Map<string, PiiModifier>();
	modifiers.forEach(modifier => {
		modifiersByEntity.set(modifier.entity.toLowerCase(), modifier);
	});

	// Add PII entity decorations first (lower priority)
	entities.forEach((entity, entityIndex) => {
		entity.occurrences.forEach((occurrence: any, occurrenceIndex) => {
			const { start_idx: from, end_idx: to } = occurrence;
			
			// Ensure positions are valid for the current document
			if (from >= 0 && to <= doc.content.size && from < to) {
				// Check if this entity has a modifier (modifier takes precedence)
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

	// Add modifier decorations (higher priority - these take precedence)
	if (modifiers.length > 0) {
		modifiers.forEach(modifier => {
			// Find all occurrences of this modifier's entity in the document
			doc.nodesBetween(0, doc.content.size, (node, pos) => {
				if (node.isText && node.text) {
					const originalText = node.text;
					
					// Create regex for word boundaries to match whole words only
					const entityText = modifier.entity.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
					const regex = new RegExp(`\\b${entityText}\\b`, 'gi');
					let match;
					
					while ((match = regex.exec(originalText)) !== null) {
						const matchStart = pos + match.index;
						const matchEnd = matchStart + match[0].length;
						
						// Ensure positions are valid
						if (matchStart >= 0 && matchEnd <= doc.content.size && matchStart < matchEnd) {
							// Determine the decoration class based on modifier action
							let decorationClass = 'pii-modifier-highlight';
							if (modifier.action === 'mask') {
								decorationClass = 'pii-modifier-highlight pii-modifier-mask';
							} else if (modifier.action === 'ignore') {
								decorationClass = 'pii-modifier-highlight pii-modifier-ignore';
							}
							
							decorations.push(
								Decoration.inline(matchStart, matchEnd, {
									class: decorationClass,
									'data-modifier-entity': modifier.entity,
									'data-modifier-action': modifier.action,
									'data-modifier-type': modifier.type || '',
									'data-modifier-id': modifier.id,
									// Add higher z-index to ensure precedence
									style: 'z-index: 10; position: relative;'
								})
							);
						}
					}
				}
			});
		});
	}

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

		console.log('PiiDetectionExtension: Initializing with options:', {
			enabled,
			hasApiKey: !!apiKey,
			conversationId: options.conversationId,
			debounceMs
		});

		if (!enabled || !apiKey) {
			console.log('PiiDetectionExtension: Disabled - missing enabled flag or API key');
			return [];
		}

		const piiSessionManager = PiiSessionManager.getInstance();
		piiSessionManager.setApiKey(apiKey);

		// Store reference to plugin for accessing view
		let pluginInstance: any = null;

		// Create a PII detection function with proper scope
		const performPiiDetection = async (plainText: string) => {
			if (!plainText.trim()) {
				return;
			}

			console.log('PiiDetectionExtension: Starting PII detection', {
				textLength: plainText.length,
				conversationId: options.conversationId,
				textPreview: plainText.substring(0, 100)
			});

			try {
				// Ensure conversation state is loaded (Note: localStorage deprecated, using SQLite via Chat.svelte)
				// State should already be loaded from chat data in Chat.svelte
				if (options.conversationId) {
					console.log('PiiDetectionExtension: Using conversation state from SQLite:', options.conversationId);
				}
				
				// Get known entities and modifiers from appropriate source
				const knownEntities = options.conversationId
					? piiSessionManager.getKnownEntitiesForApi(options.conversationId)
					: piiSessionManager.getGlobalKnownEntitiesForApi();

				const modifiers = piiSessionManager.getModifiersForApi(options.conversationId);

				console.log('PiiDetectionExtension: API call context:', {
					source: options.conversationId ? `conversation(${options.conversationId})` : 'global',
					knownEntitiesCount: knownEntities.length,
					modifiersCount: modifiers.length
				});

				// Call PII detection API
				const response = await maskPiiText(apiKey, [plainText], knownEntities, modifiers, false, false);
				
				if (response.pii && response.pii[0] && response.pii[0].length > 0) {
					const editorView = this.editor?.view;
					const state = piiDetectionPluginKey.getState(editorView?.state);
					
					if (!editorView || !state?.positionMapping) {
						console.warn('PiiDetectionExtension: No editor view or position mapping available');
						return;
					}

					// Map PII entities to ProseMirror positions
					const mappedEntities = mapPiiEntitiesToProseMirror(response.pii[0], state.positionMapping);
					
					// Store entities in session manager (will trigger SQLite save automatically)
					if (options.conversationId) {
						piiSessionManager.setConversationState(options.conversationId, response.pii[0]);
					} else {
						piiSessionManager.appendGlobalEntities(response.pii[0]);
					}

					// Update plugin state
					const tr = editorView.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'UPDATE_ENTITIES',
						entities: mappedEntities
					});
					
					editorView.dispatch(tr);

					// Notify parent component
					if (onPiiDetected) {
						onPiiDetected(mappedEntities, response.text[0]);
					}

					console.log(`PiiDetectionExtension: Detected ${mappedEntities.length} PII entities`);
				}
			} catch (error) {
				console.error('PiiDetectionExtension: PII detection failed:', error);
			}
		};

		// Debounced version
		const debouncedDetection = debounce(performPiiDetection, debounceMs || 500);

		pluginInstance = new Plugin<PiiDetectionState>({
			key: piiDetectionPluginKey,
			
			state: {
				init(): PiiDetectionState {
					console.log('PiiDetectionExtension: Initializing plugin state');
					return {
						entities: [],
						positionMapping: null,
						isDetecting: false,
						lastText: ''
					};
				},
				
				apply(tr, prevState): PiiDetectionState {
					let newState = { ...prevState };
					
					// Handle plugin meta actions
					const meta = tr.getMeta(piiDetectionPluginKey);
					if (meta) {
						console.log('PiiDetectionExtension: Processing meta action:', meta.type);
						
						switch (meta.type) {
							case 'UPDATE_ENTITIES':
								console.log('PiiDetectionExtension: Updating entities from meta');
								newState.entities = meta.entities || [];
								break;
								
							case 'TOGGLE_ENTITY_MASKING':
								console.log('PiiDetectionExtension: Toggling entity masking');
								const { entityIndex, occurrenceIndex } = meta;
								if (newState.entities[entityIndex]) {
									const entity = { ...newState.entities[entityIndex] };
									entity.shouldMask = !entity.shouldMask;
									newState.entities = [...newState.entities];
									newState.entities[entityIndex] = entity;
									
									// Update session manager
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
									
									// Trigger callback
									if (options.onPiiToggled) {
										options.onPiiToggled(newState.entities);
									}
								}
								break;
								
							case 'TRIGGER_DETECTION':
							case 'TRIGGER_DETECTION_WITH_MODIFIERS':
								console.log('PiiDetectionExtension: Triggering detection via meta');
								// Get current position mapping
								const currentMapping = buildPositionMapping(tr.doc);
								newState.positionMapping = currentMapping;
								
								// Trigger detection
								if (currentMapping.plainText.trim()) {
									performPiiDetection(currentMapping.plainText);
								}
								break;
								
							case 'RELOAD_CONVERSATION_STATE':
								console.log(`PiiDetectionExtension: Reloading conversation state for ${meta.conversationId}`);
								
								// Update the conversation ID
								options.conversationId = meta.conversationId;
								
								// Load the conversation state (Note: State should already be loaded from SQLite via Chat.svelte)
								const piiSessionManager = PiiSessionManager.getInstance();
								if (meta.conversationId) {
									console.log(`PiiDetectionExtension: Using conversation state from SQLite for ${meta.conversationId}`);
								}
								
								// Trigger detection with the new conversation context
								const newMapping = buildPositionMapping(tr.doc);
								newState.positionMapping = newMapping;
								
								if (newMapping.plainText.trim()) {
									performPiiDetection(newMapping.plainText);
								}
								break;
						}
					}
					
					// Update position mapping if document changed
					if (tr.docChanged) {
						console.log('PiiDetectionExtension: Document changed, updating position mapping');
						newState.positionMapping = buildPositionMapping(tr.doc);
						
						// Trigger detection on text change
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
					console.log('PiiDetectionExtension: Creating', decorations.length, 'decorations');
					return DecorationSet.create(state.doc, decorations);
				},

				handleClick(view, pos, event) {
					const target = event.target as HTMLElement;
					
					if (target.classList.contains('pii-highlight')) {
						console.log('PiiDetectionExtension: PII highlight clicked');
						const entityIndex = parseInt(target.getAttribute('data-entity-index') || '0');
						const occurrenceIndex = parseInt(target.getAttribute('data-pii-occurrence') || '0');

						// Toggle entity masking
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

		return [pluginInstance];
	},

	addCommands() {
		return {
			// Trigger PII detection manually
			triggerDetection: () => ({ state, dispatch }: any) => {
				console.log('PiiDetectionExtension: Manual detection triggered');
				if (dispatch) {
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'TRIGGER_DETECTION'
					});
					dispatch(tr);
					return true;
				}
				return false;
			},

			// Trigger detection for modifiers (when modifiers change)
			triggerDetectionForModifiers: () => ({ state, dispatch }: any) => {
				console.log('PiiDetectionExtension: Detection triggered for modifier changes');
				if (dispatch) {
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'TRIGGER_DETECTION_WITH_MODIFIERS'
					});
					dispatch(tr);
					return true;
				}
				return false;
			},

			// Reload conversation state when conversation ID changes
			reloadConversationState: (newConversationId: string) => ({ state, dispatch }: any) => {
				console.log(`PiiDetectionExtension: Reloading conversation state for ${newConversationId}`);
				
				if (dispatch) {
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'RELOAD_CONVERSATION_STATE',
						conversationId: newConversationId
					});
					dispatch(tr);
					return true;
				}
				return false;
			}
		} as any;
	}
}); 