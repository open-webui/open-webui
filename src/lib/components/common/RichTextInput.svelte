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

	turndownService.addRule('taskListItems', {
		filter: (node) =>
			node.nodeName === 'LI' &&
			(node.getAttribute('data-checked') === 'true' ||
				node.getAttribute('data-checked') === 'false'),
		replacement: function (content, node) {
			const checked = node.getAttribute('data-checked') === 'true';
			content = content.replace(/^\s+/, '');
			return `- [${checked ? 'x' : ' '}] ${content}\n`;
		}
	});

	import { onMount, onDestroy, tick } from 'svelte';
	import { createEventDispatcher } from 'svelte';

	const eventDispatch = createEventDispatcher();

	import { Fragment, DOMParser } from 'prosemirror-model';
	import { EditorState, Plugin, PluginKey, TextSelection, Selection } from 'prosemirror-state';
	import { Decoration, DecorationSet } from 'prosemirror-view';
	import { Editor } from '@tiptap/core';

	import { AIAutocompletion } from './RichTextInput/AutoCompletion.js';
	import Table from '@tiptap/extension-table';
	import TableRow from '@tiptap/extension-table-row';
	import TableHeader from '@tiptap/extension-table-header';
	import TableCell from '@tiptap/extension-table-cell';

	import TaskItem from '@tiptap/extension-task-item';
	import TaskList from '@tiptap/extension-task-list';

	import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
	import Placeholder from '@tiptap/extension-placeholder';
	import StarterKit from '@tiptap/starter-kit';
	import Highlight from '@tiptap/extension-highlight';
	import Typography from '@tiptap/extension-typography';
	import { all, createLowlight } from 'lowlight';

	import { PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';

	export let oncompositionstart = (e) => {};
	export let oncompositionend = (e) => {};
	export let onChange = (e) => {};

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
	export let insertPromptAsRichText = false;

	let element;
	let editor;

	const options = {
		throwOnError: false
	};

	$: if (editor) {
		editor.setOptions({
			editable: editable
		});
	}

	$: if (value === null && html !== null && editor) {
		editor.commands.setContent(html);
	}

	export const getWordAtDocPos = () => {
		if (!editor) return '';
		const { state } = editor.view;
		const pos = state.selection.from;
		const doc = state.doc;
		const resolvedPos = doc.resolve(pos);
		const textBlock = resolvedPos.parent;
		const paraStart = resolvedPos.start();
		const text = textBlock.textContent;
		const offset = resolvedPos.parentOffset;

		let wordStart = offset,
			wordEnd = offset;
		while (wordStart > 0 && !/\s/.test(text[wordStart - 1])) wordStart--;
		while (wordEnd < text.length && !/\s/.test(text[wordEnd])) wordEnd++;

		const word = text.slice(wordStart, wordEnd);

		return word;
	};

	// Returns {start, end} of the word at pos
	function getWordBoundsAtPos(doc, pos) {
		const resolvedPos = doc.resolve(pos);
		const textBlock = resolvedPos.parent;
		const paraStart = resolvedPos.start();
		const text = textBlock.textContent;

		const offset = resolvedPos.parentOffset;
		let wordStart = offset,
			wordEnd = offset;
		while (wordStart > 0 && !/\s/.test(text[wordStart - 1])) wordStart--;
		while (wordEnd < text.length && !/\s/.test(text[wordEnd])) wordEnd++;
		return {
			start: paraStart + wordStart,
			end: paraStart + wordEnd
		};
	}

	export const replaceCommandWithText = async (text) => {
		const { state, dispatch } = editor.view;
		const { selection } = state;
		const pos = selection.from;

		// Get the plain text of this document
		// const docText = state.doc.textBetween(0, state.doc.content.size, '\n', '\n');

		// Find the word boundaries at cursor
		const { start, end } = getWordBoundsAtPos(state.doc, pos);

		let tr = state.tr;

		if (insertPromptAsRichText) {
			const htmlContent = marked
				.parse(text, {
					breaks: true,
					gfm: true
				})
				.trim();

			// Create a temporary div to parse HTML
			const tempDiv = document.createElement('div');
			tempDiv.innerHTML = htmlContent;

			// Convert HTML to ProseMirror nodes
			const fragment = DOMParser.fromSchema(state.schema).parse(tempDiv);

			// Extract just the content, not the wrapper paragraphs
			const content = fragment.content;
			let nodesToInsert = [];

			content.forEach((node) => {
				if (node.type.name === 'paragraph') {
					// If it's a paragraph, extract its content
					nodesToInsert.push(...node.content.content);
				} else {
					nodesToInsert.push(node);
				}
			});

			tr = tr.replaceWith(start, end, nodesToInsert);
			// Calculate new position
			const newPos = start + nodesToInsert.reduce((sum, node) => sum + node.nodeSize, 0);
			tr = tr.setSelection(Selection.near(tr.doc.resolve(newPos)));
		} else {
			if (text.includes('\n')) {
				// Split the text into lines and create a <p> node for each line
				const lines = text.split('\n');
				const nodes = lines.map(
					(line, index) =>
						index === 0
							? state.schema.text(line ? line : []) // First line is plain text
							: state.schema.nodes.paragraph.create({}, line ? state.schema.text(line) : undefined) // Subsequent lines are paragraphs
				);

				// Build and dispatch the transaction to replace the word at cursor
				tr = tr.replaceWith(start, end, nodes);

				let newSelectionPos;

				// +1 because the insert happens at start, so last para starts at (start + sum of all previous nodes' sizes)
				let lastPos = start;
				for (let i = 0; i < nodes.length; i++) {
					lastPos += nodes[i].nodeSize;
				}
				// Place cursor inside the last paragraph at its end
				newSelectionPos = lastPos;

				tr = tr.setSelection(TextSelection.near(tr.doc.resolve(newSelectionPos)));
			} else {
				tr = tr.replaceWith(
					start,
					end, // replace this range
					text !== '' ? state.schema.text(text) : []
				);

				tr = tr.setSelection(
					state.selection.constructor.near(tr.doc.resolve(start + text.length + 1))
				);
			}
		}

		dispatch(tr);

		await tick();
		// selectNextTemplate(state, dispatch);
	};

	export const setText = (text: string) => {
		if (!editor) return;
		text = text.replaceAll('\n\n', '\n');
		const { state, view } = editor;
		const { schema, tr } = state;

		if (text.includes('\n')) {
			// Multiple lines: make paragraphs
			const lines = text.split('\n');
			// Map each line to a paragraph node (empty lines -> empty paragraph)
			const nodes = lines.map((line) =>
				schema.nodes.paragraph.create({}, line ? schema.text(line) : undefined)
			);
			// Create a document fragment containing all parsed paragraphs
			const fragment = Fragment.fromArray(nodes);
			// Replace current selection with these paragraphs
			tr.replaceSelectionWith(fragment, false /* don't select new */);
			view.dispatch(tr);
		} else if (text === '') {
			// Empty: replace with empty paragraph using tr
			editor.commands.clearContent();
		} else {
			// Single line: create paragraph with text
			const paragraph = schema.nodes.paragraph.create({}, schema.text(text));
			tr.replaceSelectionWith(paragraph, false);
			view.dispatch(tr);
		}

		selectNextTemplate(editor.view.state, editor.view.dispatch);
		focus();
	};

	export const insertContent = (content) => {
		if (!editor) return;
		const { state, view } = editor;
		const { schema, tr } = state;

		// If content is a string, convert it to a ProseMirror node
		const htmlContent = marked.parse(content, {
			breaks: true,
			gfm: true
		});

		// insert the HTML content at the current selection
		editor.commands.insertContent(htmlContent);

		focus();
	};

	export const replaceVariables = (variables) => {
		if (!editor) return;
		const { state, view } = editor;
		const { doc } = state;

		// Create a transaction to replace variables
		let tr = state.tr;
		let offset = 0; // Track position changes due to text length differences

		// Collect all replacements first to avoid position conflicts
		const replacements = [];

		doc.descendants((node, pos) => {
			if (node.isText && node.text) {
				const text = node.text;
				const replacedText = text.replace(/{{\s*([^|}]+)(?:\|[^}]*)?\s*}}/g, (match, varName) => {
					const trimmedVarName = varName.trim();
					return variables.hasOwnProperty(trimmedVarName)
						? String(variables[trimmedVarName])
						: match;
				});

				if (replacedText !== text) {
					replacements.push({
						from: pos,
						to: pos + text.length,
						text: replacedText
					});
				}
			}
		});

		// Apply replacements in reverse order to maintain correct positions
		replacements.reverse().forEach(({ from, to, text }) => {
			tr = tr.replaceWith(from, to, text !== '' ? state.schema.text(text) : []);
		});

		// Only dispatch if there are changes
		if (replacements.length > 0) {
			view.dispatch(tr);
		}
	};

	export const focus = () => {
		if (editor) {
			editor.view.focus();
			// Scroll to the current selection
			editor.view.dispatch(editor.view.state.tr.scrollIntoView());
		}
	};

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

				// Scroll to the selected template
				dispatch(
					tr.scrollIntoView().setMeta('preventScroll', true) // Prevent default scrolling behavior
				);
			}
			return true;
		}
		return false;
	}

	export const setContent = (content) => {
		editor.commands.setContent(content);
	};

	const selectTemplate = () => {
		if (value !== '') {
			// After updating the state, try to find and select the next template
			setTimeout(() => {
				const templateFound = selectNextTemplate(editor.view.state, editor.view.dispatch);
				if (!templateFound) {
					editor.commands.focus('end');
				}
			}, 0);
		}
	};

	onMount(async () => {
		let content = value;

		if (json) {
			if (!content) {
				content = html ? html : null;
			}
		} else {
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
				Table.configure({ resizable: true }),
				TableRow,
				TableHeader,
				TableCell,
				TaskList,
				TaskItem.configure({
					nested: true
				}),
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

				const htmlValue = editor.getHTML();
				const jsonValue = editor.getJSON();

				let mdValue = turndownService
					.turndown(
						htmlValue
							.replace(/<p><\/p>/g, '<br/>')
							.replace(/ {2,}/g, (m) => m.replace(/ /g, '\u00a0'))
					)
					.replace(/\u00a0/g, ' ');

				onChange({
					html: htmlValue,
					json: jsonValue,
					md: mdValue
				});

				if (json) {
					value = jsonValue;
				} else {
					if (raw) {
						value = htmlValue;
					} else {
						if (!preserveBreaks) {
							mdValue = mdValue.replace(/<br\/>/g, '');
						}

						if (value !== mdValue) {
							value = mdValue;

							// check if the node is paragraph as well
							if (editor.isActive('paragraph')) {
								if (value === '') {
									editor.commands.clearContent();
								}
							}
						}
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
								const isCtrlPressed = event.ctrlKey || event.metaKey; // metaKey is for Cmd key on Mac
								if (event.shiftKey && !isCtrlPressed) {
									editor.commands.enter(); // Insert a new line
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
									const isInList = isInside(['listItem', 'bulletList', 'orderedList', 'taskList']);
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
							const plainText = event.clipboardData.getData('text/plain');
							if (plainText) {
								if (largeTextAsFile && plainText.length > PASTED_TEXT_CHARACTER_LIMIT) {
									// Delegate handling of large text pastes to the parent component.
									eventDispatch('paste', { event });
									event.preventDefault();
									return true;
								}

								// Workaround for mobile WebViews that strip line breaks when pasting from
								// clipboard suggestions (e.g., Gboard clipboard history).
								const isMobile = /Android|iPhone|iPad|iPod|Windows Phone/i.test(
									navigator.userAgent
								);
								const isWebView =
									typeof window !== 'undefined' &&
									(/wv/i.test(navigator.userAgent) || // Standard Android WebView flag
										(navigator.userAgent.includes('Android') &&
											!navigator.userAgent.includes('Chrome')) || // Other generic Android WebViews
										(navigator.userAgent.includes('Safari') &&
											!navigator.userAgent.includes('Version'))); // iOS WebView (in-app browsers)

								if (isMobile && isWebView && plainText.includes('\n')) {
									// Manually deconstruct the pasted text and insert it with hard breaks
									// to preserve the multi-line formatting.
									const { state, dispatch } = view;
									const { from, to } = state.selection;

									const lines = plainText.split('\n');
									const nodes = [];

									lines.forEach((line, index) => {
										if (index > 0) {
											nodes.push(state.schema.nodes.hardBreak.create());
										}
										if (line.length > 0) {
											nodes.push(state.schema.text(line));
										}
									});

									const fragment = Fragment.fromArray(nodes);
									const tr = state.tr.replaceWith(from, to, fragment);
									dispatch(tr.scrollIntoView());
									event.preventDefault();
									return true;
								}
								// Let ProseMirror handle normal text paste in non-problematic environments.
								return false;
							}

							// Delegate image paste handling to the parent component.
							const hasImageFile = Array.from(event.clipboardData.files).some((file) =>
								file.type.startsWith('image/')
							);
							// Fallback for cases where an image is in dataTransfer.items but not clipboardData.files.
							const hasImageItem = Array.from(event.clipboardData.items).some((item) =>
								item.type.startsWith('image/')
							);
							if (hasImageFile || hasImageItem) {
								eventDispatch('paste', { event });
								event.preventDefault();
								return true;
							}
						}
						// For all other cases, let ProseMirror perform its default paste behavior.
						view.dispatch(view.state.tr.scrollIntoView());
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

		const jsonValue = editor.getJSON();
		const htmlValue = editor.getHTML();
		let mdValue = turndownService
			.turndown(
				(preserveBreaks ? htmlValue.replace(/<p><\/p>/g, '<br/>') : htmlValue).replace(
					/ {2,}/g,
					(m) => m.replace(/ /g, '\u00a0')
				)
			)
			.replace(/\u00a0/g, ' ');

		if (value === '') {
			editor.commands.clearContent(); // Clear content if value is empty
			selectTemplate();

			return;
		}

		if (json) {
			if (JSON.stringify(value) !== JSON.stringify(jsonValue)) {
				editor.commands.setContent(value);
				selectTemplate();
			}
		} else {
			if (raw) {
				if (value !== htmlValue) {
					editor.commands.setContent(value);
					selectTemplate();
				}
			} else {
				if (value !== mdValue) {
					editor.commands.setContent(
						preserveBreaks
							? value
							: marked.parse(value.replaceAll(`\n<br/>`, `<br/>`), {
									breaks: false
								})
					);

					selectTemplate();
				}
			}
		}
	};
</script>

<div bind:this={element} class="relative w-full min-w-full h-full min-h-fit {className}" />
