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
	import Spinner from '$lib/components/common/Spinner.svelte';

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
	import { type ExtendedPiiEntity } from '$lib/utils/pii';
	import { PiiDetectionExtension } from './RichTextInput/PiiDetectionExtension';
	import {
		PiiModifierExtension,
		addPiiModifierStyles,
		type PiiModifier
	} from './RichTextInput/PiiModifierExtension';
	import { debounce, createPiiHighlightStyles, PiiSessionManager } from '$lib/utils/pii';

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
	export let conversationId: string | undefined = undefined;
	export let onPiiDetected: (entities: ExtendedPiiEntity[], maskedText: string) => void = () => {};
	export let onPiiToggled: (entities: ExtendedPiiEntity[]) => void = () => {};
	export let onPiiDetectionStateChanged: (isDetecting: boolean) => void = () => {};

	// PII Modifier props
	export let enablePiiModifiers = false;
	export let onPiiModifiersChanged: (modifiers: PiiModifier[]) => void = () => {};
	export let piiModifierLabels: string[] = [];

	// PII Loading state
	let isPiiDetectionInProgress = false;

	let element: HTMLElement;
	let editor: any;
	let currentModifiers: PiiModifier[] = [];
	let previousModifiersLength = 0;

	// Generate a content-based hash for modifiers to detect actual changes
	// This is much smarter than just checking array length because it detects:
	// - Changes in modifier type (ignore ↔ mask)
	// - Changes in entity text
	// - Changes in labels
	// - Changes in positions (from/to)
	// - Addition/removal of specific modifiers
	const getModifiersHash = (modifiers: PiiModifier[]): string => {
		if (modifiers.length === 0) return '';

		// Create a hash based on modifier content, not just length
		// Sort by ID to ensure consistent ordering regardless of array order
		const sortedModifiers = [...modifiers].sort((a, b) => a.id.localeCompare(b.id));

		return sortedModifiers
			.map((m) => `${m.action}:${m.entity}:${m.type || ''}:${m.from}:${m.to}`)
			.join('|');
	};

	// PII Session Manager for conversation state
	let piiSessionManager = PiiSessionManager.getInstance();
	let previousConversationId: string | undefined = undefined;
	let conversationActivated = false; // Track if conversation has been activated

	// Handle PII detection state changes
	const handlePiiDetectionStateChanged = (isDetecting: boolean) => {
		isPiiDetectionInProgress = isDetecting;
		onPiiDetectionStateChanged(isDetecting);
	};

	const options = {
		throwOnError: false
	};

	// Ensure conversation is activated (load modifiers into working state)
	const ensureConversationActivated = () => {
		if (enablePiiDetection && enablePiiModifiers && conversationId && !conversationActivated) {
			// Set flag immediately to prevent multiple simultaneous calls
			conversationActivated = true;

			try {
				// Reload modifiers in the extension (only if editor exists and has the command)
				if (
					editor &&
					editor.commands &&
					typeof editor.commands.reloadConversationModifiers === 'function'
				) {
					editor.commands.reloadConversationModifiers(conversationId);
				}
			} catch (error) {
				console.error('RichTextInput: Error during conversation activation:', error);
				// Reset flag on error so it can be retried
				conversationActivated = false;
			}
		}
	};

	$: if (editor) {
		editor.setOptions({
			editable: editable
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
		// Initialize PII session manager (Backend-based)
		if (enablePiiDetection && piiApiKey) {
			piiSessionManager.setApiKey(piiApiKey);
		}

		// Add PII highlighting styles
		if (enablePiiDetection) {
			const styleElement = document.createElement('style');
			styleElement.textContent = createPiiHighlightStyles();
			document.head.appendChild(styleElement);
		}

		// Add PII modifier styles
		if (enablePiiModifiers && enablePiiDetection) {
			addPiiModifierStyles();
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
							PiiDetectionExtension.configure({
								enabled: true,
								apiKey: piiApiKey,
								conversationId: conversationId,
								onPiiDetected: onPiiDetected,
								onPiiToggled: onPiiToggled,
								onPiiDetectionStateChanged: handlePiiDetectionStateChanged
							})
						]
					: []),
				...(enablePiiModifiers && enablePiiDetection
					? [
							PiiModifierExtension.configure({
								enabled: true,
								conversationId: conversationId,
								onModifiersChanged: handleModifiersChanged,
								availableLabels: piiModifierLabels.length > 0 ? piiModifierLabels : undefined // Use default labels
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
						ensureConversationActivated(); // Ensure conversation is activated on focus
						eventDispatch('focus', { event });
						return false;
					},
					keyup: (view, event) => {
						eventDispatch('keyup', { event });

						// Force entity remapping on keyup for immediate highlight updates
						if (enablePiiDetection && editor && editor.commands.forceEntityRemapping) {
							setTimeout(() => {
								editor.commands.forceEntityRemapping();
							}, 10);
						}

						return false;
					},
					input: (view, event) => {
						// Force entity remapping on input for immediate highlight updates
						if (enablePiiDetection && editor && editor.commands.forceEntityRemapping) {
							setTimeout(() => {
								editor.commands.forceEntityRemapping();
							}, 10);
						}
						return false;
					},
					keydown: (view, event) => {
						ensureConversationActivated(); // Ensure conversation is activated on first keystroke

						// Handle CTRL+SHIFT+L to toggle PII masking (mask all <-> unmask all)
						if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'l') {
							if (enablePiiDetection && enablePiiModifiers && editor) {
								event.preventDefault();

								// Get current entities from PiiSessionManager to determine state
								const piiSessionManager = PiiSessionManager.getInstance();
								const currentEntities = piiSessionManager.getEntitiesForDisplay(conversationId);

								if (currentEntities.length > 0) {
									// Check if most entities are currently masked
									const maskedCount = currentEntities.filter(entity => entity.shouldMask).length;
									const unmaskedCount = currentEntities.length - maskedCount;
									const mostlyMasked = maskedCount >= unmaskedCount;

									if (mostlyMasked) {
										// Currently masked -> unmask all and clear mask modifiers
										// 1. Clear all mask modifiers (keep ignore modifiers)
										if (editor.commands?.clearMaskModifiers) {
											editor.commands.clearMaskModifiers();
										}

										// 2. Unmask all PII entities
										if (editor.commands?.unmaskAllEntities) {
											editor.commands.unmaskAllEntities();
										}
									} else {
										// Currently unmasked -> mask all entities
										if (editor.commands?.maskAllEntities) {
											editor.commands.maskAllEntities();
										}
									}
								}

								return true;
							}
						}

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
								const isCtrlPressed = event.ctrlKey || event.metaKey; // metaKey is for Cmd key on Mac
								if (event.shiftKey && !isCtrlPressed) {
									editor.commands.setHardBreak(); // Insert a hard break
									view.dispatch(view.state.tr.scrollIntoView()); // Move viewport to the cursor
									event.preventDefault();
									return true;
								} else {
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

	let currentModifiersHash = '';

	// Reactive statement to handle conversation ID changes and transfer global state
	$: if (conversationId !== previousConversationId && enablePiiDetection) {
		// Reset conversation activated flag when conversation changes
		conversationActivated = false;

		// Handle conversation ID transitions
		if (!previousConversationId && conversationId) {
			// Transition from no ID (new chat) to having ID (after first message sent)
			// The Chat.svelte component handles the temporary state transfer
			console.log('RichTextInput: Transition from new chat to existing chat:', conversationId);
		} else if (
			previousConversationId &&
			conversationId &&
			previousConversationId !== conversationId
		) {
			// Switch between existing conversations
			console.log(
				'RichTextInput: Switching between conversations:',
				previousConversationId,
				'→',
				conversationId
			);
			piiSessionManager.loadConversationState(conversationId);

			// Activate the new conversation and reload modifiers
			if (editor && enablePiiModifiers) {
				editor.commands.reloadConversationModifiers(conversationId);
				conversationActivated = true;
			}
		} else if (previousConversationId && !conversationId) {
			// Switch from existing conversation to new chat
			console.log('RichTextInput: Switching from existing chat to new chat');
			// The Chat.svelte component should have activated temporary state already
		}

		// Update extensions with new conversation ID
		if (editor && enablePiiDetection) {
			// Update PiiDetectionExtension
			if (editor.extensionManager.extensions.find((ext: any) => ext.name === 'piiDetection')) {
				if (editor.commands.reloadConversationState) {
					editor.commands.reloadConversationState(conversationId);
				}
			}

			// Sync with session manager to ensure consistency
			if (editor.commands.syncWithSessionManager) {
				setTimeout(() => {
					editor.commands.syncWithSessionManager();
				}, 100);
			}
		}

		previousConversationId = conversationId;
	}

	// Reactive statement to trigger PII detection when modifiers change
	$: if (editor && editor.view && enablePiiDetection && enablePiiModifiers) {
		const newHash = getModifiersHash(currentModifiers);
		if (newHash !== currentModifiersHash && newHash !== '') {
			currentModifiersHash = newHash;
			editor.commands.triggerDetectionForModifiers();

			// Also sync with session manager after modifier changes
			setTimeout(() => {
				if (editor.commands.syncWithSessionManager) {
					editor.commands.syncWithSessionManager();
				}
			}, 200);
		}
	}

	// Handle modifier changes
	const handleModifiersChanged = (modifiers: PiiModifier[]) => {
		const oldHash = getModifiersHash(currentModifiers);
		const newHash = getModifiersHash(modifiers);

		currentModifiers = modifiers;
		onPiiModifiersChanged(modifiers);

		// Use content-based comparison for more reliable change detection
		if (newHash !== oldHash) {
			// Update the tracking hash
			currentModifiersHash = newHash;

			// Trigger detection if we have an editor and text
			if (editor && editor.view && editor.view.state.doc.textContent.trim()) {
				setTimeout(() => {
					editor.commands.triggerDetectionForModifiers();

					// Sync with session manager after modifier changes
					if (editor.commands.syncWithSessionManager) {
						setTimeout(() => {
							editor.commands.syncWithSessionManager();
						}, 100);
					}
				}, 100);
			}
		}
	};

	// Periodic sync with session manager to handle external entity changes
	let syncInterval: NodeJS.Timeout | null = null;

	$: if (editor && enablePiiDetection && conversationActivated) {
		// Clear any existing interval
		if (syncInterval) {
			clearInterval(syncInterval);
		}

		// Set up periodic sync every 2 seconds when editor is active
		syncInterval = setInterval(() => {
			if (editor && editor.commands.syncWithSessionManager && document.hasFocus()) {
				editor.commands.syncWithSessionManager();
			}
		}, 2000);
	}

	// Cleanup sync interval
	onDestroy(() => {
		if (editor) {
			editor.destroy();
		}
		if (syncInterval) {
			clearInterval(syncInterval);
		}
	});
</script>

<div class="relative w-full min-w-full h-full min-h-fit {className}">
	<div bind:this={element} class="w-full h-full min-h-fit" />

	<!-- PII Detection Loading Indicator -->
	{#if enablePiiDetection && isPiiDetectionInProgress}
		<div
			class="absolute top-2 right-2 flex items-center gap-1 bg-gray-50 dark:bg-gray-850 px-2 py-1 rounded-md shadow-sm border border-gray-200 dark:border-gray-700"
		>
			<Spinner className="size-3" />
			<span class="text-xs text-gray-600 dark:text-gray-400">Scanning for PII...</span>
		</div>
	{/if}
</div>
