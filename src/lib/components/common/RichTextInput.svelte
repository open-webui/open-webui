<script lang="ts">
	import { marked } from 'marked';
	import TurndownService from 'turndown';
	import { gfm } from 'turndown-plugin-gfm';
	const turndownService = new TurndownService({
		codeBlockStyle: 'fenced',
		headingStyle: 'atx'
	});
	turndownService.escape = (string) => string;

	// Use turndown-plugin-gfm for proper GFM table support
	turndownService.use(gfm);

	import { onMount, onDestroy } from 'svelte';
	import { createEventDispatcher } from 'svelte';
	const eventDispatch = createEventDispatcher();

	import { EditorState, Plugin, PluginKey, TextSelection } from 'prosemirror-state';
	import { Decoration, DecorationSet } from 'prosemirror-view';
	import { Editor } from '@tiptap/core';

	import { AIAutocompletion } from './RichTextInput/AutoCompletion.js';
	import Table from '@tiptap/extension-table';
	import TableRow from '@tiptap/extension-table-row';
	import TableHeader from '@tiptap/extension-table-header';
	import TableCell from '@tiptap/extension-table-cell';

	import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
	import Placeholder from '@tiptap/extension-placeholder';
	import { all, createLowlight } from 'lowlight';
	import StarterKit from '@tiptap/starter-kit';
	import Highlight from '@tiptap/extension-highlight';
	import Typography from '@tiptap/extension-typography';

	import { PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';
	
	// PII Detection imports
	import { maskPiiText, type PiiEntity, type KnownPiiEntity } from '$lib/apis/pii';
	import { PiiHighlighter } from './RichTextInput/PiiHighlighter';
	import { debounce, extractPlainTextFromEditor, createPiiHighlightStyles, PiiSessionManager, type ExtendedPiiEntity } from '$lib/utils/pii';
	import PiiHoverOverlay from './PiiHoverOverlay.svelte';

	export let oncompositionstart = (e: CompositionEvent) => {};
	export let oncompositionend = (e: CompositionEvent) => {};
	export let onChange = (e: any) => {};

	// create a lowlight instance with all languages loaded
	const lowlight = createLowlight(all);

	export let className = 'input-prose';
	export let placeholder = 'Type here...';

	export let id = '';
	export let value = '';
	export let html = '';

	export let json = false;
	export let raw = false;
	export let editable = true;

	export let preserveBreaks = false;
	export let generateAutoCompletion: Function = async () => null;
	export let autocomplete = false;
	export let messageInput = false;
	export let shiftEnter = false;
	export let largeTextAsFile = false;
	
	// PII Detection props
	export let enablePiiDetection = false;
	export let piiApiKey = '';
	export let conversationId = '';
	export let onPiiDetected: (entities: ExtendedPiiEntity[], maskedText: string) => void = () => {};

	let element: HTMLElement;
	let editor: any;
	
	// PII Detection state
	let piiEntities: ExtendedPiiEntity[] = [];
	let isDetectingPii = false;
	let lastDetectedText = '';
	let piiSessionManager = PiiSessionManager.getInstance();
	
	// Reactive statement to restore entities when conversation changes or input is cleared
	$: if (enablePiiDetection && conversationId) {
		// Get entities for this conversation
		let storedEntities = piiSessionManager.getConversationEntities(conversationId);
		console.log('RichTextInput: Reactive check for conversation:', conversationId, 'stored entities:', storedEntities.length, 'current entities:', piiEntities.length);
		
		// If no entities found for this conversationId, check if there are entities stored under empty string
		// This handles the case where entities were stored before conversationId was assigned
		if (storedEntities.length === 0) {
			const emptyIdEntities = piiSessionManager.getConversationEntities('');
			if (emptyIdEntities.length > 0) {
				console.log('RichTextInput: Migrating', emptyIdEntities.length, 'entities from empty conversationId to:', conversationId);
				// Migrate entities from empty ID to actual conversationId  
				// Convert ExtendedPiiEntity back to PiiEntity for setConversationEntities
				const piiEntitiesForMigration = emptyIdEntities.map(e => ({
					id: e.id,
					type: e.type,
					label: e.label,
					raw_text: e.raw_text,
					occurrences: e.occurrences || []
				}));
				piiSessionManager.setConversationEntities(conversationId, piiEntitiesForMigration);
				// Clear the empty ID storage
				piiSessionManager.clearConversationState('');
				// Get the migrated entities
				storedEntities = piiSessionManager.getConversationEntities(conversationId);
			}
		}
		
		if (storedEntities.length > 0) {
			console.log('RichTextInput: Restoring', storedEntities.length, 'PII entities for conversation:', conversationId, 'entities:', storedEntities.map(e => e.label));
			piiEntities = storedEntities;
			// Update editor if it exists
			if (editor && editor.commands.updatePiiEntities) {
				editor.commands.updatePiiEntities(piiEntities);
			}
		}
	}

	// Additional reactive statement to restore entities when value is cleared but entities exist
	$: if (enablePiiDetection && conversationId && (!value || value.trim() === '') && piiEntities.length === 0) {
		const storedEntities = piiSessionManager.getConversationEntities(conversationId);
		console.log('RichTextInput: Input cleared check for conversation:', conversationId, 'value:', value, 'stored entities:', storedEntities.length);
		if (storedEntities.length > 0) {
			console.log('RichTextInput: Input cleared, restoring', storedEntities.length, 'conversation entities:', storedEntities.map(e => e.label));
			piiEntities = storedEntities;
			if (editor && editor.commands.updatePiiEntities) {
				editor.commands.updatePiiEntities(piiEntities);
			}
		}
	}
	
	// Hover overlay state
	let hoverOverlayVisible = false;
	let hoverOverlayEntity: ExtendedPiiEntity | null = null;
	let hoverOverlayPosition = { x: 0, y: 0 };
	let hoverTimeout: ReturnType<typeof setTimeout> | null = null;
	let isOverPiiElement = false;
	let isOverOverlay = false;

	const options = {
		throwOnError: false
	};

	$: if (editor) {
		editor.setOptions({
			editable: editable
		});
	}
	
	// Debug PII entities and editor state
	$: {
		console.log('RichTextInput debug:', {
			enablePiiDetection,
			hasApiKey: !!piiApiKey,
			piiEntitiesCount: piiEntities.length,
			hasEditor: !!editor,
			editorHasPiiCommand: editor ? !!editor.commands.updatePiiEntities : false
		});
	}

	$: if (value === null && html !== null && editor) {
		editor.commands.setContent(html);
	}

	// Function to find the next template in the document
	function findNextTemplate(doc, from = 0) {
		const patterns = [{ start: '{{', end: '}}' }];

		let result = null;

		doc.nodesBetween(from, doc.content.size, (node, pos) => {
			if (result) return false; // Stop if we've found a match
			if (node.isText) {
				const text = node.text;
				let index = Math.max(0, from - pos);
				while (index < text.length) {
					for (const pattern of patterns) {
						if (text.startsWith(pattern.start, index)) {
							const endIndex = text.indexOf(pattern.end, index + pattern.start.length);
							if (endIndex !== -1) {
								result = {
									from: pos + index,
									to: pos + endIndex + pattern.end.length
								};
								return false; // Stop searching
							}
						}
					}
					index++;
				}
			}
		});

		return result;
	}

	// Function to select the next template in the document
	function selectNextTemplate(state, dispatch) {
		const { doc, selection } = state;
		const from = selection.to;
		let template = findNextTemplate(doc, from);

		if (!template) {
			// If not found, search from the beginning
			template = findNextTemplate(doc, 0);
		}

		if (template) {
			if (dispatch) {
				const tr = state.tr.setSelection(TextSelection.create(doc, template.from, template.to));
				dispatch(tr);
			}
			return true;
		}
		return false;
	}

	export const setContent = (content: any) => {
		editor.commands.setContent(content);
	};
	
	// PII Detection function
	const detectPii = async (text: string) => {
		if (!enablePiiDetection || !piiApiKey || !text.trim() || text === lastDetectedText) {
			console.log('RichTextInput: PII detection skipped', { enablePiiDetection, hasApiKey: !!piiApiKey, textLength: text.length, sameAsLast: text === lastDetectedText, conversationId });
			return;
		}
		
		console.log('RichTextInput: Starting PII detection for text:', text.substring(0, 100), 'conversationId:', conversationId);
		isDetectingPii = true;
		lastDetectedText = text;
		
		try {
			// Get known entities from current conversation if available
			const knownEntities = conversationId 
				? piiSessionManager.getKnownEntitiesForApi(conversationId)
				: piiSessionManager.getEntities().map(entity => ({
					id: entity.id,
					label: entity.label,
					name: entity.raw_text
				}));
			
			console.log('RichTextInput: Sending known entities to API:', knownEntities.length, 'for conversation:', conversationId, 'entities:', knownEntities);
			
			const response = await maskPiiText(piiApiKey, [text], knownEntities, false, false);
			if (response.pii && response.pii[0]) {
				console.log('RichTextInput: PII detection successful, found entities:', response.pii[0]);
				// Set entities in session manager (conversation-specific if conversationId provided)
				if (conversationId) {
					piiSessionManager.setConversationEntities(conversationId, response.pii[0]);
					piiEntities = piiSessionManager.getConversationEntities(conversationId);
				} else {
					piiSessionManager.setEntities(response.pii[0]);
					piiEntities = piiSessionManager.getEntities();
				}
				console.log('RichTextInput: Updated session manager, entities count:', piiEntities.length, 'all entities:', piiEntities.map(e => e.label));
				
				// Update the editor with PII highlighting
				if (editor && editor.commands.updatePiiEntities) {
					editor.commands.updatePiiEntities(piiEntities);
					console.log('RichTextInput: Updated editor with PII entities');
				}
				
				// Notify parent component
				onPiiDetected(piiEntities, response.text[0]);
			} else {
				console.log('RichTextInput: No PII entities found in response');
			}
		} catch (error) {
			console.error('PII detection failed:', error);
		} finally {
			isDetectingPii = false;
		}
	};
	
	// Debounced PII detection
	const debouncedDetectPii = debounce(detectPii, 500);
	
	// Hover overlay handlers
	const handlePiiHover = (entity: ExtendedPiiEntity, position: { x: number, y: number }) => {
		console.log('RichTextInput: handlePiiHover called', { entity: entity.label, position });
		if (hoverTimeout) {
			clearTimeout(hoverTimeout);
			hoverTimeout = null;
		}
		isOverPiiElement = true;
		hoverOverlayEntity = entity;
		hoverOverlayPosition = position;
		hoverOverlayVisible = true;
		console.log('RichTextInput: Overlay should now be visible:', hoverOverlayVisible);
	};
	
	const handlePiiHoverEnd = () => {
		console.log('handlePiiHoverEnd called');
		isOverPiiElement = false;
		checkShouldCloseOverlay();
	};
	
	// Overlay mouse events to prevent disappearing when hovering over dialog
	const handleOverlayMouseEnter = () => {
		console.log('Mouse entered overlay');
		if (hoverTimeout) {
			clearTimeout(hoverTimeout);
			hoverTimeout = null;
		}
		isOverOverlay = true;
	};
	
	const handleOverlayMouseLeave = () => {
		console.log('Mouse left overlay');
		isOverOverlay = false;
		checkShouldCloseOverlay();
	};
	
	// Helper function to check if overlay should close
	const checkShouldCloseOverlay = () => {
		console.log('checkShouldCloseOverlay called:', { isOverPiiElement, isOverOverlay });
		if (hoverTimeout) {
			clearTimeout(hoverTimeout);
		}
		
		// Only close if we're not over either the PII element or the overlay
		if (!isOverPiiElement && !isOverOverlay) {
			console.log('Starting close timeout');
			hoverTimeout = setTimeout(() => {
				console.log('Closing overlay due to timeout');
				hoverOverlayVisible = false;
				hoverOverlayEntity = null;
			}, 300); // Slightly longer delay to handle rapid mouse movements
		} else {
			console.log('Not closing overlay - still hovering');
		}
	};
	
	const handleOverlayToggle = (event: CustomEvent) => {
		// Update the entities in the editor using conversation-specific entities
		if (conversationId) {
			piiEntities = piiSessionManager.getConversationEntities(conversationId);
		} else {
			piiEntities = piiSessionManager.getEntities();
		}
		if (editor && editor.commands.updatePiiEntities) {
			editor.commands.updatePiiEntities(piiEntities);
		}
	};

	const selectTemplate = () => {
		if (value !== '') {
			// After updating the state, try to find and select the next template
			setTimeout(() => {
				const templateFound = selectNextTemplate(editor.view.state, editor.view.dispatch);
				if (!templateFound) {
					// If no template found, set cursor at the end
					const endPos = editor.view.state.doc.content.size;
					editor.view.dispatch(
						editor.view.state.tr.setSelection(TextSelection.create(editor.view.state.doc, endPos))
					);
				}
			}, 0);
		}
	};

	onMount(async () => {
		// Initialize PII session manager
		if (enablePiiDetection && piiApiKey) {
			piiSessionManager.setApiKey(piiApiKey);
		}
		
		// Add PII highlighting styles
		if (enablePiiDetection) {
			const styleElement = document.createElement('style');
			styleElement.textContent = createPiiHighlightStyles();
			document.head.appendChild(styleElement);
		}
		
		let content = value;

		if (!json) {
			if (preserveBreaks) {
				turndownService.addRule('preserveBreaks', {
					filter: 'br', // Target <br> elements
					replacement: function (content) {
						return '<br/>';
					}
				});
			}

			if (!raw) {
				async function tryParse(value, attempts = 3, interval = 100) {
					try {
						// Try parsing the value
						return marked.parse(value.replaceAll(`\n<br/>`, `<br/>`), {
							breaks: false
						});
					} catch (error) {
						// If no attempts remain, fallback to plain text
						if (attempts <= 1) {
							return value;
						}
						// Wait for the interval, then retry
						await new Promise((resolve) => setTimeout(resolve, interval));
						return tryParse(value, attempts - 1, interval); // Recursive call
					}
				}

				// Usage example
				content = await tryParse(value);
			}
		} else {
			if (html && !content) {
				content = html;
			}
		}

		console.log('content', content);

		editor = new Editor({
			element: element,
			extensions: [
				StarterKit,
				CodeBlockLowlight.configure({
					lowlight
				}),
				Highlight,
				Typography,
				Placeholder.configure({ placeholder }),
				...(enablePiiDetection
					? [
							PiiHighlighter.configure({
								piiEntities: piiEntities,
								highlightClass: 'pii-highlight',
								onHover: handlePiiHover,
								onHoverEnd: handlePiiHoverEnd
							})
						]
					: []),
				Table.configure({ resizable: true }),
				TableRow,
				TableHeader,
				TableCell,
				...(autocomplete
					? [
							AIAutocompletion.configure({
								generateCompletion: async (text) => {
									if (text.trim().length === 0) {
										return null;
									}

									const suggestion = await generateAutoCompletion(text).catch(() => null);
									if (!suggestion || suggestion.trim().length === 0) {
										return null;
									}

									return suggestion;
								}
							})
						]
					: [])
			],
			content: content,
			autofocus: messageInput ? true : false,
			onTransaction: () => {
				// force re-render so `editor.isActive` works as expected
				editor = editor;

				html = editor.getHTML();

				onChange({
					html: editor.getHTML(),
					json: editor.getJSON(),
					md: turndownService.turndown(editor.getHTML())
				});

				if (json) {
					value = editor.getJSON();
				} else {
					if (!raw) {
						let newValue = turndownService
							.turndown(
								editor
									.getHTML()
									.replace(/<p><\/p>/g, '<br/>')
									.replace(/ {2,}/g, (m) => m.replace(/ /g, '\u00a0'))
							)
							.replace(/\u00a0/g, ' ');

						if (!preserveBreaks) {
							newValue = newValue.replace(/<br\/>/g, '');
						}

						if (value !== newValue) {
							value = newValue;

							// check if the node is paragraph as well
							if (editor.isActive('paragraph')) {
								if (value === '') {
									editor.commands.clearContent();
								}
							}
						}
					} else {
						value = editor.getHTML();
					}
				}
				
				// Trigger PII detection on content change
				if (enablePiiDetection && piiApiKey) {
					const plainText = extractPlainTextFromEditor(editor.getHTML());
					if (plainText.trim()) {
						debouncedDetectPii(plainText);
					}
				}
			},
			editorProps: {
				attributes: { id },
				handleDOMEvents: {
					compositionstart: (view, event) => {
						oncompositionstart(event);
						return false;
					},
					compositionend: (view, event) => {
						oncompositionend(event);
						return false;
					},
					focus: (view, event) => {
						eventDispatch('focus', { event });
						return false;
					},
					keyup: (view, event) => {
						eventDispatch('keyup', { event });
						return false;
					},
					keydown: (view, event) => {
						if (messageInput) {
							// Handle Tab Key
							if (event.key === 'Tab') {
								const handled = selectNextTemplate(view.state, view.dispatch);
								if (handled) {
									event.preventDefault();
									return true;
								}
							}

							if (event.key === 'Enter') {
								// Check if the current selection is inside a structured block (like codeBlock or list)
								const { state } = view;
								const { $head } = state.selection;

								// Recursive function to check ancestors for specific node types
								function isInside(nodeTypes: string[]): boolean {
									let currentNode = $head;
									while (currentNode) {
										if (nodeTypes.includes(currentNode.parent.type.name)) {
											return true;
										}
										if (!currentNode.depth) break; // Stop if we reach the top
										currentNode = state.doc.resolve(currentNode.before()); // Move to the parent node
									}
									return false;
								}

								const isInCodeBlock = isInside(['codeBlock']);
								const isInList = isInside(['listItem', 'bulletList', 'orderedList']);
								const isInHeading = isInside(['heading']);

								if (isInCodeBlock || isInList || isInHeading) {
									// Let ProseMirror handle the normal Enter behavior
									return false;
								}
							}

							// Handle shift + Enter for a line break
							if (shiftEnter) {
								if (event.key === 'Enter' && event.shiftKey && !event.ctrlKey && !event.metaKey) {
									editor.commands.setHardBreak(); // Insert a hard break
									view.dispatch(view.state.tr.scrollIntoView()); // Move viewport to the cursor
									event.preventDefault();
									return true;
								}
							}
						}
						eventDispatch('keydown', { event });
						return false;
					},
					paste: (view, event) => {
						if (event.clipboardData) {
							// Extract plain text from clipboard and paste it without formatting
							const plainText = event.clipboardData.getData('text/plain');
							if (plainText) {
								if (largeTextAsFile) {
									if (plainText.length > PASTED_TEXT_CHARACTER_LIMIT) {
										// Dispatch paste event to parent component
										eventDispatch('paste', { event });
										event.preventDefault();
										return true;
									}
								}
								return false;
							}

							// Check if the pasted content contains image files
							const hasImageFile = Array.from(event.clipboardData.files).some((file) =>
								file.type.startsWith('image/')
							);

							// Check for image in dataTransfer items (for cases where files are not available)
							const hasImageItem = Array.from(event.clipboardData.items).some((item) =>
								item.type.startsWith('image/')
							);
							if (hasImageFile) {
								// If there's an image, dispatch the event to the parent
								eventDispatch('paste', { event });
								event.preventDefault();
								return true;
							}

							if (hasImageItem) {
								// If there's an image item, dispatch the event to the parent
								eventDispatch('paste', { event });
								event.preventDefault();
								return true;
							}
						}

						// For all other cases (text, formatted text, etc.), let ProseMirror handle it
						view.dispatch(view.state.tr.scrollIntoView()); // Move viewport to the cursor after pasting
						return false;
					}
				}
			}
		});

		if (messageInput) {
			selectTemplate();
		}
	});

	onDestroy(() => {
		if (editor) {
			editor.destroy();
		}
	});

	$: if (value !== null && editor) {
		onValueChange();
	}

	const onValueChange = () => {
		if (!editor) return;

		if (json) {
			if (JSON.stringify(value) !== JSON.stringify(editor.getJSON())) {
				editor.commands.setContent(value);
				selectTemplate();
			}
		} else {
			if (raw) {
				if (value !== editor.getHTML()) {
					editor.commands.setContent(value);
					selectTemplate();
				}
			} else {
				if (
					value !==
					turndownService
						.turndown(
							(preserveBreaks
								? editor.getHTML().replace(/<p><\/p>/g, '<br/>')
								: editor.getHTML()
							).replace(/ {2,}/g, (m) => m.replace(/ /g, '\u00a0'))
						)
						.replace(/\u00a0/g, ' ')
				) {
					preserveBreaks
						? editor.commands.setContent(value)
						: editor.commands.setContent(
								marked.parse(value.replaceAll(`\n<br/>`, `<br/>`), {
									breaks: false
								})
							); // Update editor content

					selectTemplate();
				}
			}
		}
	};
</script>

<div bind:this={element} class="relative w-full min-w-full h-full min-h-fit {className}" />

<!-- PII Hover Overlay -->
{#if enablePiiDetection}
	<PiiHoverOverlay
		bind:visible={hoverOverlayVisible}
		entity={hoverOverlayEntity}
		position={hoverOverlayPosition}
		on:toggle={handleOverlayToggle}
		on:overlayMouseEnter={(e) => {
			console.log('RichTextInput: overlayMouseEnter event received');
			handleOverlayMouseEnter();
		}}
		on:overlayMouseLeave={(e) => {
			console.log('RichTextInput: overlayMouseLeave event received');
			handleOverlayMouseLeave();
		}}
		on:copy={(event) => {
			// Optional: Show a toast notification
			console.log('Copied:', event.detail.text);
		}}
	/>
{/if}
