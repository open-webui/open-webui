import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import type { Node as ProseMirrorNode } from 'prosemirror-model';
import type { EditorView } from 'prosemirror-view';
import type { EditorState, Transaction } from 'prosemirror-state';
import { PiiSessionManager } from '$lib/utils/pii';
import { generateModifierId, findCompleteWordsRobust } from './PiiTextUtils';
import { findTokenizedWords } from './PiiTokenization';
import { getPiiConfig, type PiiExtensionConfig } from './PiiExtensionConfig';
import { PiiPerformanceTracker } from './PiiPerformanceOptimizer';
import { piiDetectionPluginKey } from './PiiDetectionExtension';

// TypeScript interfaces for TipTap command context
interface CommandContext {
	state: EditorState;
	dispatch?: (tr: Transaction) => void;
	view?: EditorView;
}

// Types for the Shield API modifiers
export type ModifierAction = 'ignore' | 'string-mask';

export interface PiiModifier {
	action: ModifierAction;
	entity: string;
	type?: string; // PII type - required for 'string-mask' action
	id: string; // Unique identifier for this modifier
	from?: number; // Optional: ProseMirror start position for exact selection
	to?: number; // Optional: ProseMirror end position for exact selection
}

// Options for the extension
export interface PiiModifierOptions {
	enabled: boolean;
	conversationId?: string; // Add conversation ID for proper state management
	onModifiersChanged?: (modifiers: PiiModifier[]) => void;
	availableLabels?: string[]; // List of available PII labels for mask type
	showPiiHoverMenu?: (menuData: PiiHoverMenuData) => void; // Function to show Svelte hover menu
	hidePiiHoverMenu?: () => void; // Function to hide Svelte hover menu
}

// Interface for hover menu data passed to PiiHoverMenu.svelte component
// This replaces the old DOM-based createHoverMenu function with a proper Svelte component
export interface PiiHoverMenuData {
	wordInfo: { word: string; from: number; to: number; x: number; y: number };
	showIgnoreButton: boolean;
	existingModifiers: PiiModifier[];
	showTextField: boolean;
	currentLabel?: string;
	onIgnore: () => void;
	onMask: (label: string) => void;
	onRemoveModifier: (modifierId: string) => void;
	onInputFocused: (focused: boolean) => void;
	onClose: () => void;
	onMouseEnter: () => void;
	onMouseLeave: () => void;
}

// Extension state
interface PiiModifierState {
	modifiers: PiiModifier[];
	currentConversationId?: string; // Track the current conversation ID
	hoveredWordInfo: {
		word: string;
		from: number;
		to: number;
		x: number;
		y: number;
	} | null;
	selectedTextInfo: {
		selectedText: string;
		tokenizedWords: Array<{ word: string; from: number; to: number }>;
		from: number;
		to: number;
		x: number;
		y: number;
	} | null;
}

const piiModifierExtensionKey = new PluginKey<PiiModifierState>('piiModifier');

// Export the plugin key so other extensions can access the state
export { piiModifierExtensionKey };

// generateModifierId function moved to PiiTextUtils.ts

// WORD_TOKENIZER_PATTERN moved to PiiTokenization.ts

// findTokenizedWords function moved to PiiTokenization.ts

// Find existing PII or modifier element under mouse cursor
function findExistingEntityAtPosition(
	view: EditorView,
	clientX: number,
	clientY: number,
	config: PiiExtensionConfig
): { from: number; to: number; text: string; type: 'pii' | 'modifier' } | null {
	const target = document.elementFromPoint(clientX, clientY) as HTMLElement;
	if (!target) return null;

	const getPositionFromCoords = (text: string) => {
		const pos = view.posAtCoords({ left: clientX, top: clientY });
		if (!pos) return null;
		const textLength = text.length;
		return {
			from: Math.max(0, pos.pos - Math.floor(textLength / 2)),
			to: Math.min(view.state.doc.content.size, pos.pos + Math.ceil(textLength / 2))
		};
	};

	// Check PII element
	const piiElement = target.closest('.pii-highlight');
	if (piiElement) {
		const piiText = piiElement.getAttribute('data-pii-text') || piiElement.textContent || '';
		const piiLabel = piiElement.getAttribute('data-pii-label') || '';
		if (piiText.length >= config.textProcessing.minTextLengthForMatching) {
			try {
				const piiDetectionPluginKey = new PluginKey('piiDetection');
				interface PiiDetectionState {
					entities?: Array<{
						label: string;
						occurrences: Array<{ start_idx: number; end_idx: number }>;
					}>;
				}
				const piiState = piiDetectionPluginKey.getState(view.state) as PiiDetectionState;
				const matchingEntity = piiState?.entities?.find((entity) => entity.label === piiLabel);
				if (matchingEntity?.occurrences?.length && matchingEntity.occurrences.length > 0) {
					const occurrence = matchingEntity.occurrences[0];
					return { from: occurrence.start_idx, to: occurrence.end_idx, text: piiText, type: 'pii' };
				}
			} catch {
				// Fall through to position-based approach
			}

			const position = getPositionFromCoords(piiText);
			if (position) return { ...position, text: piiText, type: 'pii' };
		}
	}

	// Check modifier element
	const modifierElement = target.closest('.pii-modifier-highlight');
	if (modifierElement) {
		const modifierText =
			modifierElement.getAttribute('data-modifier-entity') || modifierElement.textContent || '';
		if (modifierText.length >= config.textProcessing.minTextLengthForMatching) {
			const position = getPositionFromCoords(modifierText);
			if (position) return { ...position, text: modifierText, type: 'modifier' };
		}
	}

	return null;
}

// Label autocompletion and matching functions are now handled by PiiHoverMenu.svelte

// Deprecated functions have been removed - now using PiiHoverMenu.svelte component

// Selection menus are now handled by BubbleMenu + PiiModifierButtons.svelte

export const PiiModifierExtension = Extension.create<PiiModifierOptions>({
	name: 'piiModifier',

	addOptions() {
		return {
			enabled: false,
			conversationId: '',
			onModifiersChanged: undefined,
			availableLabels: [
				'PERSON',
				'EMAIL',
				'PHONE_NUMBER',
				'ADDRESS',
				'SSN',
				'CREDIT_CARD',
				'DATE_TIME',
				'IP_ADDRESS',
				'URL',
				'IBAN',
				'MEDICAL_LICENSE',
				'US_PASSPORT',
				'US_DRIVER_LICENSE'
			]
		};
	},

	onCreate() {
		// Extension initialization
	},

	addProseMirrorPlugins() {
		const options = this.options;
		const { enabled, conversationId, onModifiersChanged } = options;
		const config = getPiiConfig();

		if (!enabled) {
			return [];
		}

		let isHoverMenuShowing = false;
		let hoverTimeout: number | null = null;
		let menuCloseTimeout: ReturnType<typeof setTimeout> | null = null;
		let isInputFocused = false;
		// Selection handling is now in BubbleMenu + PiiModifierButtons.svelte

		const plugin = new Plugin<PiiModifierState>({
			key: piiModifierExtensionKey,

			state: {
				init(): PiiModifierState {
					const piiSessionManager = PiiSessionManager.getInstance();

					if (conversationId) {
						piiSessionManager.loadConversationState(conversationId);
					}

					const loadedModifiers = piiSessionManager.getModifiersForDisplay(conversationId);

					return {
						modifiers: loadedModifiers,
						currentConversationId: conversationId,
						hoveredWordInfo: null,
						selectedTextInfo: null
					};
				},

				apply(tr, prevState): PiiModifierState {
					const tracker = PiiPerformanceTracker.getInstance();
					tracker.recordStateUpdate();

					let newState = { ...prevState };

					const meta = tr.getMeta(piiModifierExtensionKey);
					if (meta) {
						switch (meta.type) {
							case 'RELOAD_CONVERSATION_MODIFIERS': {
								tracker.recordSyncOperation();
								const piiSessionManagerReload = PiiSessionManager.getInstance();
								const reloadConversationId = meta.conversationId;

								if (reloadConversationId) {
									piiSessionManagerReload.loadConversationState(reloadConversationId);
								}

								const reloadedModifiers =
									piiSessionManagerReload.getModifiersForDisplay(reloadConversationId);

								newState = {
									...newState,
									modifiers: reloadedModifiers,
									currentConversationId: reloadConversationId
								};

								if (onModifiersChanged) {
									onModifiersChanged(reloadedModifiers);
								}
								break;
							}

							case 'ADD_MODIFIER': {
								// Align selection to the provided entity within the selected range (fix concatenations across nodes)
								let selFrom = typeof meta.from === 'number' ? meta.from : 0;
								let selTo = typeof meta.to === 'number' ? meta.to : 0;
								if (selFrom > selTo) {
									[selFrom, selTo] = [selTo, selFrom];
								}
								const doc = tr.doc as ProseMirrorNode;
								const docSize = doc.content.size;
								selFrom = Math.max(0, Math.min(selFrom, docSize));
								selTo = Math.max(0, Math.min(selTo, docSize));

								const rawEntity = (meta.entity || '').normalize('NFKC').trim();
								let finalFrom = selFrom;
								let finalTo = selTo;
								let finalEntity = rawEntity;

								// Simplified ADD_MODIFIER logic - use provided entity text directly
								if (meta.isExistingPii && rawEntity) {
									// Use the entity text and positions as provided - no tokenization needed
									// This prevents "und" being selected from "wachsenden Entwickler- und Projektteams"
									finalEntity = rawEntity;
									finalFrom = selFrom;
									finalTo = selTo;
								} else {
									// For new text selections, use provided entity text directly - no complex tokenization
									finalEntity = rawEntity || doc.textBetween(selFrom, selTo, '\n', '\0').trim();
									finalFrom = selFrom;
									finalTo = selTo;
								}

								// Skip if no valid entity text
								if (!finalEntity) {
									break;
								}

								const newModifier: PiiModifier = {
									id: generateModifierId(),
									action: meta.modifierAction,
									entity: finalEntity,
									type: meta.piiType,
									from: finalFrom,
									to: finalTo
								};

								// Replace any existing modifier for the same entity text (case-insensitive)
								const filteredModifiers = newState.modifiers.filter(
									(modifier) => modifier.entity.toLowerCase() !== finalEntity.toLowerCase()
								);

								const updatedModifiers = [...filteredModifiers, newModifier];

								newState = {
									...newState,
									modifiers: updatedModifiers
								};

								const piiSessionManager = PiiSessionManager.getInstance();
								const addConversationId = newState.currentConversationId;
								if (addConversationId) {
									piiSessionManager.setConversationModifiers(addConversationId, updatedModifiers);
								} else {
									piiSessionManager.setTemporaryModifiers(updatedModifiers);
								}

								// Note: Fast mask-update API call will be triggered by the command that calls this transaction

								if (onModifiersChanged) {
									onModifiersChanged(updatedModifiers);
								}
								break;
							}

							case 'REMOVE_MODIFIER': {
								const piiSessionManagerRemove = PiiSessionManager.getInstance();
								const removeConversationId = newState.currentConversationId;

								// Use dedicated removal methods instead of merging
								if (removeConversationId) {
									piiSessionManagerRemove.removeConversationModifier(
										removeConversationId,
										meta.modifierId
									);
								} else {
									piiSessionManagerRemove.removeTemporaryModifier(meta.modifierId);
								}

								// Update the plugin state to reflect the removal
								const remainingModifiers = newState.modifiers.filter(
									(m) => m.id !== meta.modifierId
								);
								newState = {
									...newState,
									modifiers: remainingModifiers
								};

								// Note: Fast mask-update API call will be triggered by the command that calls this transaction

								if (onModifiersChanged) {
									onModifiersChanged(remainingModifiers);
								}
								break;
							}

							case 'CLEAR_MODIFIERS': {
								newState = {
									...newState,
									modifiers: []
								};

								const piiSessionManagerClear = PiiSessionManager.getInstance();
								const clearConversationId = newState.currentConversationId;
								if (clearConversationId) {
									piiSessionManagerClear.setConversationModifiers(clearConversationId, []);
								} else {
									piiSessionManagerClear.setTemporaryModifiers([]);
								}

								// Note: Fast mask-update API call will be triggered by the command that calls this transaction

								if (onModifiersChanged) {
									onModifiersChanged([]);
								}
								break;
							}
						}
					}

					return newState;
				}
			},

			props: {
				handleClick(view, _pos, event) {
					// Check if clicking on a text element with a mask modifier
					const existingEntity = findExistingEntityAtPosition(
						view,
						event.clientX,
						event.clientY,
						config
					);

					if (existingEntity) {
						// Get current conversation ID from plugin state
						const pluginState = piiModifierExtensionKey.getState(view.state);
						const currentConversationId = pluginState?.currentConversationId;

						// Get session modifiers
						const piiSessionManager = PiiSessionManager.getInstance();
						if (currentConversationId) {
							piiSessionManager.loadConversationState(currentConversationId);
						}

						const sessionModifiers =
							piiSessionManager.getModifiersForDisplay(currentConversationId);
						const entityText = existingEntity.text;

						// Find mask modifier for this entity
						const maskModifier = sessionModifiers.find(
							(modifier) =>
								modifier.action === 'string-mask' &&
								modifier.entity.toLowerCase() === entityText.toLowerCase()
						);

						if (maskModifier) {
							console.log(
								'PiiModifierExtension: Removing mask modifier and hiding entity:',
								entityText
							);

							// Create transaction with both meta actions
							const tr = view.state.tr
								.setMeta(piiModifierExtensionKey, {
									type: 'REMOVE_MODIFIER',
									modifierId: maskModifier.id
								})
								.setMeta(piiDetectionPluginKey, {
									type: 'TEMPORARILY_HIDE_ENTITY',
									entityText: entityText
								});

							view.dispatch(tr);

							// Prevent further event handling
							event.preventDefault();
							return true;
						}
					}

					// Close hover menu if clicking outside of it
					if (isHoverMenuShowing && options.hidePiiHoverMenu) {
						// Let the Svelte component handle click-outside detection
						// This will be handled by the parent component
					}

					// No selection menu to close

					// Reset input focus state if clicking outside menus
					if (!isHoverMenuShowing) {
						isInputFocused = false;
					}

					return false;
				},

				handleKeyDown() {
					// If input in menu is focused, don't let ProseMirror handle keyboard events
					if (isInputFocused) {
						return true; // This tells ProseMirror we handled the event
					}
					return false;
				},

				handleDOMEvents: {
					mouseup: () => {
						// Selection-based popup is now handled by BubbleMenu UI
						return false;
					},
					mousemove: (view, event) => {
						// Menu hover state is now managed by the Svelte component
						// We only need to handle editor mouseover detection here

						// No selection menu state any more

						// Only show hover menu if SHIFT key is pressed; however, do not hide if the user is interacting with the menu
						if (!event.shiftKey && !(isHoverMenuShowing && isInputFocused)) {
							if (isHoverMenuShowing && options.hidePiiHoverMenu) {
								options.hidePiiHoverMenu();
								isHoverMenuShowing = false;
							}
							if (hoverTimeout) {
								clearTimeout(hoverTimeout);
								hoverTimeout = null;
							}
							return;
						}

						// Clear existing timeout
						if (hoverTimeout) {
							clearTimeout(hoverTimeout);
						}

						// Set new timeout for hover
						hoverTimeout = window.setTimeout(() => {
							// Use DOM-based entity detection instead of position-based
							const existingEntity = findExistingEntityAtPosition(
								view,
								event.clientX,
								event.clientY,
								config
							);

							if (!existingEntity) {
								// Hide menu if no entity found
								if (isHoverMenuShowing && options.hidePiiHoverMenu) {
									options.hidePiiHoverMenu();
									isHoverMenuShowing = false;
								}
								return;
							}

							// We found an existing PII or modifier entity
							const targetInfo = {
								word: existingEntity.text,
								from: existingEntity.from,
								to: existingEntity.to
							};
							const isPiiHighlighted = existingEntity.type === 'pii';

							// Get current conversation ID from plugin state (not options)
							const pluginState = piiModifierExtensionKey.getState(view.state);
							const currentConversationId = pluginState?.currentConversationId;

							// Find existing modifiers for this entity using getModifiersForDisplay consistently
							const piiSessionManager = PiiSessionManager.getInstance();

							// Ensure conversation state is loaded if we have a conversationId
							if (currentConversationId) {
								piiSessionManager.loadConversationState(currentConversationId);
							}

							const sessionModifiers =
								piiSessionManager.getModifiersForDisplay(currentConversationId);

							const targetText = targetInfo.word;

							// Check if the hovered entity is part of any modifier entity
							let existingModifiers =
								sessionModifiers.filter((modifier) => {
									// Check if modifier's entity text matches the target text (case-insensitive)
									return modifier.entity.toLowerCase() === targetText.toLowerCase();
								}) || [];

							// If no exact match, check if the hovered text is part of any multi-word modifier
							if (existingModifiers.length === 0) {
								for (const modifier of sessionModifiers || []) {
									const modifierWords = modifier.entity.toLowerCase().split(/\s+/);
									if (modifierWords.includes(targetText.toLowerCase())) {
										existingModifiers = [modifier];
										// Use the complete modifier entity text
										targetInfo.word = modifier.entity;
										break;
									}
								}
							}

							// Use the final target text
							const finalTargetText = targetInfo.word;

							// We already found an existing entity (PII or modifier), so show the menu

							// Show hover menu - first hide existing one
							if (isHoverMenuShowing && options.hidePiiHoverMenu) {
								options.hidePiiHoverMenu();
								isHoverMenuShowing = false;
							}

							// Create timeout manager
							const timeoutManager = {
								clearAll: () => {
									if (hoverTimeout) {
										clearTimeout(hoverTimeout);
										hoverTimeout = null;
									}
									if (menuCloseTimeout) {
										clearTimeout(menuCloseTimeout);
										menuCloseTimeout = null;
									}
								},
								setFallback: (callback: () => void, delay: number) => {
									if (menuCloseTimeout) {
										clearTimeout(menuCloseTimeout);
									}
									menuCloseTimeout = setTimeout(callback, delay);
								},
								setInputFocused: (focused: boolean) => {
									isInputFocused = focused;
								}
							};

							const onIgnore = () => {
								// Use transaction method with special meta to indicate this is from existing PII
								// This will be handled in the ADD_MODIFIER case to prevent tokenization
								const tr = view.state.tr.setMeta(piiModifierExtensionKey, {
									type: 'ADD_MODIFIER',
									modifierAction: 'ignore' as ModifierAction,
									entity: finalTargetText,
									from: targetInfo.from,
									to: targetInfo.to,
									isExistingPii: isPiiHighlighted // Add flag to prevent tokenization
								});
								view.dispatch(tr);

								if (isHoverMenuShowing && options.hidePiiHoverMenu) {
									options.hidePiiHoverMenu();
									isHoverMenuShowing = false;
								}
								timeoutManager.clearAll();
							};

							const onMask = (piiType: string) => {
								// Use transaction method with special meta to indicate this is from existing PII
								// This will be handled in the ADD_MODIFIER case to prevent tokenization
								const tr = view.state.tr.setMeta(piiModifierExtensionKey, {
									type: 'ADD_MODIFIER',
									modifierAction: 'string-mask' as ModifierAction,
									entity: finalTargetText,
									piiType,
									from: targetInfo.from,
									to: targetInfo.to,
									isExistingPii: isPiiHighlighted // Add flag to prevent tokenization
								});
								view.dispatch(tr);

								if (isHoverMenuShowing && options.hidePiiHoverMenu) {
									options.hidePiiHoverMenu();
									isHoverMenuShowing = false;
								}
								timeoutManager.clearAll();
							};

							const onRemoveModifier = (modifierId: string) => {
								// Find the modifier to get its entity text for hiding
								const modifierToRemove = sessionModifiers.find((m) => m.id === modifierId);

								let tr = view.state.tr.setMeta(piiModifierExtensionKey, {
									type: 'REMOVE_MODIFIER',
									modifierId
								});

								// If this was a mask modifier, also temporarily hide the PII entity
								if (modifierToRemove && modifierToRemove.action === 'string-mask') {
									console.log(
										'PiiModifierExtension: Hover menu removing modifier and hiding entity:',
										modifierToRemove.entity
									);
									tr = tr.setMeta(piiDetectionPluginKey, {
										type: 'TEMPORARILY_HIDE_ENTITY',
										entityText: modifierToRemove.entity
									});
								}

								view.dispatch(tr);

								if (isHoverMenuShowing && options.hidePiiHoverMenu) {
									options.hidePiiHoverMenu();
									isHoverMenuShowing = false;
								}
								timeoutManager.clearAll();
							};

							// Use Svelte component interface
							if (options.showPiiHoverMenu) {
								// ALWAYS use mouse coordinates for positioning - they're the most reliable
								const menuX = event.clientX;
								const menuY = event.clientY;

								// debug logs removed
								const labelFromModifier =
									existingModifiers.find((m) => m.action === 'string-mask')?.type || '';
								const elAtPoint = document.elementFromPoint(menuX, menuY) as HTMLElement | null;
								const labelFromDom = (elAtPoint?.getAttribute('data-pii-type') || '').toUpperCase();
								const computedCurrentLabel = (
									labelFromModifier ||
									labelFromDom ||
									'CUSTOM'
								).toUpperCase();
								const menuData: PiiHoverMenuData = {
									wordInfo: {
										word: finalTargetText,
										from: targetInfo.from,
										to: targetInfo.to,
										x: menuX,
										y: menuY
									},
									showIgnoreButton: isPiiHighlighted,
									existingModifiers,
									showTextField:
										existingModifiers.length === 0 ||
										existingModifiers.some((m) => m.action === 'string-mask'),
									currentLabel: computedCurrentLabel,
									onIgnore,
									onMask,
									onRemoveModifier,
									onInputFocused: (focused: boolean) => {
										isInputFocused = focused;
										if (focused) {
											timeoutManager.clearAll();
										}
									},
									onClose: () => {
										if (isHoverMenuShowing && options.hidePiiHoverMenu) {
											options.hidePiiHoverMenu();
											isHoverMenuShowing = false;
										}
									},
									onMouseEnter: () => {
										timeoutManager.clearAll();
									},
									onMouseLeave: () => {
										timeoutManager.setFallback(() => {
											if (isHoverMenuShowing && !isInputFocused && options.hidePiiHoverMenu) {
												options.hidePiiHoverMenu();
												isHoverMenuShowing = false;
											}
										}, config.timing.menuCloseTimeoutMs);
									}
								};

								options.showPiiHoverMenu(menuData);
								isHoverMenuShowing = true;
							}

							// Set a fallback timeout to close menu after inactivity
							timeoutManager.setFallback(() => {
								if (isHoverMenuShowing && options.hidePiiHoverMenu) {
									options.hidePiiHoverMenu();
									isHoverMenuShowing = false;
								}
							}, config.timing.menuFallbackTimeoutMs);
						}, config.timing.hoverTimeoutMs);
					},

					// Note: selection menu creation is disabled; BubbleMenu handles selection actions now

					mouseleave: () => {
						// Clear timeout when leaving editor, but keep menus if they exist
						if (hoverTimeout) {
							clearTimeout(hoverTimeout);
						}
					}
				}
			},

			view() {
				return {
					destroy: () => {
						if (isHoverMenuShowing && options.hidePiiHoverMenu) {
							options.hidePiiHoverMenu();
							isHoverMenuShowing = false;
						}
						if (hoverTimeout) {
							clearTimeout(hoverTimeout);
							hoverTimeout = null;
						}
						if (menuCloseTimeout) {
							clearTimeout(menuCloseTimeout);
							menuCloseTimeout = null;
						}
					}
				};
			}
		});

		return [plugin];
	},

	addCommands() {
		return {
			// Get current modifiers
			getModifiers:
				() =>
				({ state }: CommandContext) => {
					const pluginState = piiModifierExtensionKey.getState(state);
					return pluginState?.modifiers || [];
				},

			// Reload modifiers for a conversation (called when conversation changes)
			reloadConversationModifiers:
				(conversationId: string) =>
				({ state, dispatch }: CommandContext) => {
					const tr = state.tr.setMeta(piiModifierExtensionKey, {
						type: 'RELOAD_CONVERSATION_MODIFIERS',
						conversationId
					});

					if (dispatch) {
						dispatch(tr);
					}

					return true;
				},

			// Clear all modifiers
			clearModifiers:
				() =>
				({ state, dispatch }: CommandContext) => {
					const pluginState = piiModifierExtensionKey.getState(state);
					if (!pluginState?.modifiers.length) {
						return false;
					}

					const tr = state.tr.setMeta(piiModifierExtensionKey, {
						type: 'CLEAR_MODIFIERS'
					});

					if (dispatch) {
						dispatch(tr);

						// Trigger fast mask-update API call after modifiers are cleared
						const fastUpdateTr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'TRIGGER_FAST_MASK_UPDATE'
						});
						dispatch(fastUpdateTr);
					}

					return true;
				},

			// NEW: Add string-mask modifier for complete words in selection
			addWordMaskModifier:
				() =>
				({ state, dispatch }: CommandContext) => {
					const { from, to } = state.selection;
					if (from === to) return false; // No selection

					// Use robust tokenization with broader context (inspired by old findTokenizedWords)
					const completeWordsText = findCompleteWordsRobust(state.doc, from, to);
					if (!completeWordsText.trim()) {
						console.log('PiiModifierExtension: No complete words found in selection');
						return false; // No complete words found
					}

					console.log('PiiModifierExtension: Found complete words:', completeWordsText);

					const tr = state.tr.setMeta(piiModifierExtensionKey, {
						type: 'ADD_MODIFIER',
						modifierAction: 'string-mask' as ModifierAction,
						entity: completeWordsText,
						piiType: 'CUSTOM',
						from,
						to
					});

					if (dispatch) {
						dispatch(tr);

						// Trigger fast mask-update API call after modifier is added
						const fastUpdateTr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'TRIGGER_FAST_MASK_UPDATE'
						});
						dispatch(fastUpdateTr);
					}

					return true;
				},

			// Add a modifier programmatically
			addModifier:
				(options: {
					action: ModifierAction;
					entity: string;
					type?: string;
					from: number;
					to: number;
					isExistingPii?: boolean; // New flag to indicate this is from an existing PII highlight
				}) =>
				({ state, dispatch }: CommandContext) => {
					const doc = state.doc as ProseMirrorNode;
					const selFrom = state.selection.from;
					const selTo = state.selection.to;

					// Start with provided options
					let useFrom = typeof options.from === 'number' ? options.from : selFrom;
					let useTo = typeof options.to === 'number' ? options.to : selTo;
					if (useFrom > useTo) [useFrom, useTo] = [useTo, useFrom];

					// Derive canonical entity from current selection if necessary
					let entity = (options.entity || '').normalize('NFKC').trim();

					// If this is from an existing PII highlight, trust the entity text and don't tokenize
					if (options.isExistingPii && entity) {
						// Use the entity text and positions as provided - no tokenization needed
						// This prevents "und" being selected from "wachsenden Entwickler- und Projektteams"
					} else {
						// Original tokenization logic for new text selections
						const selText = doc.textBetween(selFrom, selTo, '\n', '\0').normalize('NFKC');
						if (!entity || (selText && selText.indexOf(entity) === -1)) {
							// Try to pick a token from selection
							const slice = selText || '';
							const tokenConfig = getPiiConfig();
							const tokens: Array<{ start: number; end: number; text: string; hasAlpha: boolean }> =
								[];
							const re = tokenConfig.patterns.tokenizationFallback;
							let m: RegExpExecArray | null;
							re.lastIndex = 0;
							while ((m = re.exec(slice)) !== null) {
								const t = m[0];
								tokens.push({
									start: m.index,
									end: m.index + t.length,
									text: t,
									hasAlpha: /[A-Za-zÀ-ÿ]/.test(t)
								});
							}
							if (tokens.length > 0) {
								const alphaTokens = tokens.filter((t) => t.hasAlpha);
								const pick =
									alphaTokens.length > 0
										? alphaTokens[alphaTokens.length - 1]
										: tokens[tokens.length - 1];
								entity = pick.text;
								useFrom = selFrom + pick.start;
								useTo = selFrom + pick.end;
							} else if (slice.trim()) {
								entity = slice.replace(/\s+/g, ' ').trim();
								useFrom = selFrom;
								useTo = selTo;
							}
						}
					}

					const tr = state.tr.setMeta(piiModifierExtensionKey, {
						type: 'ADD_MODIFIER',
						modifierAction: options.action,
						entity,
						piiType: options.type,
						from: useFrom,
						to: useTo
					});

					if (dispatch) {
						dispatch(tr);

						// Trigger fast mask-update API call after modifier is added
						const fastUpdateTr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'TRIGGER_FAST_MASK_UPDATE'
						});
						dispatch(fastUpdateTr);
					}

					return true;
				},

			// DEPRECATED: Use addWordMaskModifier instead - this creates multiple modifiers
			addTokenizedMask:
				() =>
				({ state, dispatch }: CommandContext) => {
					const { from, to } = state.selection;
					if (from === to) return false; // No selection

					// Get all tokenized words touched by the selection
					const tokenizedWords = findTokenizedWords(state.doc, from, to);

					if (tokenizedWords.length === 0) return false;

					// Create a transaction that adds modifiers for all tokenized words
					let tr = state.tr;

					tokenizedWords.forEach((word) => {
						tr = tr.setMeta(piiModifierExtensionKey, {
							type: 'ADD_MODIFIER',
							modifierAction: 'string-mask',
							entity: word.word,
							piiType: 'CUSTOM',
							from: word.from,
							to: word.to
						});
					});

					if (dispatch) {
						dispatch(tr);
					}

					return true;
				},

			// Remove a modifier by ID
			removeModifier:
				(modifierId: string) =>
				({ state, dispatch }: CommandContext) => {
					// Find the modifier to get its entity text for hiding
					const pluginState = piiModifierExtensionKey.getState(state);
					const modifierToRemove = pluginState?.modifiers.find((m) => m.id === modifierId);

					console.log(
						'PiiModifierExtension: removeModifier command called for:',
						modifierId,
						modifierToRemove?.entity
					);

					let tr = state.tr.setMeta(piiModifierExtensionKey, {
						type: 'REMOVE_MODIFIER',
						modifierId
					});

					// If this was a mask modifier, also temporarily hide the PII entity
					if (modifierToRemove && modifierToRemove.action === 'string-mask') {
						console.log('PiiModifierExtension: Also hiding PII entity:', modifierToRemove.entity);
						tr = tr.setMeta(piiDetectionPluginKey, {
							type: 'TEMPORARILY_HIDE_ENTITY',
							entityText: modifierToRemove.entity
						});
					}

					if (dispatch) {
						dispatch(tr);

						// Trigger fast mask-update API call after modifier is removed
						const fastUpdateTr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'TRIGGER_FAST_MASK_UPDATE'
						});
						dispatch(fastUpdateTr);
					}

					return true;
				},

			// Export modifiers in Shield API format
			exportModifiersForApi:
				() =>
				({ state }: CommandContext) => {
					const pluginState = piiModifierExtensionKey.getState(state);
					if (!pluginState?.modifiers.length) {
						return [];
					}

					return pluginState.modifiers.map((modifier) => ({
						action: modifier.action,
						entity: modifier.entity,
						...(modifier.type && { type: modifier.type })
					}));
				},

			// Get modifiers for a specific entity text
			getModifiersForEntity:
				(entityText: string) =>
				({ state }: CommandContext) => {
					const pluginState = piiModifierExtensionKey.getState(state);
					if (!pluginState?.modifiers.length) {
						return [];
					}

					return pluginState.modifiers.filter(
						(modifier) => modifier.entity.toLowerCase() === entityText.toLowerCase()
					);
				},

			// Clear only mask modifiers (keep ignore modifiers)
			clearMaskModifiers:
				() =>
				({ state, dispatch }: CommandContext) => {
					const pluginState = piiModifierExtensionKey.getState(state);
					const maskModifiers =
						pluginState?.modifiers.filter((m) => m.action === 'string-mask') || [];

					if (maskModifiers.length === 0) {
						return false; // No mask modifiers to clear
					}

					console.log(
						'PiiModifierExtension: clearMaskModifiers clearing:',
						maskModifiers.map((m) => m.entity)
					);

					// For clearing multiple modifiers, we need to send separate transactions
					// because ProseMirror transactions are immutable and we can't batch multiple REMOVE_MODIFIER actions
					maskModifiers.forEach((modifier) => {
						const tr = state.tr
							.setMeta(piiModifierExtensionKey, {
								type: 'REMOVE_MODIFIER',
								modifierId: modifier.id
							})
							.setMeta(piiDetectionPluginKey, {
								type: 'TEMPORARILY_HIDE_ENTITY',
								entityText: modifier.entity
							});

						if (dispatch) {
							dispatch(tr);
						}
					});

					// Trigger fast mask-update API call after all mask modifiers are cleared
					if (dispatch) {
						const fastUpdateTr = state.tr.setMeta(piiDetectionPluginKey, {
							type: 'TRIGGER_FAST_MASK_UPDATE'
						});
						dispatch(fastUpdateTr);
					}

					return true;
				}
		} as any;
	}
});

// Utility function to add CSS styles for modifier system
export function addPiiModifierStyles(config?: PiiExtensionConfig) {
	const piiConfig = config || getPiiConfig();
	const styleId = piiConfig.styling.styleElementId;

	// Check if styles already exist
	if (document.getElementById(styleId)) {
		return;
	}

	const styleElement = document.createElement('style');
	styleElement.id = styleId;
	styleElement.textContent = `
		/* Modifier highlighting - takes precedence over PII detection */
		.pii-modifier-highlight {
			position: relative;
			border-radius: ${piiConfig.styling.borderRadius};
			padding: ${piiConfig.styling.highlightPadding};
			cursor: pointer;
			transition: all ${piiConfig.styling.transitionDuration} ease;
			z-index: ${piiConfig.styling.zIndex.modifierHighlight}; /* Higher than PII highlights */
		}

		.pii-modifier-highlight:hover {
			box-shadow: ${piiConfig.styling.boxShadow.hover};
		}

		/* Mask modifier styling - orange text with green background/border */
		.pii-modifier-highlight.pii-modifier-mask {
			color: ${piiConfig.styling.modifierColors.textColor} !important;
			background-color: ${piiConfig.styling.modifierColors.maskBackgroundColor} !important;
			border-bottom: 1px dashed ${piiConfig.styling.modifierColors.maskBorderColor} !important;
		}

		.pii-modifier-highlight.pii-modifier-mask:hover {
			color: ${piiConfig.styling.modifierColors.textHoverColor} !important;
			background-color: ${piiConfig.styling.modifierColors.maskBackgroundHoverColor} !important;
			border-bottom: 2px dashed ${piiConfig.styling.modifierColors.maskBorderColor} !important;
		}

		/* Ignore modifier styling - orange text, no background */
		.pii-modifier-highlight.pii-modifier-ignore {
			color: ${piiConfig.styling.modifierColors.textColor} !important;
			text-decoration: line-through !important;
			opacity: ${piiConfig.styling.modifierColors.ignoreOpacity} !important;
		}

		.pii-modifier-highlight.pii-modifier-ignore:hover {
			color: ${piiConfig.styling.modifierColors.textHoverColor} !important;
			opacity: ${piiConfig.styling.modifierColors.ignoreHoverOpacity} !important;
		}

		/* Ensure modifier styles take precedence over PII styles */
		.pii-highlight.pii-modifier-highlight {
			color: ${piiConfig.styling.modifierColors.textColor} !important;
		}

		.pii-highlight.pii-modifier-highlight.pii-modifier-mask {
			color: ${piiConfig.styling.modifierColors.textColor} !important;
			background-color: ${piiConfig.styling.modifierColors.maskBackgroundColor} !important;
			border-bottom: 1px dashed ${piiConfig.styling.modifierColors.maskBorderColor} !important;
		}

		.pii-highlight.pii-modifier-highlight.pii-modifier-ignore {
			color: ${piiConfig.styling.modifierColors.textColor} !important;
			background-color: transparent !important;
			border-bottom: none !important;
			text-decoration: line-through !important;
			opacity: ${piiConfig.styling.modifierColors.ignoreOpacity} !important;
		}
	`;

	document.head.appendChild(styleElement);
}
