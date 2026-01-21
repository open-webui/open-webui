<script lang="ts">
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';

	marked.use({
		breaks: true,
		gfm: true,
		renderer: {
			list(body, ordered, start) {
				const isTaskList = body.includes('data-checked=');

				if (isTaskList) {
					return `<ul data-type="taskList">${body}</ul>`;
				}

				const type = ordered ? 'ol' : 'ul';
				const startatt = ordered && start !== 1 ? ` start="${start}"` : '';
				return `<${type}${startatt}>${body}</${type}>`;
			},

			listitem(text, task, checked) {
				if (task) {
					const checkedAttr = checked ? 'true' : 'false';
					return `<li data-type="taskItem" data-checked="${checkedAttr}">${text}</li>`;
				}
				return `<li>${text}</li>`;
			}
		}
	});

	import TurndownService from 'turndown';
	import { gfm } from '@joplin/turndown-plugin-gfm';
	const turndownService = new TurndownService({
		codeBlockStyle: 'fenced',
		headingStyle: 'atx'
	});
	turndownService.escape = (string: string) => string;

	// Use turndown-plugin-gfm for proper GFM table support
	turndownService.use(gfm);

	// Add custom table header rule before using GFM plugin
	turndownService.addRule('tableHeaders', {
		filter: 'th',
		replacement: function (content: string, node: HTMLElement) {
			return content;
		}
	});

	// Add custom table rule to handle headers properly
	turndownService.addRule('tables', {
		filter: 'table',
		replacement: function (content: string, node: HTMLElement) {
			// Extract rows
			const rows = Array.from(node.querySelectorAll('tr'));
			if (rows.length === 0) return content;

			let markdown = '\n';

			rows.forEach((row: Element, rowIndex: number) => {
				const cells = Array.from(row.querySelectorAll('th, td'));
				const cellContents = cells.map((cell: Element) => {
					// Get the text content and clean it up
					let cellContent = turndownService.turndown((cell as HTMLElement).innerHTML).trim();
					// Remove extra paragraph tags that might be added
					cellContent = cellContent.replace(/^\n+|\n+$/g, '');
					return cellContent;
				});

				// Add the row
				markdown += '| ' + cellContents.join(' | ') + ' |\n';

				// Add separator after first row (which should be headers)
				if (rowIndex === 0) {
					const separator = cells.map(() => '---').join(' | ');
					markdown += '| ' + separator + ' |\n';
				}
			});

			return markdown + '\n';
		}
	});

	turndownService.addRule('taskListItems', {
		filter: (node: HTMLElement) =>
			node.nodeName === 'LI' &&
			(node.getAttribute('data-checked') === 'true' ||
				node.getAttribute('data-checked') === 'false'),
		replacement: function (content: string, node: HTMLElement) {
			const checked = node.getAttribute('data-checked') === 'true';
			content = content.replace(/^\s+/, '');
			return `- [${checked ? 'x' : ' '}] ${content}\n`;
		}
	});

	// Convert TipTap mention spans -> <@id>
	turndownService.addRule('mentions', {
		filter: (node: HTMLElement) => node.nodeName === 'SPAN' && node.getAttribute('data-type') === 'mention',
		replacement: (_content: string, node: HTMLElement) => {
			const id = node.getAttribute('data-id') || '';
			// TipTap stores the trigger char in data-mention-suggestion-char (usually "@")
			const ch = node.getAttribute('data-mention-suggestion-char') || '@';
			// Emit <@id> style, e.g. <@llama3.2:latest>
			return `<${ch}${id}>`;
		}
	});

	import { onMount, onDestroy, tick, getContext } from 'svelte';
	import { createEventDispatcher } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	const i18n: Writable<i18nType> = getContext('i18n');
	const eventDispatch = createEventDispatcher();

	import { Fragment, DOMParser } from 'prosemirror-model';
	import { EditorState, Plugin, PluginKey, TextSelection, Selection } from 'prosemirror-state';
	import { Decoration, DecorationSet } from 'prosemirror-view';
	import { Editor, Extension, mergeAttributes } from '@tiptap/core';

	import { AIAutocompletion } from './RichTextInput/AutoCompletion';

	import StarterKit from '@tiptap/starter-kit';

	// Bubble and Floating menus are currently fixed to v2 due to styling issues in v3
	// TODO: Update to v3 when styling issues are resolved
	import BubbleMenu from '@tiptap/extension-bubble-menu';
	import FloatingMenu from '@tiptap/extension-floating-menu';

	import { TableKit } from '@tiptap/extension-table';
	import { ListKit } from '@tiptap/extension-list';
	import { Placeholder, CharacterCount } from '@tiptap/extensions';

	import Image from './RichTextInput/Image/index.js';
	// import TiptapImage from '@tiptap/extension-image';

	import FileHandler from '@tiptap/extension-file-handler';
	import Typography from '@tiptap/extension-typography';
	import Highlight from '@tiptap/extension-highlight';
	import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';

	import Mention from '@tiptap/extension-mention';
	import FormattingButtons from './RichTextInput/FormattingButtons.svelte';

	import { PASTED_TEXT_CHARACTER_LIMIT } from '$lib/constants';
	import { createLowlight } from 'lowlight';
	import hljs from 'highlight.js';

	import type { SocketIOCollaborationProvider } from './RichTextInput/Collaboration';

	export let oncompositionstart = (e: CompositionEvent) => {};
	export let oncompositionend = (e: CompositionEvent) => {};
	export let onChange = (e: { html: string; json: object; md: string }) => {};

	// create a lowlight instance with all languages loaded
	const lowlight = createLowlight(
		hljs.listLanguages().reduce(
			(obj, lang) => {
				obj[lang] = () => hljs.getLanguage(lang);
				return obj;
			},
			{} as Record<string, any>
		)
	);

	export let editor: Editor | null = null;

	export let socket = null;
	export let user = null;
	export let files: File[] = [];

	export let documentId = '';

	export let className = 'input-prose min-h-fit h-full';
	export let placeholder = $i18n.t('Type here...');
	let _placeholder = placeholder;

	$: if (placeholder !== _placeholder) {
		setPlaceholder();
	}

	const setPlaceholder = () => {
		_placeholder = placeholder;
		if (editor) {
			editor?.view.dispatch(editor.state.tr);
		}
	};

	export let richText = true;
	export let dragHandle = false;
	export let link = false;
	export let image = false;
	export let fileHandler = false;
	export let suggestions = null;

	export let onFileDrop = (currentEditor: Editor, files: File[], pos: number) => {
		files.forEach((file: File) => {
			const fileReader = new FileReader();

			fileReader.readAsDataURL(file);
			fileReader.onload = () => {
				currentEditor
					.chain()
					.insertContentAt(pos, {
						type: 'image',
						attrs: {
							src: fileReader.result
						}
					})
					.focus()
					.run();
			};
		});
	};

	export let onFilePaste = (currentEditor: Editor, files: File[], htmlContent?: string) => {
		files.forEach((file: File) => {
			if (htmlContent) {
				// if there is htmlContent, stop manual insertion & let other extensions handle insertion via inputRule
				// you could extract the pasted file from this url string and upload it to a server for example
				console.log(htmlContent); // eslint-disable-line no-console
				return false;
			}

			const fileReader = new FileReader();

			fileReader.readAsDataURL(file);
			fileReader.onload = () => {
				currentEditor
					.chain()
					.insertContentAt(currentEditor.state.selection.anchor, {
						type: 'image',
						attrs: {
							src: fileReader.result
						}
					})
					.focus()
					.run();
			};
		});
	};

	export let onSelectionUpdate = (_e: { editor: Editor }) => {};

	export let id = '';
	export let value = '';
	export let html = '';

	export let json = false;
	export let raw = false;
	export let editable = true;
	export let collaboration = false;

	export let showFormattingToolbar = true;

	export let preserveBreaks = false;
	export let generateAutoCompletion: Function = async () => null;
	export let autocomplete = false;
	export let messageInput = false;
	export let shiftEnter = false;
	export let largeTextAsFile = false;
	export let insertPromptAsRichText = false;
	export let floatingMenuPlacement = 'bottom-start';

	let content = null;
	let htmlValue = '';
	let jsonValue: any = '';
	let mdValue = '';

	let provider: SocketIOCollaborationProvider | null = null;

	let floatingMenuElement: Element | null = null;
	let bubbleMenuElement: Element | null = null;
	let element: Element | null = null;

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
	function getWordBoundsAtPos(doc: any, pos: number) {
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

	export const replaceCommandWithText = async (text: string) => {
		if (!editor) return;
		const { state, dispatch } = editor.view;
		const { selection } = state;
		const pos = selection.from;

		// Get the plain text of this document
		// const docText = state.doc.textBetween(0, state.doc.content.size, '\n', '\n');

		// Find the word boundaries at cursor
		const { start, end } = getWordBoundsAtPos(state.doc, pos);

		let tr = state.tr;

		if (insertPromptAsRichText) {
			const htmlContent = DOMPurify.sanitize(
				marked
					.parse(text, {
						breaks: true,
						gfm: true
					})
					.trim()
			);

			// Create a temporary div to parse HTML
			const tempDiv = document.createElement('div');
			tempDiv.innerHTML = htmlContent;

			// Convert HTML to ProseMirror nodes
			const fragment = DOMParser.fromSchema(state.schema).parse(tempDiv);

			// Extract just the content, not the wrapper paragraphs
			const content = fragment.content;
			const nodesToInsert: any[] = [];

			content.forEach((node: any) => {
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
				const nodes: any[] = lines.map(
					(line: string, index: number) =>
						index === 0
							? state.schema.text(line || '') // First line is plain text
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
					(TextSelection as any).near(tr.doc.resolve(start + text.length + 1))
				);
			}
		}

		dispatch(tr);

		await tick();
		// selectNextTemplate(state, dispatch);
	};

	export const setText = (text: string) => {
		if (!editor || !editor.view) return;
		text = text.replaceAll('\n\n', '\n');

		// reset the editor content
		editor.commands.clearContent();

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
			tr.replaceSelectionWith(fragment as any, false /* don't select new */);
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

		// Ensure the editor is still valid before trying to focus
		focus();
	};

	export const insertContent = (content: string) => {
		if (!editor || !editor.view) return;

		// If content is a string, convert it to a ProseMirror node
		const htmlContent = marked.parse(content);

		// insert the HTML content at the current selection
		editor.commands.insertContent(htmlContent);

		focus();
	};

	export const replaceVariables = (variables: Record<string, any>) => {
		if (!editor || !editor.view) return;
		const { state, view } = editor;
		const { doc } = state;

		// Create a transaction to replace variables
		let tr = state.tr;

		// Collect all replacements first to avoid position conflicts
		const replacements: { from: number; to: number; text: string }[] = [];

		doc.descendants((node: any, pos: number) => {
			if (node.isText && node.text) {
				const text = node.text;
				const replacedText = text.replace(/{{\s*([^|}]+)(?:\|[^}]*)?\s*}}/g, (match: string, varName: string) => {
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
		if (editor && editor.view) {
			// Check if the editor is destroyed
			if (editor.isDestroyed) {
				return;
			}

			try {
				editor.view.focus();
				// Scroll to the current selection
				editor.view.dispatch(editor.view.state.tr.scrollIntoView());
			} catch (e) {
				// sometimes focusing throws an error, ignore
				console.warn('Error focusing editor', e);
			}
		}
	};

	// Function to find the next template in the document
	function findNextTemplate(doc: any, from = 0): { from: number; to: number } | null {
		const patterns = [{ start: '{{', end: '}}' }];

		let result: { from: number; to: number } | null = null;

		doc.nodesBetween(from, doc.content.size, (node: any, pos: number) => {
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
	function selectNextTemplate(state: any, dispatch: any) {
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

	export const setContent = (content: string) => {
		if (!editor) return;
		editor.commands.setContent(content);
	};

	const selectTemplate = () => {
		if (value !== '' && editor) {
			// After updating the state, try to find and select the next template
			setTimeout(() => {
				if (!editor) return;
				const templateFound = selectNextTemplate(editor.view.state, editor.view.dispatch);
				if (!templateFound) {
					editor.commands.focus('end');
				}
			}, 0);
		}
	};

	const SelectionDecoration = Extension.create({
		name: 'selectionDecoration',
		addProseMirrorPlugins() {
			return [
				new Plugin({
					key: new PluginKey('selection'),
					props: {
						decorations: (state) => {
							const { selection } = state;
							const focused = (this.editor as any).isFocused;

							if (focused || selection.empty) {
								return null;
							}

							return DecorationSet.create(state.doc, [
								Decoration.inline(selection.from, selection.to, {
									class: 'editor-selection'
								})
							]);
						}
					}
				})
			];
		}
	});

	import { listDragHandlePlugin } from './RichTextInput/listDragHandlePlugin';

	const ListItemDragHandle = Extension.create({
		name: 'listItemDragHandle',
		addProseMirrorPlugins() {
			return [
				listDragHandlePlugin({
					itemTypeNames: ['listItem', 'taskItem'],
					getEditor: () => this.editor
				})
			];
		}
	});

	onMount(async () => {
		content = value;

		if (json) {
			if (!content) {
				content = html ? html : null;
			}
		} else {
			if (preserveBreaks) {
				turndownService.addRule('preserveBreaks', {
					filter: 'br', // Target <br> elements
					replacement: function (_content: string) {
						return '<br/>';
					}
				});
			}

			if (!raw) {
				async function tryParse(value: string, attempts = 3, interval = 100): Promise<string> {
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

		if (collaboration && documentId && socket && user) {
			const { SocketIOCollaborationProvider } = await import('./RichTextInput/Collaboration');
			provider = new SocketIOCollaborationProvider(documentId, socket, user, content);
		}
		editor = new Editor({
			element: element,
			extensions: [
				StarterKit.configure({
					link: link ? {} : false
				}),
				...(dragHandle ? [ListItemDragHandle] : []),
				Placeholder.configure({ placeholder: () => _placeholder, showOnlyWhenEditable: false }),
				SelectionDecoration,

				...(richText
					? [
							CodeBlockLowlight.configure({
								lowlight
							}),
							Typography,
							TableKit.configure({
								table: { resizable: true }
							}),
							ListKit.configure({
								taskItem: {
									nested: true
								}
							})
						]
					: []),
				...(suggestions
					? [
							Mention.configure({
								HTMLAttributes: { class: 'mention' },
								suggestions: suggestions
							})
						]
					: []),

				CharacterCount.configure({}),
				...(image ? [Image] : []),
				...(fileHandler
					? [
							FileHandler.configure({
								onDrop: onFileDrop,
								onPaste: onFilePaste
							})
						]
					: []),
				...(autocomplete
					? [
							AIAutocompletion.configure({
								generateCompletion: async (text: string) => {
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
					: []),
				...(richText && showFormattingToolbar
					? [
							BubbleMenu.configure({
								element: bubbleMenuElement as HTMLElement,
								tippyOptions: {
									duration: 100,
									arrow: false,
									placement: 'top',
									theme: 'transparent',
									offset: [0, 2]
								},
								shouldShow: ({ editor, from, to }: { editor: any; from: number; to: number }) => {
									// safety check
									if (!editor || !editor.view || editor.isDestroyed) {
										return false;
									}
									// default logic
									return from !== to;
								}
							} as any),
							FloatingMenu.configure({
								element: floatingMenuElement as HTMLElement,
								tippyOptions: {
									duration: 100,
									arrow: false,
									placement: floatingMenuPlacement,
									theme: 'transparent',
									offset: [-12, 4]
								},
								shouldShow: ({ editor }: { editor: any }) => {
									// safety check
									if (!editor || !editor.view || editor.isDestroyed) {
										return false;
									}
									// default logic
									return editor.isActive('paragraph');
								}
							} as any)
						]
					: []),
				...(collaboration && provider ? [provider.getEditorExtension()] : [])
			],
			content: collaboration ? undefined : content,
			autofocus: messageInput ? true : false,
			onTransaction: () => {
				// force re-render so `editor.isActive` works as expected
				editor = editor;
				if (!editor) return;

				htmlValue = editor.getHTML();
				jsonValue = editor.getJSON() as any;

				if (richText) {
					mdValue = turndownService
						.turndown(
							htmlValue
								.replace(/<p><\/p>/g, '<br/>')
								.replace(/ {2,}/g, (m) => m.replace(/ /g, '\u00a0'))
						)
						.replace(/\u00a0/g, ' ');
				} else {
					mdValue = turndownService
						.turndown(
							htmlValue
								// Replace empty paragraphs with line breaks
								.replace(/<p><\/p>/g, '<br/>')
								// Replace multiple spaces with non-breaking spaces
								.replace(/ {2,}/g, (m) => m.replace(/ /g, '\u00a0'))
								// Replace tabs with non-breaking spaces (preserve indentation)
								.replace(/\t/g, '\u00a0\u00a0\u00a0\u00a0') // 1 tab = 4 spaces
						)
						// Convert non-breaking spaces back to regular spaces for markdown
						.replace(/\u00a0/g, ' ');
				}

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
				handlePaste: (view, event) => {
					// Force plain-text pasting when richText === false
					if (!richText) {
						// swallow HTML completely
						event.preventDefault();
						const { state, dispatch } = view;

						const plainText = (event.clipboardData?.getData('text/plain') ?? '').replace(
							/\r\n/g,
							'\n'
						);

						const lines = plainText.split('\n');
						const nodes: any[] = [];

						lines.forEach((line: string, index: number) => {
							if (index > 0) {
								nodes.push(state.schema.nodes.hardBreak.create());
							}
							if (line.length > 0) {
								nodes.push(state.schema.text(line));
							}
						});

						const fragment = Fragment.fromArray(nodes);
						dispatch(state.tr.replaceSelectionWith(fragment as any, false).scrollIntoView());

						return true; // handled
					}

					return false;
				},
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

							// Handle Tab Key
							if (event.key === 'Tab') {
								const isInCodeBlock = isInside(['codeBlock']);

								if (isInCodeBlock) {
									// Handle tab in code block - insert tab character or spaces
									const tabChar = '\t'; // or '    ' for 4 spaces
									editor?.commands.insertContent(tabChar);
									event.preventDefault();
									return true; // Prevent further propagation
								} else {
									const handled = selectNextTemplate(view.state, view.dispatch);
									if (handled) {
										event.preventDefault();
										return true;
									}
								}
							}

							if (event.key === 'Enter') {
								const isCtrlPressed = event.ctrlKey || event.metaKey; // metaKey is for Cmd key on Mac

								const { state } = view;
								const { $from } = state.selection;
								const lineStart = $from.before($from.depth);
								const lineEnd = $from.after($from.depth);
								const lineText = state.doc.textBetween(lineStart, lineEnd, '\n', '\0').trim();
								if (event.shiftKey && !isCtrlPressed) {
									if (lineText.startsWith('```')) {
										// Fix GitHub issue #16337: prevent backtick removal for lines starting with ```
										return false; // Let ProseMirror handle the Enter key normally
									}

									editor?.commands.enter(); // Insert a new line
									view.dispatch(view.state.tr.scrollIntoView()); // Move viewport to the cursor
									event.preventDefault();
									return true;
								} else {
									const isInCodeBlock = isInside(['codeBlock']);
									const isInList = isInside(['listItem', 'bulletList', 'orderedList', 'taskList']);
									const isInHeading = isInside(['heading']);

									console.log({ isInCodeBlock, isInList, isInHeading });

									if (isInCodeBlock || isInList || isInHeading) {
										// Let ProseMirror handle the normal Enter behavior
										return false;
									}

									const suggestionsElement = document.getElementById('suggestions-container');
									if (lineText.startsWith('#') && suggestionsElement) {
										console.log('Letting heading suggestion handle Enter key');
										return true;
									}
								}
							}

							// Handle shift + Enter for a line break
							if (shiftEnter) {
								if (event.key === 'Enter' && event.shiftKey && !event.ctrlKey && !event.metaKey) {
									editor?.commands.setHardBreak(); // Insert a hard break
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
									const nodes: any[] = [];

									lines.forEach((line: string, index: number) => {
										if (index > 0) {
											nodes.push(state.schema.nodes.hardBreak.create());
										}
										if (line.length > 0) {
											nodes.push(state.schema.text(line));
										}
									});

									const fragment = Fragment.fromArray(nodes);
									const tr = state.tr.replaceWith(from, to, fragment as any);
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

							const hasFile = Array.from(event.clipboardData.files).length > 0;

							if (hasImageFile || hasImageItem || hasFile) {
								eventDispatch('paste', { event });
								event.preventDefault();
								return true;
							}
						}
						// For all other cases, let ProseMirror perform its default paste behavior.
						view.dispatch(view.state.tr.scrollIntoView());
						return false;
					},
					copy: (view, event: ClipboardEvent) => {
						if (!event.clipboardData) return false;
						if (richText) return false; // Let ProseMirror handle normal copy in rich text mode

						const { state } = view;
						const { from, to } = state.selection;

						// Only take the selected text & HTML, not the full doc
						const plain = state.doc.textBetween(from, to, '\n');
						const html = editor?.getHTML() ?? ''; // get full HTML

						event.clipboardData.setData('text/plain', plain);
						event.clipboardData.setData('text/html', html);

						event.preventDefault();
						return true;
					}
				}
			},
			onBeforeCreate: ({ editor }) => {
				if (files) {
					(editor.storage as any).files = files;
				}
			},
			onSelectionUpdate: onSelectionUpdate,
			enableInputRules: richText,
			enablePasteRules: richText
		});

		provider?.setEditor(editor, () => ({ md: mdValue, html: htmlValue, json: jsonValue }));

		if (messageInput) {
			selectTemplate();
		}
	});

	onDestroy(() => {
		if (provider) {
			provider.destroy();
		}

		if (editor) {
			editor.destroy();
		}
	});

	$: if (value !== null && editor && !collaboration) {
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

{#if richText && showFormattingToolbar}
	<div bind:this={bubbleMenuElement} id="bubble-menu" class="p-0 {editor ? '' : 'hidden'}">
		<FormattingButtons {editor} />
	</div>

	<div bind:this={floatingMenuElement} id="floating-menu" class="p-0 {editor ? '' : 'hidden'}">
		<FormattingButtons {editor} />
	</div>
{/if}

<div
	bind:this={element}
	dir="auto"
	class="relative w-full min-w-full {className} {!editable ? 'cursor-not-allowed' : ''}"
></div>
