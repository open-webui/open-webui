import { Extension } from '@tiptap/core';
import { Plugin, PluginKey } from 'prosemirror-state';
import type { Node as ProseMirrorNode } from 'prosemirror-model';
import { PiiSessionManager } from '$lib/utils/pii';

// Types for the Shield API modifiers
export type ModifierAction = 'ignore' | 'mask';

export interface PiiModifier {
	action: ModifierAction;
	entity: string;
	type?: string; // PII type - required for 'mask' action
	id: string; // Unique identifier for this modifier
}

// Options for the extension
export interface PiiModifierOptions {
	enabled: boolean;
	conversationId?: string; // Add conversation ID for proper state management
	onModifiersChanged?: (modifiers: PiiModifier[]) => void;
	availableLabels?: string[]; // List of available PII labels for mask type
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
		tokenizedWords: Array<{ word: string; from: number; to: number; }>;
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

// Tokenizer pattern for broader context word detection
const WORD_TOKENIZER_PATTERN = /[\w'-äöüÄÖÜß]+(?=\b|\.)/g;

// Find all tokenized words touched by a text selection with broader context
function findTokenizedWords(doc: ProseMirrorNode, selectionFrom: number, selectionTo: number): Array<{ word: string; from: number; to: number; }> {
	const words: Array<{ word: string; from: number; to: number; }> = [];
	
	// Expand context to include words that might be partially selected
	const contextStart = Math.max(0, selectionFrom - 100); // 100 chars before
	const contextEnd = Math.min(doc.content.size, selectionTo + 100); // 100 chars after
	
	let contextText = '';
	
	// Build context text with position mapping
	const positionMap: number[] = []; // Maps context text index to document position
	
	doc.nodesBetween(contextStart, contextEnd, (node, nodePos) => {
		if (node.isText && node.text) {
			const nodeStart = nodePos;
			const nodeEnd = nodePos + node.text.length;
			const effectiveStart = Math.max(nodeStart, contextStart);
			const effectiveEnd = Math.min(nodeEnd, contextEnd);
			
			if (effectiveStart < effectiveEnd) {
				const startOffset = effectiveStart - nodeStart;
				const endOffset = effectiveEnd - nodeStart;
				const textSlice = node.text.substring(startOffset, endOffset);
				
				// Map each character position
				for (let i = 0; i < textSlice.length; i++) {
					positionMap.push(effectiveStart + i);
				}
				
				contextText += textSlice;
			}
		}
	});
	
	// Find all words using tokenizer
	let match;
	WORD_TOKENIZER_PATTERN.lastIndex = 0; // Reset regex
	
	while ((match = WORD_TOKENIZER_PATTERN.exec(contextText)) !== null) {
		const wordStart = match.index;
		const wordEnd = match.index + match[0].length;
		
		// Map back to document positions
		const docStart = positionMap[wordStart];
		const docEnd = positionMap[wordEnd - 1] + 1; // +1 because we want end position
		
		// Check if this word is "touched" by the selection (overlaps with selection range)
		if (docEnd > selectionFrom && docStart < selectionTo) {
			words.push({
				word: match[0],
				from: docStart,
				to: docEnd
			});
		}
	}
	
	// Remove duplicates and sort by position
	const uniqueWords = words.filter((word, index, arr) => 
		arr.findIndex(w => w.from === word.from && w.to === word.to) === index
	).sort((a, b) => a.from - b.from);
	
	return uniqueWords;
}

// Find existing PII or modifier element under mouse cursor using DOM element detection
function findExistingEntityAtPosition(view: any, clientX: number, clientY: number): { from: number; to: number; text: string; type: 'pii' | 'modifier' } | null {
	const target = document.elementFromPoint(clientX, clientY) as HTMLElement;
	if (!target) return null;

	// Check if we're hovering over a PII highlight
	const piiElement = target.closest('.pii-highlight');
	if (piiElement) {
		const piiText = piiElement.getAttribute('data-pii-text') || piiElement.textContent || '';
		const piiLabel = piiElement.getAttribute('data-pii-label') || '';
		if (piiText.length >= 2) {
			// Try to find the exact position using PII plugin state
			try {
				// We need to import the PII detection plugin key to access its state
				const piiDetectionPluginKey = new PluginKey('piiDetection');
				const piiState = piiDetectionPluginKey.getState(view.state);
				
				if (piiState?.entities) {
					// Find the entity that matches this label
					const matchingEntity = piiState.entities.find((entity: any) => entity.label === piiLabel);
					if (matchingEntity && matchingEntity.occurrences.length > 0) {
						const occurrence = matchingEntity.occurrences[0]; // Use first occurrence
						return {
							from: occurrence.start_idx,
							to: occurrence.end_idx,
							text: piiText,
							type: 'pii'
						};
					}
				}
			} catch (error) {
				console.log('PiiModifierExtension: Could not access PII state:', error);
			}
			
			// Fallback: get position from mouse and estimate range
			const pos = view.posAtCoords({ left: clientX, top: clientY });
			if (pos) {
				const textLength = piiText.length;
				return {
					from: Math.max(0, pos.pos - Math.floor(textLength / 2)),
					to: Math.min(view.state.doc.content.size, pos.pos + Math.ceil(textLength / 2)),
					text: piiText,
					type: 'pii'
				};
			}
		}
	}

	// Check if we're hovering over a modifier highlight
	const modifierElement = target.closest('.pii-modifier-highlight');
	if (modifierElement) {
		const modifierText = modifierElement.getAttribute('data-modifier-entity') || modifierElement.textContent || '';
		if (modifierText.length >= 2) {
			// Try to find the exact position using modifier plugin state
			try {
				const modifierState = piiModifierExtensionKey.getState(view.state);
				if (modifierState?.modifiers) {
					// Find the modifier that matches this entity text
					const matchingModifier = modifierState.modifiers.find((modifier: any) => 
						modifier.entity.toLowerCase() === modifierText.toLowerCase()
					);
					if (matchingModifier) {
						// Find actual position of this modifier entity in the document
						const pos = view.posAtCoords({ left: clientX, top: clientY });
						if (pos) {
							const textLength = modifierText.length;
							return {
								from: Math.max(0, pos.pos - Math.floor(textLength / 2)),
								to: Math.min(view.state.doc.content.size, pos.pos + Math.ceil(textLength / 2)),
								text: modifierText,
								type: 'modifier'
							};
						}
					}
				}
			} catch (error) {
				console.log('PiiModifierExtension: Could not access modifier state:', error);
			}
			
			// Fallback: get position from mouse and estimate range
			const pos = view.posAtCoords({ left: clientX, top: clientY });
			if (pos) {
				const textLength = modifierText.length;
				return {
					from: Math.max(0, pos.pos - Math.floor(textLength / 2)),
					to: Math.min(view.state.doc.content.size, pos.pos + Math.ceil(textLength / 2)),
					text: modifierText,
					type: 'modifier'
				};
			}
		}
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
	
	// Only find exact prefix matches - autocomplete should only suggest words that start with the input
	const exactMatch = labels.find(label => label.startsWith(upperInput));
	if (exactMatch) return exactMatch;
	
	// No partial/substring matching - let user type what they want
	return null;
}

// Create hover menu element for PII entities
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
			const typeIcon = modifier.action === 'ignore' ? '🚫' : '🏷️';
			const typeText = modifier.action === 'ignore' ? 'Ignore' : `${modifier.type}`;
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
		ignoreBtn.textContent = '🚫 Ignore';
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
	maskBtn.textContent = 'Change Label';
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
		const piiType = isDefaultValue ? 'CUSTOM' : labelInput.value.trim().toUpperCase();
		if (piiType) {
			onMask(piiType);
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

// Create text selection menu element
function createSelectionMenu(
	selectionInfo: { 
		selectedText: string; 
		tokenizedWords: Array<{ word: string; from: number; to: number; }>; 
		from: number; 
		to: number; 
		x: number; 
		y: number; 
	},
	onMaskSelection: (text: string, label: string, from: number, to: number) => void,
	timeoutManager?: { clearAll: () => void; setFallback: (callback: () => void, delay: number) => void }
): HTMLElement {
	const menu = document.createElement('div');
	menu.className = 'pii-modifier-selection-menu';
	menu.style.cssText = `
		position: fixed;
		left: ${Math.min(selectionInfo.x, window.innerWidth - 300)}px;
		top: ${selectionInfo.y - 120}px;
		background: white;
		border: 1px solid #ddd;
		border-radius: 8px;
		box-shadow: 0 4px 20px rgba(0,0,0,0.15);
		padding: 16px;
		z-index: 1000;
		font-family: system-ui, -apple-system, sans-serif;
		font-size: 13px;
		min-width: 280px;
		max-width: 400px;
		max-height: 300px;
		overflow-y: auto;
	`;

	// Header
	const header = document.createElement('div');
	header.style.cssText = `
		display: flex;
		align-items: center;
		gap: 8px;
		font-weight: 600;
		color: #333;
		margin-bottom: 12px;
		font-size: 12px;
	`;
	
	const icon = document.createElement('img');
	icon.src = '/static/icon-purple-32.png';
	icon.style.cssText = `width: 16px; height: 16px; flex-shrink: 0;`;
	
	const headerText = document.createElement('span');
	headerText.textContent = 'Mark text as PII';
	
	header.appendChild(icon);
	header.appendChild(headerText);
	menu.appendChild(header);

	// Selection options
	const optionsContainer = document.createElement('div');
	optionsContainer.style.cssText = `margin-bottom: 12px;`;

	// Tokenized words option (default)
	const tokenizedOption = document.createElement('div');
	tokenizedOption.style.cssText = `margin-bottom: 8px;`;

	const tokenizedRadio = document.createElement('input');
	tokenizedRadio.type = 'radio';
	tokenizedRadio.name = 'selection-type';
	tokenizedRadio.value = 'tokenized';
	tokenizedRadio.checked = true;
	tokenizedRadio.id = 'tokenized-option';

	const tokenizedLabel = document.createElement('label');
	tokenizedLabel.htmlFor = 'tokenized-option';
	tokenizedLabel.style.cssText = `
		margin-left: 6px;
		font-weight: 500;
		cursor: pointer;
	`;
	tokenizedLabel.textContent = 'Words: ';

	const tokenizedWords = document.createElement('span');
	tokenizedWords.style.cssText = `
		background: #f0f9ff;
		color: #0369a1;
		padding: 2px 6px;
		border-radius: 4px;
		font-size: 11px;
		margin-left: 4px;
	`;
	tokenizedWords.textContent = `"${selectionInfo.tokenizedWords.map(w => w.word).join(' ')}"`;  // Show as single combined phrase

	tokenizedOption.appendChild(tokenizedRadio);
	tokenizedOption.appendChild(tokenizedLabel);
	tokenizedOption.appendChild(tokenizedWords);

	// Exact selection option
	const exactOption = document.createElement('div');
	exactOption.style.cssText = `margin-bottom: 8px;`;

	const exactRadio = document.createElement('input');
	exactRadio.type = 'radio';
	exactRadio.name = 'selection-type';
	exactRadio.value = 'exact';
	exactRadio.id = 'exact-option';

	const exactLabel = document.createElement('label');
	exactLabel.htmlFor = 'exact-option';
	exactLabel.style.cssText = `
		margin-left: 6px;
		font-weight: 500;
		cursor: pointer;
	`;
	exactLabel.textContent = 'Exact: ';

	const exactText = document.createElement('span');
	exactText.style.cssText = `
		background: #fef3c7;
		color: #92400e;
		padding: 2px 6px;
		border-radius: 4px;
		font-size: 11px;
		margin-left: 4px;
	`;
	exactText.textContent = `"${selectionInfo.selectedText}"`;

	exactOption.appendChild(exactRadio);
	exactOption.appendChild(exactLabel);
	exactOption.appendChild(exactText);

	optionsContainer.appendChild(tokenizedOption);
	optionsContainer.appendChild(exactOption);
	menu.appendChild(optionsContainer);

	// Label input section
	const labelSection = document.createElement('div');
	labelSection.style.cssText = `
		display: flex;
		flex-direction: column;
		gap: 8px;
	`;

	const labelInput = document.createElement('input');
	labelInput.type = 'text';
	labelInput.value = 'CUSTOM';
	labelInput.placeholder = 'Enter PII label type';
	labelInput.style.cssText = `
		width: 100%;
		padding: 8px 10px;
		border: 1px solid #ddd;
		border-radius: 4px;
		font-size: 12px;
		box-sizing: border-box;
		color: #999;
	`;

	let isDefaultValue = true;
	let skipAutocompletion = false;

	// Handle input focus
	const handleInputFocus = (e: Event) => {
		e.stopPropagation();
		
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

	labelInput.addEventListener('blur', () => {
		if (timeoutManager) {
			(timeoutManager as any).setInputFocused(false);
		}
		
		if (labelInput.value.trim() === '') {
			labelInput.value = 'CUSTOM';
			labelInput.style.color = '#999';
			isDefaultValue = true;
		}
	});

	// Handle autocompletion
	labelInput.addEventListener('input', (e) => {
		e.stopPropagation();
		
		if (skipAutocompletion) {
			skipAutocompletion = false;
			return;
		}
		
		const inputValue = labelInput.value;
		
		if (!isDefaultValue && inputValue) {
			const bestMatch = findBestMatch(inputValue, PREDEFINED_LABELS);
			
			if (bestMatch && bestMatch !== inputValue.toUpperCase()) {
				const cursorPos = labelInput.selectionStart || 0;
				labelInput.value = bestMatch;
				labelInput.setSelectionRange(cursorPos, bestMatch.length);
			}
		}
	});

	// Handle keyboard events
	labelInput.addEventListener('keydown', (e) => {
		e.stopPropagation();
		
		if (e.key === 'Enter') {
			e.preventDefault();
			markSelectedText();
		} else if (e.key === 'Tab') {
			e.preventDefault();
			labelInput.setSelectionRange(labelInput.value.length, labelInput.value.length);
		} else if (e.key === 'Escape') {
			e.preventDefault();
			menu.remove();
		} else if (e.key === 'Backspace') {
			skipAutocompletion = true;
		}
	});

	labelInput.addEventListener('keyup', (e) => {
		e.stopPropagation();
	});

	// Mark button
	const markBtn = document.createElement('button');
	markBtn.textContent = 'Mask';
	markBtn.style.cssText = `
		width: 100%;
		padding: 8px 12px;
		border: 1px solid #6b46c1;
		background: #6b46c1;
		border-radius: 4px;
		cursor: pointer;
		font-size: 12px;
		color: white;
		font-weight: 500;
		transition: background-color 0.2s ease;
	`;

	markBtn.addEventListener('mouseenter', () => {
		markBtn.style.backgroundColor = '#553c9a';
	});
	
	markBtn.addEventListener('mouseleave', () => {
		markBtn.style.backgroundColor = '#6b46c1';
	});

			// Mark selected text function
		const markSelectedText = () => {
			const piiType = isDefaultValue ? 'CUSTOM' : labelInput.value.trim().toUpperCase();
			if (!piiType) {
				labelInput.style.borderColor = '#ff6b6b';
				labelInput.focus();
				setTimeout(() => {
					labelInput.style.borderColor = '#ddd';
				}, 1000);
				return;
			}

			const isTokenized = tokenizedRadio.checked;
			
			if (isTokenized) {
				// Combine all tokenized words into a single PII entity
				if (selectionInfo.tokenizedWords.length > 0) {
					// Get the full range from first word start to last word end
					const firstWord = selectionInfo.tokenizedWords[0];
					const lastWord = selectionInfo.tokenizedWords[selectionInfo.tokenizedWords.length - 1];
					const combinedText = selectionInfo.tokenizedWords.map(w => w.word).join(' ');
					
					// Create one modifier spanning the full tokenized range
					onMaskSelection(combinedText, piiType, firstWord.from, lastWord.to);
				}
			} else {
				// Mark exact selection
				onMaskSelection(selectionInfo.selectedText, piiType, selectionInfo.from, selectionInfo.to);
			}

			menu.remove();
		};

	markBtn.addEventListener('click', (e) => {
		e.preventDefault();
		e.stopPropagation();
		markSelectedText();
	});

	labelSection.appendChild(labelInput);
	labelSection.appendChild(markBtn);
	menu.appendChild(labelSection);

	// Hover protection
	menu.addEventListener('mouseenter', () => {
		if (timeoutManager) {
			timeoutManager.clearAll();
		}
	});

	menu.addEventListener('mouseleave', (e) => {
		const relatedTarget = e.relatedTarget as HTMLElement;
		if (relatedTarget && menu.contains(relatedTarget)) {
			return;
		}
		
		if (timeoutManager) {
			timeoutManager.setFallback(() => {
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
			conversationId: '',
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
		const { enabled, conversationId, onModifiersChanged, availableLabels } = options;

		console.log('PiiModifierExtension: Adding ProseMirror plugins', {
			enabled,
			conversationId,
			hasCallback: !!onModifiersChanged,
			labelsCount: availableLabels?.length || 0
		});

		if (!enabled) {
			console.log('PiiModifierExtension: Disabled - not adding plugins');
			return [];
		}

		let hoverMenuElement: HTMLElement | null = null;
		let selectionMenuElement: HTMLElement | null = null;
		let hoverTimeout: number | null = null;
		let menuCloseTimeout: ReturnType<typeof setTimeout> | null = null;
		let isMouseOverMenu = false;
		let isInputFocused = false;

		const plugin = new Plugin<PiiModifierState>({
			key: piiModifierExtensionKey,

			state: {
				init(): PiiModifierState {
					console.log('PiiModifierExtension: Initializing extension state');
					
					// Load modifiers from session manager if available
					const piiSessionManager = PiiSessionManager.getInstance();
					
					// Load conversation state if we have a conversationId
					if (conversationId) {
						console.log(`PiiModifierExtension: Loading conversation state for ${conversationId}`);
						piiSessionManager.loadConversationState(conversationId);
					}
					
					// Use the getActiveModifiers method consistently
					const loadedModifiers = piiSessionManager.getActiveModifiers(conversationId);
					
					console.log(`PiiModifierExtension: Loaded ${loadedModifiers.length} modifiers from session manager`, {
						conversationId: conversationId || 'global',
						modifiers: loadedModifiers.map(m => ({ entity: m.entity, action: m.action, type: m.type }))
					});
					
					return {
						modifiers: loadedModifiers,
						currentConversationId: conversationId, // Store the conversation ID in state
						hoveredWordInfo: null,
						selectedTextInfo: null
					};
				},

				apply(tr, prevState): PiiModifierState {
					let newState = { ...prevState };

					// Document changes don't affect modifiers since we search for entity text dynamically
					// No position tracking needed

					// Handle plugin-specific meta actions
					const meta = tr.getMeta(piiModifierExtensionKey);
					if (meta) {
						console.log('PiiModifierExtension: Handling meta action:', meta.type);
						switch (meta.type) {
							case 'RELOAD_CONVERSATION_MODIFIERS':
								// Reload modifiers for a conversation
								const piiSessionManagerReload = PiiSessionManager.getInstance();
								const reloadConversationId = meta.conversationId;
								
								console.log(`PiiModifierExtension: Reloading modifiers for conversation ${reloadConversationId || 'global'}`);
								
								// Load conversation state first if we have a conversationId
								if (reloadConversationId) {
									piiSessionManagerReload.loadConversationState(reloadConversationId);
								}
								
								// Use getActiveModifiers consistently
								const reloadedModifiers = piiSessionManagerReload.getActiveModifiers(reloadConversationId);
								
								newState = {
									...newState,
									modifiers: reloadedModifiers,
									currentConversationId: reloadConversationId // Update the conversation ID in state
								};

								if (onModifiersChanged) {
									onModifiersChanged(reloadedModifiers);
								}
								
								console.log(`PiiModifierExtension: Reloaded ${reloadedModifiers.length} modifiers`, {
									conversationId: reloadConversationId || 'global',
									modifiers: reloadedModifiers.map(m => ({ entity: m.entity, action: m.action, type: m.type }))
								});
								break;
								
							case 'ADD_MODIFIER':
								const newModifier: PiiModifier = {
									id: generateModifierId(),
									action: meta.modifierAction,
									entity: meta.entity,
									type: meta.piiType,
								};

								// Replace any existing modifier for the same entity text (case-insensitive)
								const filteredModifiers = newState.modifiers.filter(modifier => 
									modifier.entity.toLowerCase() !== meta.entity.toLowerCase()
								);
								
								const updatedModifiers = [...filteredModifiers, newModifier];

								newState = {
									...newState,
									modifiers: updatedModifiers
								};

								// Store in session manager using consistent approach
								const piiSessionManager = PiiSessionManager.getInstance();
								const addConversationId = newState.currentConversationId;
								if (addConversationId) {
									piiSessionManager.setConversationModifiers(addConversationId, updatedModifiers);
									console.log(`PiiModifierExtension: Stored ${updatedModifiers.length} modifiers for conversation ${addConversationId}`);
								} else {
									piiSessionManager.setGlobalModifiers(updatedModifiers);
									console.log(`PiiModifierExtension: Stored ${updatedModifiers.length} global modifiers`);
								}

								if (onModifiersChanged) {
									onModifiersChanged(updatedModifiers);
								}
								break;

							case 'REMOVE_MODIFIER':
								const remainingModifiers = newState.modifiers.filter(m => m.id !== meta.modifierId);
								newState = {
									...newState,
									modifiers: remainingModifiers
								};

								// Store in session manager using consistent approach
								const piiSessionManagerRemove = PiiSessionManager.getInstance();
								const removeConversationId = newState.currentConversationId;
								if (removeConversationId) {
									piiSessionManagerRemove.setConversationModifiers(removeConversationId, remainingModifiers);
									console.log(`PiiModifierExtension: Removed modifier, ${remainingModifiers.length} remaining for conversation ${removeConversationId}`);
								} else {
									piiSessionManagerRemove.setGlobalModifiers(remainingModifiers);
									console.log(`PiiModifierExtension: Removed modifier, ${remainingModifiers.length} global modifiers remaining`);
								}

								if (onModifiersChanged) {
									onModifiersChanged(remainingModifiers);
								}
								break;
								
							case 'CLEAR_MODIFIERS':
								newState = {
									...newState,
									modifiers: []
								};

								// Store in session manager using consistent approach
								const piiSessionManagerClear = PiiSessionManager.getInstance();
								const clearConversationId = newState.currentConversationId;
								if (clearConversationId) {
									piiSessionManagerClear.setConversationModifiers(clearConversationId, []);
									console.log(`PiiModifierExtension: Cleared all modifiers for conversation ${clearConversationId}`);
								} else {
									piiSessionManagerClear.setGlobalModifiers([]);
									console.log(`PiiModifierExtension: Cleared all global modifiers`);
								}

								if (onModifiersChanged) {
									onModifiersChanged([]);
								}
								break;
						}
					}

					return newState;
				}
			},

			props: {
				handleClick(view, pos, event) {
					const target = event.target as HTMLElement;
					
					// Close hover menu if clicking outside of it
					if (hoverMenuElement) {
						const isClickInsideHoverMenu = hoverMenuElement.contains(target);
						
						if (!isClickInsideHoverMenu) {
							hoverMenuElement.remove();
							hoverMenuElement = null;
						}
					}
					
					// Close selection menu if clicking outside of it
					if (selectionMenuElement) {
						const isClickInsideSelectionMenu = selectionMenuElement.contains(target);
						
						if (!isClickInsideSelectionMenu) {
							selectionMenuElement.remove();
							selectionMenuElement = null;
						}
					}
					
					// Reset input focus state if clicking outside menus
					if (!hoverMenuElement && !selectionMenuElement) {
						isInputFocused = false;
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
						// Check if mouse is over existing menus
						const isOverHoverMenu = hoverMenuElement && hoverMenuElement.contains(event.target as Node);
						const isOverSelectionMenu = selectionMenuElement && selectionMenuElement.contains(event.target as Node);
						
						if (isOverHoverMenu || isOverSelectionMenu) {
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

						// Don't show hover menu if selection menu is active
						if (selectionMenuElement) {
							return;
						}

						// Clear existing timeout
						if (hoverTimeout) {
							clearTimeout(hoverTimeout);
						}

						// Set new timeout for hover
						hoverTimeout = window.setTimeout(() => {
							// Use DOM-based entity detection instead of position-based
							const existingEntity = findExistingEntityAtPosition(view, event.clientX, event.clientY);
							
							if (!existingEntity) {
								// Hide menu if no entity found
								if (hoverMenuElement) {
									hoverMenuElement.remove();
									hoverMenuElement = null;
								}
								return;
							}

							// We found an existing PII or modifier entity
							let targetInfo = {
								word: existingEntity.text,
								from: existingEntity.from,
								to: existingEntity.to
							};
							const isPiiHighlighted = existingEntity.type === 'pii';
							
							console.log('PiiModifierExtension: Found existing entity at hover position:', {
								text: existingEntity.text,
								type: existingEntity.type
							});

							// Get current conversation ID from plugin state (not options)
							const pluginState = piiModifierExtensionKey.getState(view.state);
							const currentConversationId = pluginState?.currentConversationId;
							
							// Find existing modifiers for this entity using getActiveModifiers consistently
							const piiSessionManager = PiiSessionManager.getInstance();
							
							// Ensure conversation state is loaded if we have a conversationId
							if (currentConversationId) {
								piiSessionManager.loadConversationState(currentConversationId);
							}
							
							const sessionModifiers = piiSessionManager.getActiveModifiers(currentConversationId);

							console.log('PiiModifierExtension: Session modifiers for hover', {
								conversationId: currentConversationId || 'global',
								modifierCount: sessionModifiers.length,
								modifiers: sessionModifiers.map(m => ({ entity: m.entity, action: m.action, type: m.type }))
							});
							
							const targetText = targetInfo.word;
							
							// Check if the hovered entity is part of any modifier entity
							let existingModifiers = sessionModifiers.filter(modifier => {
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
									modifierAction: 'ignore' as ModifierAction,
									entity: finalTargetText,
									from: targetInfo.from,
									to: targetInfo.to
								});
								view.dispatch(tr);

								if (hoverMenuElement) {
									hoverMenuElement.remove();
									hoverMenuElement = null;
								}
								timeoutManager.clearAll();
							};

							const onMask = (piiType: string) => {
								const tr = view.state.tr.setMeta(piiModifierExtensionKey, {
									type: 'ADD_MODIFIER',
									modifierAction: 'mask' as ModifierAction,
									entity: finalTargetText,
									piiType,
									from: targetInfo.from,
									to: targetInfo.to
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
									word: finalTargetText,
									from: targetInfo.from,
									to: targetInfo.to,
									x: event.clientX,
									y: event.clientY
								},
								onIgnore,
								onMask,
								isPiiHighlighted, // Show ignore button if detected as PII
								existingModifiers, // Pass existing modifiers
								onRemoveModifier, // Pass removal callback
								timeoutManager, // Pass timeout manager
								existingModifiers.length === 0 || existingModifiers.some(m => m.action === 'mask') // Show text field if no modifiers or has mask modifiers
							);

							document.body.appendChild(hoverMenuElement);

							// Set a fallback timeout to close menu after 10 seconds of inactivity
							timeoutManager.setFallback(() => {
								if (hoverMenuElement) {
									hoverMenuElement.remove();
									hoverMenuElement = null;
								}
							}, 10000);

						}, 300);
					},

					mouseup: (view, event) => {
						// Handle text selection for selection menu
						const selection = view.state.selection;
						
						// Only show selection menu if there's actual text selected
						if (selection.empty || selection.from === selection.to) {
							// Close selection menu if no selection
							if (selectionMenuElement) {
								selectionMenuElement.remove();
								selectionMenuElement = null;
							}
							return;
						}

						// Get selected text
						const selectedText = view.state.doc.textBetween(selection.from, selection.to);
						
						// Don't show menu for very short selections
						if (selectedText.length < 2) {
							return;
						}

						// Find tokenized words touched by the selection
						const tokenizedWords = findTokenizedWords(view.state.doc, selection.from, selection.to);
						
						// Don't show menu if no words found
						if (tokenizedWords.length === 0) {
							return;
						}

						// Close hover menu if it exists
						if (hoverMenuElement) {
							hoverMenuElement.remove();
							hoverMenuElement = null;
						}

						// Close existing selection menu
						if (selectionMenuElement) {
							selectionMenuElement.remove();
						}

						// Create timeout manager for selection menu
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

						const onMaskSelection = (text: string, piiType: string, from: number, to: number) => {
							const tr = view.state.tr.setMeta(piiModifierExtensionKey, {
								type: 'ADD_MODIFIER',
								modifierAction: 'mask' as ModifierAction,
								entity: text,
								piiType,
								from,
								to
							});
							view.dispatch(tr);

							if (selectionMenuElement) {
								selectionMenuElement.remove();
								selectionMenuElement = null;
							}
							timeoutManager.clearAll();
						};

						// Create selection menu
						selectionMenuElement = createSelectionMenu(
							{
								selectedText,
								tokenizedWords,
								from: selection.from,
								to: selection.to,
								x: event.clientX,
								y: event.clientY
							},
							onMaskSelection,
							timeoutManager
						);

						document.body.appendChild(selectionMenuElement);

						// Set a fallback timeout to close menu after 15 seconds
						timeoutManager.setFallback(() => {
							if (selectionMenuElement) {
								selectionMenuElement.remove();
								selectionMenuElement = null;
							}
						}, 15000);
					},

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
						if (hoverMenuElement) {
							hoverMenuElement.remove();
							hoverMenuElement = null;
						}
						if (selectionMenuElement) {
							selectionMenuElement.remove();
							selectionMenuElement = null;
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

			// Reload modifiers for a conversation (called when conversation changes)
			reloadConversationModifiers: (conversationId: string) => ({ state, dispatch }: any) => {
				console.log(`PiiModifierExtension: Command to reload modifiers for conversation`, {
					newConversationId: conversationId,
					hasDispatch: !!dispatch
				});
				
				const tr = state.tr.setMeta(piiModifierExtensionKey, {
					type: 'RELOAD_CONVERSATION_MODIFIERS',
					conversationId
				});

				if (dispatch) {
					dispatch(tr);
					console.log(`PiiModifierExtension: Dispatched reload transaction for conversation ${conversationId}`);
				}

				return true;
			},

			// Clear all modifiers
			clearModifiers: () => ({ state, dispatch }: any) => {
				const pluginState = piiModifierExtensionKey.getState(state);
				if (!pluginState?.modifiers.length) {
					return false;
				}

				const tr = state.tr.setMeta(piiModifierExtensionKey, {
					type: 'CLEAR_MODIFIERS'
				});

				if (dispatch) {
					dispatch(tr);
				}

				return true;
			},

			// Add a modifier programmatically
			addModifier: (options: { action: ModifierAction; entity: string; type?: string; from: number; to: number; }) => ({ state, dispatch }: any) => {
				const tr = state.tr.setMeta(piiModifierExtensionKey, {
					type: 'ADD_MODIFIER',
					modifierAction: options.action,
					entity: options.entity,
					piiType: options.type,
					from: options.from,
					to: options.to
				});

				if (dispatch) {
					dispatch(tr);
				}

				return true;
			},

			// Remove a modifier by ID
			removeModifier: (modifierId: string) => ({ state, dispatch }: any) => {
				const tr = state.tr.setMeta(piiModifierExtensionKey, {
					type: 'REMOVE_MODIFIER',
					modifierId
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
					action: modifier.action,
					entity: modifier.entity,
					...(modifier.type && { type: modifier.type })
				}));
			},

			// Get modifiers for a specific entity text
			getModifiersForEntity: (entityText: string) => ({ state }: any) => {
				const pluginState = piiModifierExtensionKey.getState(state);
				if (!pluginState?.modifiers.length) {
					return [];
				}

				return pluginState.modifiers.filter(modifier => 
					modifier.entity.toLowerCase() === entityText.toLowerCase()
				);
			}
		} as any;
	}
});

// Utility function to add CSS styles for modifier system
export function addPiiModifierStyles() {
	const styleId = 'pii-modifier-styles';
	
	// Check if styles already exist
	if (document.getElementById(styleId)) {
		return;
	}

	const styleElement = document.createElement('style');
	styleElement.id = styleId;
	styleElement.textContent = `
		/* Menu animations and interactions */
		.pii-modifier-hover-menu,
		.pii-modifier-selection-menu {
			animation: fadeIn 0.2s ease-in-out;
			pointer-events: auto;
		}

		@keyframes fadeIn {
			from { opacity: 0; transform: translateY(5px); }
			to { opacity: 1; transform: translateY(0); }
		}

		.pii-modifier-hover-menu button:hover,
		.pii-modifier-selection-menu button:hover {
			transform: scale(1.02);
			transition: transform 0.1s ease;
			box-shadow: 0 2px 8px rgba(0,0,0,0.1);
		}

		.pii-modifier-hover-menu input:focus,
		.pii-modifier-selection-menu input:focus {
			outline: none;
			border-color: #4ecdc4;
			box-shadow: 0 0 0 2px rgba(78, 205, 196, 0.2);
		}

		/* Modifier highlighting - takes precedence over PII detection */
		.pii-modifier-highlight {
			position: relative;
			border-radius: 3px;
			padding: 1px 2px;
			cursor: pointer;
			transition: all 0.2s ease;
			z-index: 10; /* Higher than PII highlights */
		}

		.pii-modifier-highlight:hover {
			box-shadow: 0 1px 3px rgba(0,0,0,0.2);
		}

		/* Mask modifier styling - orange text with green background/border */
		.pii-modifier-highlight.pii-modifier-mask {
			color: #ca8a04 !important; /* Orange text - takes precedence */
			background-color: rgba(34, 197, 94, 0.2) !important; /* Green background */
			border-bottom: 1px dashed #15803d !important; /* Green dashed underline */
		}

		.pii-modifier-highlight.pii-modifier-mask:hover {
			color: #a16207 !important;
			background-color: rgba(34, 197, 94, 0.3) !important;
			border-bottom: 2px dashed #15803d !important;
		}

		/* Ignore modifier styling - orange text, no background */
		.pii-modifier-highlight.pii-modifier-ignore {
			color: #ca8a04 !important; /* Orange text - takes precedence */
			text-decoration: line-through !important; /* Strike through */
			opacity: 0.7 !important;
		}

		.pii-modifier-highlight.pii-modifier-ignore:hover {
			color: #a16207 !important;
			opacity: 0.9 !important;
		}

		/* Ensure modifier styles take precedence over PII styles */
		.pii-highlight.pii-modifier-highlight {
			color: #ca8a04 !important;
		}

		.pii-highlight.pii-modifier-highlight.pii-modifier-mask {
			color: #ca8a04 !important;
			background-color: rgba(34, 197, 94, 0.2) !important;
			border-bottom: 1px dashed #15803d !important;
		}

		.pii-highlight.pii-modifier-highlight.pii-modifier-ignore {
			color: #ca8a04 !important;
			background-color: transparent !important;
			border-bottom: none !important;
			text-decoration: line-through !important;
			opacity: 0.7 !important;
		}
	`;

	document.head.appendChild(styleElement);
}