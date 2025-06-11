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
	conversationId: string;
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

	// Add PII entity decorations
	entities.forEach((entity, entityIndex) => {
		entity.occurrences.forEach((occurrence: any, occurrenceIndex) => {
			const { start_idx: from, end_idx: to } = occurrence;
			
			// Ensure positions are valid for the current document
			if (from >= 0 && to <= doc.content.size && from < to) {
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
		});
	});

	// Add modifier decorations (find ALL occurrences of modifier-affected words)
	if (modifiers.length > 0) {
		// Group modifiers by entity text for efficient processing
		const modifiersByEntity = new Map<string, PiiModifier[]>();
		modifiers.forEach(modifier => {
			const entityText = modifier.entity.toLowerCase();
			if (!modifiersByEntity.has(entityText)) {
				modifiersByEntity.set(entityText, []);
			}
			modifiersByEntity.get(entityText)!.push(modifier);
		});

		// Search for all occurrences of each modifier-affected word
		modifiersByEntity.forEach((entityModifiers, entityText) => {
			// Find all occurrences of this word in the document
			doc.nodesBetween(0, doc.content.size, (node, pos) => {
				if (node.isText && node.text) {
					const text = node.text.toLowerCase();
					const originalText = node.text;
					
					// Create regex for word boundaries to match whole words only
					const regex = new RegExp(`\\b${entityText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
					let match;
					
					while ((match = regex.exec(originalText)) !== null) {
						const matchStart = pos + match.index;
						const matchEnd = matchStart + match[0].length;
						
						// Ensure positions are valid
						if (matchStart >= 0 && matchEnd <= doc.content.size && matchStart < matchEnd) {
							// Determine the decoration class based on modifier types
							const hasIgnoreModifier = entityModifiers.some(m => m.type === 'ignore');
							const hasMaskModifier = entityModifiers.some(m => m.type === 'mask');
							
							let decorationClass = 'pii-modifier-highlight';
							if (hasMaskModifier) {
								// Mask modifiers get yellow font + green styling
								decorationClass = 'pii-modifier-highlight pii-modifier-mask';
							}
							
							decorations.push(
								Decoration.inline(matchStart, matchEnd, {
									class: decorationClass,
									'data-modifier-entity': entityModifiers[0].entity,
									'data-modifier-types': entityModifiers.map(m => m.type).join(','),
									'data-modifier-labels': entityModifiers.filter(m => m.label).map(m => m.label).join(',')
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
		type: modifier.type,
		entity: modifier.entity,
		...(modifier.label && { label: modifier.label })
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
		const { enabled, apiKey, conversationId, onPiiDetected, onPiiToggled, debounceMs } = options;

		console.log('PiiDetectionExtension: Initializing with options:', {
			enabled,
			hasApiKey: !!apiKey,
			conversationId,
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
				console.log('PiiDetectionExtension: Skipping detection - empty text');
				return;
			}

			console.log('PiiDetectionExtension: Starting PII detection for text:', plainText.substring(0, 100));

			try {
				// Get known entities from conversation state
				const knownEntities = conversationId
					? piiSessionManager.getKnownEntitiesForApi(conversationId)
					: [];

				console.log('PiiDetectionExtension: Using known entities:', knownEntities);

				// Get current modifiers from PiiModifierExtension state (read-only)
				const view = this.editor?.view;
				let modifiers: ShieldApiModifier[] = [];
				if (view) {
					const modifierState = piiModifierExtensionKey.getState(view.state);
					if (modifierState?.modifiers && modifierState.modifiers.length > 0) {
						modifiers = convertModifiersToApiFormat(modifierState.modifiers);
						console.log('PiiDetectionExtension: Found', modifiers.length, 'modifiers:', modifiers);
					} else {
						console.log('PiiDetectionExtension: No modifiers found in editor state');
					}
				} else {
					console.log('PiiDetectionExtension: No editor view available for reading modifiers');
				}

				const response = await maskPiiText(apiKey, [plainText], knownEntities, modifiers, false, false);
				
				console.log('PiiDetectionExtension: API request details:', {
					textLength: plainText.length,
					knownEntitiesCount: knownEntities.length,
					modifiersCount: modifiers.length,
					modifiers: modifiers,
					hasApiKey: !!apiKey
				});
				
				console.log('PiiDetectionExtension: API response:', response);

				if (response.pii && response.pii[0] && response.pii[0].length > 0) {
					// Get the editor view through the stored editor reference
					if (!view) {
						console.log('PiiDetectionExtension: No editor view available');
						return;
					}

					const state = piiDetectionPluginKey.getState(view.state);
					if (!state?.positionMapping) {
						console.log('PiiDetectionExtension: No position mapping available');
						return;
					}

					// Map PII entities to ProseMirror positions
					const mappedEntities = mapPiiEntitiesToProseMirror(response.pii[0], state.positionMapping);
					
					console.log('PiiDetectionExtension: Mapped entities:', mappedEntities);

					// Store entities in session manager
					if (conversationId) {
						piiSessionManager.setConversationEntities(conversationId, response.pii[0]);
					} else {
						piiSessionManager.setEntities(response.pii[0]);
					}

					// Update plugin state with new entities (don't touch modifiers - they're managed by PiiModifierExtension)
					const tr = view.state.tr.setMeta(piiDetectionPluginKey, {
						type: 'UPDATE_ENTITIES',
						entities: mappedEntities
					});
					
					view.dispatch(tr);

					// Notify parent component
					if (onPiiDetected) {
						onPiiDetected(mappedEntities, response.text[0]);
					}
				} else {
					console.log('PiiDetectionExtension: No PII entities found in response');
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
					let newState = prevState;

					// Handle document changes
					if (tr.docChanged) {
						// Rebuild position mapping
						const newMapping = buildPositionMapping(tr.doc);
						newState = {
							...newState,
							positionMapping: newMapping
						};

						console.log('PiiDetectionExtension: Document changed, new text:', newMapping.plainText.substring(0, 100));

						// Trigger PII detection if text changed significantly
						if (newMapping.plainText !== prevState.lastText && newMapping.plainText.trim()) {
							newState = {
								...newState,
								lastText: newMapping.plainText
							};

							console.log('PiiDetectionExtension: Triggering PII detection for text change');
							
							// Trigger debounced detection - the editor reference will be available when it executes
							debouncedDetection(newMapping.plainText);
						}

						// Map existing entities through the document change
						if (prevState.entities.length > 0) {
							const mappedEntities = prevState.entities.map(entity => ({
								...entity,
								occurrences: entity.occurrences.map((occurrence: any) => {
									// Use ProseMirror's mapping to update positions
									const newStart = tr.mapping.map(occurrence.start_idx);
									const newEnd = tr.mapping.map(occurrence.end_idx);
									return {
										...occurrence,
										start_idx: newStart,
										end_idx: newEnd
									};
								})
							}));
							
							newState = {
								...newState,
								entities: mappedEntities
							};
						}
					}

					// Handle plugin-specific meta actions
					const meta = tr.getMeta(piiDetectionPluginKey);
					if (meta) {
						console.log('PiiDetectionExtension: Handling meta action:', meta.type);
						switch (meta.type) {
							case 'UPDATE_ENTITIES':
								newState = {
									...newState,
									entities: meta.entities
								};
								break;
							case 'TRIGGER_DETECTION_WITH_MODIFIERS':
								// Trigger detection when modifiers change
								if (newState.positionMapping?.plainText.trim()) {
									console.log('PiiDetectionExtension: Triggering detection due to modifier change');
									debouncedDetection(newState.positionMapping.plainText);
								} else {
									console.log('PiiDetectionExtension: Skipping detection - no text content');
								}
								break;
							case 'TOGGLE_ENTITY_MASKING':
								const { entityIndex, occurrenceIndex } = meta;
								const updatedEntities = [...newState.entities];
								if (updatedEntities[entityIndex]) {
									updatedEntities[entityIndex] = {
										...updatedEntities[entityIndex],
										shouldMask: !updatedEntities[entityIndex].shouldMask
									};
									newState = {
										...newState,
										entities: updatedEntities
									};
									
									// Update session manager with the new masking state
									const piiSessionManager = PiiSessionManager.getInstance();
									const toggledEntity = updatedEntities[entityIndex];
									if (conversationId) {
										piiSessionManager.toggleConversationEntityMasking(
											conversationId,
											toggledEntity.label,
											occurrenceIndex
										);
									} else {
										piiSessionManager.toggleEntityMasking(toggledEntity.label, occurrenceIndex);
									}
									
									if (onPiiToggled) {
										onPiiToggled(updatedEntities);
									}
								}
								break;
						}
					}

					return newState;
				}
			},

			props: {
				decorations(state) {
					const pluginState = piiDetectionPluginKey.getState(state);
					if (!pluginState?.entities.length) {
						// Check if we have modifiers even without PII entities
						const modifierState = piiModifierExtensionKey.getState(state);
						if (!modifierState?.modifiers.length) {
							return DecorationSet.empty;
						}
					}
					
					// Get modifiers from the PiiModifierExtension state
					const modifierState = piiModifierExtensionKey.getState(state);
					const modifiers = modifierState?.modifiers || [];
					
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
			// Command to manually trigger PII detection
			detectPii: () => ({ state, dispatch }: { state: any; dispatch: any }) => {
				const pluginState = piiDetectionPluginKey.getState(state);
				
				if (pluginState?.positionMapping && dispatch) {
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'TRIGGER_DETECTION',
						text: pluginState.positionMapping.plainText
					});
					dispatch(tr);
					return true;
				}
				
				return false;
			},

			// Command to trigger PII detection when modifiers change
			triggerDetectionForModifiers: () => ({ state, dispatch }: { state: any; dispatch: any }) => {
				if (dispatch) {
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'TRIGGER_DETECTION_WITH_MODIFIERS'
					});
					dispatch(tr);
					return true;
				}
				return false;
			},

			// Command to update PII entities (for external updates)
			updatePiiEntities: (entities: ExtendedPiiEntity[]) => ({ state, dispatch }: { state: any; dispatch: any }) => {
				if (dispatch) {
					const tr = state.tr.setMeta(piiDetectionPluginKey, {
						type: 'UPDATE_ENTITIES',
						entities
					});
					dispatch(tr);
					return true;
				}
				return false;
			},

			// Command to get current PII state
			getPiiState: () => ({ state }: { state: any }) => {
				return piiDetectionPluginKey.getState(state);
			}
		} as any;
	}
}); 