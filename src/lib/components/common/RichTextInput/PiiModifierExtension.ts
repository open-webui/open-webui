import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import type { Node as ProseMirrorNode } from 'prosemirror-model';

// Types for the Shield API modifiers
export type ModifierType = 'ignore' | 'mask';

export interface PiiModifier {
	type: ModifierType;
	entity: string;
	label?: string; // Required for 'mask' type
	id: string; // Unique identifier for this modifier
	from: number; // ProseMirror position start
	to: number; // ProseMirror position end
}

// Options for the extension
export interface PiiModifierOptions {
	enabled: boolean;
	onModifiersChanged?: (modifiers: PiiModifier[]) => void;
	availableLabels?: string[]; // List of available PII labels for mask type
}

// Extension state
interface PiiModifierState {
	modifiers: PiiModifier[];
	hoveredWordInfo: {
		word: string;
		from: number;
		to: number;
		x: number;
		y: number;
	} | null;
}

const piiModifierExtensionKey = new PluginKey<PiiModifierState>('piiModifier');

// Generate unique ID for modifiers
function generateModifierId(): string {
	return `modifier_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Find word boundaries at a given position
function findWordAt(doc: ProseMirrorNode, pos: number): { from: number; to: number; text: string } | null {
	let from = pos;
	let to = pos;
	let text = '';

	// Find word boundaries by traversing text nodes
	doc.nodesBetween(0, doc.content.size, (node, nodePos) => {
		if (node.isText && node.text) {
			const nodeStart = nodePos;
			const nodeEnd = nodePos + node.text.length;

			if (pos >= nodeStart && pos <= nodeEnd) {
				const relativePos = pos - nodeStart;
				const nodeText = node.text;

				// Find word start
				let wordStart = relativePos;
				while (wordStart > 0 && /\w/.test(nodeText[wordStart - 1])) {
					wordStart--;
				}

				// Find word end
				let wordEnd = relativePos;
				while (wordEnd < nodeText.length && /\w/.test(nodeText[wordEnd])) {
					wordEnd++;
				}

				// Only proceed if we're actually within a word
				if (wordStart < wordEnd && relativePos >= wordStart && relativePos <= wordEnd) {
					from = nodeStart + wordStart;
					to = nodeStart + wordEnd;
					text = nodeText.substring(wordStart, wordEnd);
				}
				return false; // Stop searching
			}
		}
	});

	if (text && text.length > 2) {
		return { from, to, text };
	}
	return null;
}



// Create hover menu element
function createHoverMenu(
	wordInfo: { word: string; from: number; to: number; x: number; y: number },
	onIgnore: () => void,
	onMask: (label: string) => void,
	showIgnoreButton: boolean = false
): HTMLElement {
	const menu = document.createElement('div');
	menu.className = 'pii-modifier-hover-menu';
	menu.style.cssText = `
		position: fixed;
		left: ${Math.min(wordInfo.x, window.innerWidth - 250)}px;
		top: ${wordInfo.y - 80}px;
		background: white;
		border: 1px solid #ddd;
		border-radius: 8px;
		box-shadow: 0 4px 20px rgba(0,0,0,0.15);
		padding: 12px;
		z-index: 1000;
		font-family: system-ui, -apple-system, sans-serif;
		font-size: 13px;
		min-width: 220px;
		max-width: 300px;
	`;

	// Header
	const header = document.createElement('div');
	header.style.cssText = `
		font-weight: 600;
		color: #333;
		margin-bottom: 8px;
		font-size: 12px;
	`;
	header.textContent = `"${wordInfo.word}"`;
	menu.appendChild(header);

	// Ignore button (only show if word is detected as PII)
	if (showIgnoreButton) {
		const ignoreBtn = document.createElement('button');
		ignoreBtn.textContent = '🚫 Ignore this PII';
		ignoreBtn.style.cssText = `
			width: 100%;
			padding: 6px 10px;
			margin-bottom: 8px;
			border: 1px solid #ff6b6b;
			background: #fff5f5;
			border-radius: 4px;
			cursor: pointer;
			font-size: 12px;
			color: #c53030;
		`;
		ignoreBtn.addEventListener('click', onIgnore);
		menu.appendChild(ignoreBtn);
	}

	// Label input section
	const labelSection = document.createElement('div');
	labelSection.style.cssText = `
		display: flex;
		flex-direction: column;
		gap: 6px;
	`;

	const labelInput = document.createElement('input');
	labelInput.type = 'text';
	labelInput.placeholder = 'Enter custom label (e.g., CASENUMBER)';
	labelInput.style.cssText = `
		width: 100%;
		padding: 6px 8px;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 12px;
		box-sizing: border-box;
	`;

	const maskBtn = document.createElement('button');
	maskBtn.textContent = '🎭 Mark as PII';
	maskBtn.style.cssText = `
		width: 100%;
		padding: 6px 10px;
		border: 1px solid #4ecdc4;
		background: #f0fdfa;
		border-radius: 4px;
		cursor: pointer;
		font-size: 12px;
		color: #0d9488;
		font-weight: 500;
	`;

	// Handle mask button click
	maskBtn.addEventListener('click', () => {
		const label = labelInput.value.trim().toUpperCase();
		if (label) {
			onMask(label);
		} else {
			// Highlight input if empty
			labelInput.style.borderColor = '#ff6b6b';
			labelInput.focus();
			setTimeout(() => {
				labelInput.style.borderColor = '#ddd';
			}, 1000);
		}
	});

	// Handle Enter key in input
	labelInput.addEventListener('keydown', (e) => {
		if (e.key === 'Enter') {
			const label = labelInput.value.trim().toUpperCase();
			if (label) {
				onMask(label);
			}
		}
	});

	labelSection.appendChild(labelInput);
	labelSection.appendChild(maskBtn);
	menu.appendChild(labelSection);

	// Auto-focus input
	setTimeout(() => labelInput.focus(), 100);

	// Add hover protection to keep menu open
	menu.addEventListener('mouseenter', () => {
		// Cancel any pending hide timeout when hovering over menu
		console.log('PiiModifierExtension: Mouse entered menu, keeping it open');
	});

	menu.addEventListener('mouseleave', () => {
		// Hide menu when mouse leaves it
		setTimeout(() => {
			menu.remove();
		}, 200); // Small delay to allow moving back to menu
	});

	return menu;
}

export const PiiModifierExtension = Extension.create<PiiModifierOptions>({
	name: 'piiModifier',

	addOptions() {
		return {
			enabled: false,
			onModifiersChanged: undefined,
			availableLabels: [
				'PERSON', 'EMAIL', 'PHONE_NUMBER', 'ADDRESS', 'SSN', 
				'CREDIT_CARD', 'DATE_TIME', 'IP_ADDRESS', 'URL', 'IBAN',
				'MEDICAL_LICENSE', 'US_PASSPORT', 'US_DRIVER_LICENSE'
			]
		};
	},

	onCreate() {
		console.log('PiiModifierExtension: Extension created successfully');
	},

	addProseMirrorPlugins() {
		const options = this.options;
		const { enabled, onModifiersChanged, availableLabels } = options;

		console.log('PiiModifierExtension: Adding ProseMirror plugins', {
			enabled,
			hasCallback: !!onModifiersChanged,
			labelsCount: availableLabels?.length || 0
		});

		if (!enabled) {
			console.log('PiiModifierExtension: Disabled - not adding plugins');
			return [];
		}

		let hoverMenuElement: HTMLElement | null = null;
		let hoverTimeout: number | null = null;

		const plugin = new Plugin<PiiModifierState>({
			key: piiModifierExtensionKey,

			state: {
				init(): PiiModifierState {
					console.log('PiiModifierExtension: Initializing extension state');
					return {
						modifiers: [],
						hoveredWordInfo: null
					};
				},

				apply(tr, prevState): PiiModifierState {
					let newState = { ...prevState };

					// Handle document changes - update positions
					if (tr.docChanged) {
						const updatedModifiers = prevState.modifiers.map(modifier => ({
							...modifier,
							from: tr.mapping.map(modifier.from),
							to: tr.mapping.map(modifier.to)
						})).filter(modifier => 
							// Remove modifiers that are no longer valid
							modifier.from < modifier.to && 
							modifier.from >= 0 && 
							modifier.to <= tr.doc.content.size
						);

						newState = {
							...newState,
							modifiers: updatedModifiers
						};

						// Notify of changes if modifiers were removed
						if (updatedModifiers.length !== prevState.modifiers.length && onModifiersChanged) {
							onModifiersChanged(updatedModifiers);
						}
					}

					// Handle plugin-specific meta actions
					const meta = tr.getMeta(piiModifierExtensionKey);
					if (meta) {
						console.log('PiiModifierExtension: Handling meta action:', meta.type);
						switch (meta.type) {
							case 'ADD_MODIFIER':
								const newModifier: PiiModifier = {
									id: generateModifierId(),
									type: meta.modifierType,
									entity: meta.entity,
									label: meta.label,
									from: meta.from,
									to: meta.to
								};

								const updatedModifiers = [...newState.modifiers, newModifier];
								newState = {
									...newState,
									modifiers: updatedModifiers
								};

								if (onModifiersChanged) {
									onModifiersChanged(updatedModifiers);
								}
								break;

							case 'REMOVE_MODIFIER':
								const filteredModifiers = newState.modifiers.filter(m => m.id !== meta.modifierId);
								newState = {
									...newState,
									modifiers: filteredModifiers
								};

								if (onModifiersChanged) {
									onModifiersChanged(filteredModifiers);
								}
								break;
						}
					}

					return newState;
				}
			},

			props: {
				handleClick(view, pos, event) {
					// Hide hover menu on click
					if (hoverMenuElement) {
						hoverMenuElement.remove();
						hoverMenuElement = null;
					}

					return false;
				},

				handleDOMEvents: {
					mousemove: (view, event) => {
						// Don't show menu if hovering over existing menu
						if (hoverMenuElement && hoverMenuElement.contains(event.target as Node)) {
							return;
						}

						// Clear existing timeout
						if (hoverTimeout) {
							clearTimeout(hoverTimeout);
						}

						// Set new timeout for hover
						hoverTimeout = window.setTimeout(() => {
							const pos = view.posAtCoords({ left: event.clientX, top: event.clientY });
							if (!pos) return;

							const wordInfo = findWordAt(view.state.doc, pos.pos);
							if (!wordInfo) {
								// Hide menu if no word found
								if (hoverMenuElement) {
									hoverMenuElement.remove();
									hoverMenuElement = null;
								}
								return;
							}

							// Note: Allow multiple modifiers for the same word since we don't show visual indicators

							// Check if word is currently highlighted as PII (by PII detection)
							const isPiiHighlighted = document.querySelector(`[data-pii-text="${wordInfo.text}"]`) !== null;

							// Show hover menu
							if (hoverMenuElement) {
								hoverMenuElement.remove();
							}

							const onIgnore = () => {
								const tr = view.state.tr.setMeta(piiModifierExtensionKey, {
									type: 'ADD_MODIFIER',
									modifierType: 'ignore' as ModifierType,
									entity: wordInfo.text,
									from: wordInfo.from,
									to: wordInfo.to
								});
								view.dispatch(tr);

								if (hoverMenuElement) {
									hoverMenuElement.remove();
									hoverMenuElement = null;
								}
							};

							const onMask = (label: string) => {
								const tr = view.state.tr.setMeta(piiModifierExtensionKey, {
									type: 'ADD_MODIFIER',
									modifierType: 'mask' as ModifierType,
									entity: wordInfo.text,
									label,
									from: wordInfo.from,
									to: wordInfo.to
								});
								view.dispatch(tr);

								if (hoverMenuElement) {
									hoverMenuElement.remove();
									hoverMenuElement = null;
								}
							};

							hoverMenuElement = createHoverMenu(
								{
									word: wordInfo.text,
									from: wordInfo.from,
									to: wordInfo.to,
									x: event.clientX,
									y: event.clientY
								},
								onIgnore,
								onMask,
								isPiiHighlighted // Show ignore button only if already detected as PII
							);

							document.body.appendChild(hoverMenuElement);

							// Keep menu open longer for interaction (10 seconds)
							setTimeout(() => {
								if (hoverMenuElement) {
									hoverMenuElement.remove();
									hoverMenuElement = null;
								}
							}, 10000);

						}, 300); // Reduced hover delay to 300ms
					},

					mouseleave: () => {
						// Clear timeout when leaving editor, but keep menu if it exists
						if (hoverTimeout) {
							clearTimeout(hoverTimeout);
						}
					}
				}
			},

			view() {
				return {
					destroy: () => {
						if (hoverMenuElement) {
							hoverMenuElement.remove();
							hoverMenuElement = null;
						}
						if (hoverTimeout) {
							clearTimeout(hoverTimeout);
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
			getModifiers: () => ({ state }: any) => {
				const pluginState = piiModifierExtensionKey.getState(state);
				return pluginState?.modifiers || [];
			},

			// Clear all modifiers
			clearModifiers: () => ({ state, dispatch }: any) => {
				const pluginState = piiModifierExtensionKey.getState(state);
				if (!pluginState?.modifiers.length) {
					return false;
				}

				// Clear all modifiers
				const tr = state.tr.setMeta(piiModifierExtensionKey, {
					type: 'CLEAR_MODIFIERS'
				});

				if (dispatch) {
					dispatch(tr);
				}

				return true;
			},

			// Export modifiers in Shield API format
			exportModifiersForApi: () => ({ state }: any) => {
				const pluginState = piiModifierExtensionKey.getState(state);
				if (!pluginState?.modifiers.length) {
					return [];
				}

				return pluginState.modifiers.map(modifier => ({
					type: modifier.type,
					entity: modifier.entity,
					...(modifier.label && { label: modifier.label })
				}));
			}
		} as any;
	}
});

// Utility function to add CSS styles for the hover menu only
export function addPiiModifierStyles() {
	const styleId = 'pii-modifier-styles';
	
	// Check if styles already exist
	if (document.getElementById(styleId)) {
		return;
	}

	const styleElement = document.createElement('style');
	styleElement.id = styleId;
	styleElement.textContent = `
		.pii-modifier-hover-menu {
			animation: fadeIn 0.2s ease-in-out;
			pointer-events: auto;
		}

		@keyframes fadeIn {
			from { opacity: 0; transform: translateY(5px); }
			to { opacity: 1; transform: translateY(0); }
		}

		.pii-modifier-hover-menu button:hover {
			transform: scale(1.02);
			transition: transform 0.1s ease;
			box-shadow: 0 2px 8px rgba(0,0,0,0.1);
		}

		.pii-modifier-hover-menu input:focus {
			outline: none;
			border-color: #4ecdc4;
			box-shadow: 0 0 0 2px rgba(78, 205, 196, 0.2);
		}
	`;

	document.head.appendChild(styleElement);
}