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

// Export the plugin key so other extensions can access the state
export { piiModifierExtensionKey };

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

	if (text && text.length >= 2) {
		return { from, to, text };
	}
	return null;
}



// Predefined PII labels for autocompletion (from SPACY_LABEL_MAPPINGS values)
const PREDEFINED_LABELS = [
	'ADDRESS', 'BANK_ACCOUNT_NUMBER', 'ID_NUMBER', 'HEALTH_DATA', 'LOCATION', 
	'NUMBER', 'TAX_NUMBER', 'CREDIT_CARD', 'DATE', 'SIGNATURE', 'EMAIL', 
	'IBAN', 'HEALTH_ID', 'IPv4v6', 'PHONENUMBER', 'LICENSE_PLATE', 'CURRENCY', 
	'ORGANISATION', 'PASSPORT', 'PERSON', 'SSN'
];

// Find best matching label for inline completion
function findBestMatch(input: string, labels: string[]): string | null {
	if (!input) return null;
	
	const upperInput = input.toUpperCase();
	
	// Find exact prefix match first
	const exactMatch = labels.find(label => label.startsWith(upperInput));
	if (exactMatch) return exactMatch;
	
	// Find partial match
	const partialMatch = labels.find(label => label.includes(upperInput));
	if (partialMatch) return partialMatch;
	
	return null;
}

// Create hover menu element
function createHoverMenu(
	wordInfo: { word: string; from: number; to: number; x: number; y: number },
	onIgnore: () => void,
	onMask: (label: string) => void,
	showIgnoreButton: boolean = false,
	existingModifiers: PiiModifier[] = [],
	onRemoveModifier?: (modifierId: string) => void,
	timeoutManager?: { clearAll: () => void; setFallback: (callback: () => void, delay: number) => void },
	showTextField: boolean = true
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

	// Header with icon
	const header = document.createElement('div');
	header.style.cssText = `
		display: flex;
		align-items: center;
		gap: 8px;
		font-weight: 600;
		color: #333;
		margin-bottom: 8px;
		font-size: 12px;
	`;
	
	// Add NENNA icon
	const icon = document.createElement('img');
	icon.src = '/static/icon-purple-32.png';
	icon.style.cssText = `
		width: 16px;
		height: 16px;
		flex-shrink: 0;
	`;
	
	const textNode = document.createElement('span');
	textNode.textContent = `"${wordInfo.word}"`;
	
	header.appendChild(icon);
	header.appendChild(textNode);
	menu.appendChild(header);

	// Show existing modifiers if any
	if (existingModifiers.length > 0) {
		const modifiersSection = document.createElement('div');
		modifiersSection.style.cssText = `
			margin-bottom: 12px;
			padding: 8px;
			background: #f8f9fa;
			border-radius: 4px;
			border: 1px solid #e9ecef;
		`;

		const modifiersHeader = document.createElement('div');
		modifiersHeader.textContent = 'Current Modifiers:';
		modifiersHeader.style.cssText = `
			font-weight: 600;
			font-size: 11px;
			color: #495057;
			margin-bottom: 6px;
		`;
		modifiersSection.appendChild(modifiersHeader);

		existingModifiers.forEach((modifier) => {
			const modifierItem = document.createElement('div');
			modifierItem.style.cssText = `
				display: flex;
				justify-content: space-between;
				align-items: center;
				padding: 4px 6px;
				margin-bottom: 4px;
				background: white;
				border-radius: 3px;
				border: 1px solid #dee2e6;
				font-size: 11px;
			`;

			const modifierInfo = document.createElement('span');
			const typeIcon = modifier.type === 'ignore' ? '🚫' : '🏷️';
			const typeText = modifier.type === 'ignore' ? 'Ignore' : `Mask as ${modifier.label}`;
			modifierInfo.textContent = `${typeIcon} ${typeText}`;
			modifierInfo.style.cssText = `
				color: #495057;
				flex: 1;
			`;

			const removeBtn = document.createElement('button');
			removeBtn.textContent = '✕';
			removeBtn.title = 'Remove modifier';
			removeBtn.style.cssText = `
				background: #dc3545;
				color: white;
				border: none;
				border-radius: 2px;
				width: 18px;
				height: 18px;
				cursor: pointer;
				font-size: 10px;
				display: flex;
				align-items: center;
				justify-content: center;
				flex-shrink: 0;
				margin-left: 6px;
			`;

			removeBtn.addEventListener('click', (e) => {
				e.preventDefault();
				e.stopPropagation();
				if (onRemoveModifier) {
					onRemoveModifier(modifier.id);
				}
			});

			removeBtn.addEventListener('mouseenter', () => {
				removeBtn.style.backgroundColor = '#c82333';
			});

			removeBtn.addEventListener('mouseleave', () => {
				removeBtn.style.backgroundColor = '#dc3545';
			});

			modifierItem.appendChild(modifierInfo);
			modifierItem.appendChild(removeBtn);
			modifiersSection.appendChild(modifierItem);
		});

		menu.appendChild(modifiersSection);
	}

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
		ignoreBtn.addEventListener('click', (e) => {
			e.preventDefault();
			e.stopPropagation();
			onIgnore();
		});
		menu.appendChild(ignoreBtn);
	}

	// Label input section (only show if showTextField is true)
	if (showTextField) {
		const labelSection = document.createElement('div');
		labelSection.style.cssText = `
			display: flex;
			flex-direction: column;
			gap: 6px;
			position: relative;
		`;

	const labelInput = document.createElement('input');
	labelInput.type = 'text';
	labelInput.value = 'CUSTOM';
	labelInput.style.cssText = `
		width: 100%;
		padding: 6px 8px;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 12px;
		box-sizing: border-box;
		color: #999;
	`;

	let isDefaultValue = true;
	let skipAutocompletion = false;

	// Handle focus/click - clear default value
	const handleInputFocus = (e: Event) => {
		e.stopPropagation(); // Prevent click from bubbling up and closing menu
		console.log('PiiModifierExtension: Input field focused');
		
		// Notify timeout manager that input is focused
		if (timeoutManager) {
			(timeoutManager as any).setInputFocused(true);
		}
		
		if (isDefaultValue) {
			labelInput.value = '';
			labelInput.style.color = '#333';
			isDefaultValue = false;
		}
	};

	labelInput.addEventListener('focus', handleInputFocus);
	labelInput.addEventListener('click', handleInputFocus);

	// Handle blur - restore default if empty
	labelInput.addEventListener('blur', () => {
		
		// Notify timeout manager that input is no longer focused
		if (timeoutManager) {
			(timeoutManager as any).setInputFocused(false);
		}
		
		if (labelInput.value.trim() === '') {
			labelInput.value = 'CUSTOM';
			labelInput.style.color = '#999';
			isDefaultValue = true;
		}
	});

	// Handle input for inline autocompletion
	labelInput.addEventListener('input', (e) => {
		e.stopPropagation();
		
		// Skip autocompletion if we're handling a backspace
		if (skipAutocompletion) {
			skipAutocompletion = false;
			return;
		}
		
		const inputValue = labelInput.value;
		
		// Only autocomplete if not default value and user has typed something
		if (!isDefaultValue && inputValue) {
			const bestMatch = findBestMatch(inputValue, PREDEFINED_LABELS);
			
			if (bestMatch && bestMatch !== inputValue.toUpperCase()) {
				// Complete the text inline
				const cursorPos = labelInput.selectionStart || 0;
				labelInput.value = bestMatch;
				
				// Select the completed portion
				labelInput.setSelectionRange(cursorPos, bestMatch.length);
			}
		}
	});

	// Prevent ProseMirror from intercepting keyboard events when input is focused
	labelInput.addEventListener('keydown', (e) => {
		// Stop propagation for all keyboard events to prevent ProseMirror interference
		e.stopPropagation();
		
		// Handle specific keys
		if (e.key === 'Enter') {
			e.preventDefault();
			const label = isDefaultValue ? 'CUSTOM' : labelInput.value.trim().toUpperCase();
			if (label) {
				onMask(label);
			}
		} else if (e.key === 'Tab') {
			// Accept the current autocompletion on Tab
			e.preventDefault();
			// The text is already completed, just move cursor to end
			labelInput.setSelectionRange(labelInput.value.length, labelInput.value.length);
		} else if (e.key === 'Escape') {
			// Close menu on Escape
			e.preventDefault();
			menu.remove();
		} else if (e.key === 'Backspace') {
			// Just set flag to skip autocompletion and let browser handle backspace naturally
			skipAutocompletion = true;
			// Don't prevent default - let browser handle backspace naturally
		}
		// For all other keys, let the input handle them naturally
	});

	// Also prevent keyup events from bubbling to ProseMirror
	labelInput.addEventListener('keyup', (e) => {
		e.stopPropagation();
	});



	const maskBtn = document.createElement('button');
	maskBtn.textContent = 'Mark as PII';
	maskBtn.style.cssText = `
		width: 100%;
		padding: 6px 10px;
		border: 1px solid #6b46c1;
		background: #6b46c1;
		border-radius: 4px;
		cursor: pointer;
		font-size: 12px;
		color: white;
		font-weight: 500;
		transition: background-color 0.2s ease;
	`;

	// Add hover effects for the button
	maskBtn.addEventListener('mouseenter', () => {
		maskBtn.style.backgroundColor = '#553c9a';
	});
	
	maskBtn.addEventListener('mouseleave', () => {
		maskBtn.style.backgroundColor = '#6b46c1';
	});

	// Handle mask button click
	maskBtn.addEventListener('click', (e) => {
		e.preventDefault();
		e.stopPropagation();
		const label = isDefaultValue ? 'CUSTOM' : labelInput.value.trim().toUpperCase();
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



		labelSection.appendChild(labelInput);
		labelSection.appendChild(maskBtn);
		menu.appendChild(labelSection);
	}

	// Don't auto-focus to allow users to see the "CUSTOM" placeholder first
	// Users can click to focus when ready

	// Add hover protection to keep menu open
	menu.addEventListener('mouseenter', () => {
		// Cancel any pending hide timeout when hovering over menu
		console.log('PiiModifierExtension: Mouse entered menu, keeping it open');
		if (timeoutManager) {
			timeoutManager.clearAll();
		}
	});

	menu.addEventListener('mouseleave', (e) => {
		// Only hide menu if not moving to a child element (like the dropdown)
		const relatedTarget = e.relatedTarget as HTMLElement;
		if (relatedTarget && menu.contains(relatedTarget)) {
			return; // Don't hide if moving to a child element
		}
		
		// Hide menu when mouse leaves it with a longer delay
		if (timeoutManager) {
			timeoutManager.setFallback(() => {
				// Double-check the menu still exists and isn't being interacted with
				if (menu && document.body.contains(menu)) {
					const activeElement = document.activeElement;
					const isInputFocused = activeElement && menu.contains(activeElement);
					
					if (!isInputFocused) {
						menu.remove();
					}
				}
			}, 500);
		}
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
		let menuCloseTimeout: ReturnType<typeof setTimeout> | null = null;
		let isMouseOverMenu = false;
		let isInputFocused = false;

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

								let updatedModifiers;
								
								if (meta.modifierType === 'mask') {
									// For mask modifiers, replace any existing mask modifiers for the same entity
									updatedModifiers = newState.modifiers.filter(modifier => 
										!(modifier.type === 'mask' && modifier.entity.toLowerCase() === meta.entity.toLowerCase())
									);
									updatedModifiers.push(newModifier);
								} else {
									// For ignore modifiers, just add normally (ignore can coexist with masks)
									updatedModifiers = [...newState.modifiers, newModifier];
								}

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
					// Only hide hover menu if clicking outside of it
					if (hoverMenuElement) {
						const target = event.target as HTMLElement;
						const isClickInsideMenu = hoverMenuElement.contains(target);
						
						if (!isClickInsideMenu) {
							hoverMenuElement.remove();
							hoverMenuElement = null;
							isInputFocused = false;
						}
					}

					return false;
				},

				handleKeyDown(view, event) {
					// If input in menu is focused, don't let ProseMirror handle keyboard events
					if (isInputFocused) {
						return true; // This tells ProseMirror we handled the event
					}
					return false;
				},

				handleDOMEvents: {
					mousemove: (view, event) => {
						// Check if mouse is over existing menu
						const isOverMenu = hoverMenuElement && hoverMenuElement.contains(event.target as Node);
						
						if (isOverMenu) {
							// Update mouse over menu state
							if (!isMouseOverMenu) {
								isMouseOverMenu = true;
							}
							
							// Clear any pending timeouts to keep menu stable
							if (hoverTimeout) {
								clearTimeout(hoverTimeout);
								hoverTimeout = null;
							}
							if (menuCloseTimeout) {
								clearTimeout(menuCloseTimeout);
								menuCloseTimeout = null;
							}
							return;
						} else {
							// Mouse left menu area
							if (isMouseOverMenu) {
								isMouseOverMenu = false;
							}
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

							// Find existing modifiers for this word (check entity text match)
							const pluginState = piiModifierExtensionKey.getState(view.state);
							const existingModifiers = pluginState?.modifiers.filter(modifier => {
								// Check if modifier's entity text matches the current word (case-insensitive)
								return modifier.entity.toLowerCase() === wordInfo.text.toLowerCase();
							}) || [];

							// Check if there are any mask modifiers for this word
							const hasMaskModifier = existingModifiers.some(modifier => modifier.type === 'mask');
							// Check if there are any ignore modifiers for this word
							const hasIgnoreModifier = existingModifiers.some(modifier => modifier.type === 'ignore');

							// Show hover menu
							if (hoverMenuElement) {
								hoverMenuElement.remove();
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
								timeoutManager.clearAll();
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
								timeoutManager.clearAll();
							};

							const onRemoveModifier = (modifierId: string) => {
								const tr = view.state.tr.setMeta(piiModifierExtensionKey, {
									type: 'REMOVE_MODIFIER',
									modifierId
								});
								view.dispatch(tr);

								if (hoverMenuElement) {
									hoverMenuElement.remove();
									hoverMenuElement = null;
								}
								timeoutManager.clearAll();
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
								isPiiHighlighted && !hasMaskModifier, // Show ignore button only if detected as PII AND no mask modifier exists
								existingModifiers, // Pass existing modifiers
								onRemoveModifier, // Pass removal callback
								timeoutManager, // Pass timeout manager
								!hasIgnoreModifier // Show text field only if no ignore modifier exists
							);

							document.body.appendChild(hoverMenuElement);

							// Set a fallback timeout to close menu after 10 seconds of inactivity
							timeoutManager.setFallback(() => {
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