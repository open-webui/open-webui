<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	import { EditorState, Plugin } from 'prosemirror-state';
	import { EditorView, Decoration, DecorationSet } from 'prosemirror-view';
	import { undo, redo, history } from 'prosemirror-history';
	import { schema, defaultMarkdownParser, defaultMarkdownSerializer } from 'prosemirror-markdown';

	import {
		inputRules,
		wrappingInputRule,
		textblockTypeInputRule,
		InputRule
	} from 'prosemirror-inputrules'; // Import input rules
	import { splitListItem, liftListItem, sinkListItem } from 'prosemirror-schema-list'; // Import from prosemirror-schema-list

	import { keymap } from 'prosemirror-keymap';
	import { baseKeymap, chainCommands } from 'prosemirror-commands';
	import { DOMParser, DOMSerializer, Schema } from 'prosemirror-model';

	import { marked } from 'marked'; // Import marked for markdown parsing

	export let className = 'input-prose';

	export let value = '';
	export let placeholder = 'Type here...';

	let element: HTMLElement; // Element where ProseMirror will attach
	let state;
	let view;

	// Plugin to add placeholder when the content is empty
	function placeholderPlugin(placeholder: string) {
		return new Plugin({
			props: {
				decorations(state) {
					const doc = state.doc;
					if (
						doc.childCount === 1 &&
						doc.firstChild.isTextblock &&
						doc.firstChild?.textContent === ''
					) {
						// If there's nothing in the editor, show the placeholder decoration
						const decoration = Decoration.node(0, doc.content.size, {
							'data-placeholder': placeholder,
							class: 'placeholder'
						});
						return DecorationSet.create(doc, [decoration]);
					}
					return DecorationSet.empty;
				}
			}
		});
	}

	// Method to convert markdown content to ProseMirror-compatible document
	function markdownToProseMirrorDoc(markdown: string) {
		return defaultMarkdownParser.parse(value || '');
	}

	// Utility function to convert ProseMirror content back to markdown text
	function serializeEditorContent(doc) {
		return defaultMarkdownSerializer.serialize(doc);
	}

	// ---- Input Rules ----
	// Input rule for heading (e.g., # Headings)
	function headingRule(schema) {
		return textblockTypeInputRule(/^(#{1,6})\s$/, schema.nodes.heading, (match) => ({
			level: match[1].length
		}));
	}

	// Input rule for bullet list (e.g., `- item`)
	function bulletListRule(schema) {
		return wrappingInputRule(/^\s*([-+*])\s$/, schema.nodes.bullet_list);
	}

	// Input rule for ordered list (e.g., `1. item`)
	function orderedListRule(schema) {
		return wrappingInputRule(/^(\d+)\.\s$/, schema.nodes.ordered_list, (match) => ({
			order: +match[1]
		}));
	}

	// Custom input rules for Bold/Italic (using * or _)
	function markInputRule(regexp: RegExp, markType: any) {
		return new InputRule(regexp, (state, match, start, end) => {
			const { tr } = state;
			if (match) {
				tr.replaceWith(start, end, schema.text(match[1], [markType.create()]));
			}
			return tr;
		});
	}

	function boldRule(schema) {
		return markInputRule(/\*([^*]+)\*/, schema.marks.strong);
	}

	function italicRule(schema) {
		return markInputRule(/\_([^*]+)\_/, schema.marks.em);
	}

	// Initialize Editor State and View

	function isInList(state) {
		const { $from } = state.selection;
		return (
			$from.parent.type === schema.nodes.paragraph && $from.node(-1).type === schema.nodes.list_item
		);
	}

	function isEmptyListItem(state) {
		const { $from } = state.selection;
		return isInList(state) && $from.parent.content.size === 0 && $from.node(-1).childCount === 1;
	}

	function exitList(state, dispatch) {
		return liftListItem(schema.nodes.list_item)(state, dispatch);
	}

	onMount(() => {
		const initialDoc = markdownToProseMirrorDoc(value || ''); // Convert the initial content
		// const initialDoc =

		state = EditorState.create({
			doc: initialDoc,
			schema,
			plugins: [
				history(),
				placeholderPlugin(placeholder),
				inputRules({
					rules: [
						headingRule(schema), // Handle markdown-style headings (# H1, ## H2, etc.)
						bulletListRule(schema), // Handle `-` or `*` input to start bullet list
						orderedListRule(schema), // Handle `1.` input to start ordered list
						boldRule(schema), // Bold input rule
						italicRule(schema) // Italic input rule
					]
				}),
				keymap({
					...baseKeymap,
					'Mod-z': undo,
					'Mod-y': redo,
					Enter: chainCommands(
						(state, dispatch, view) => {
							if (isEmptyListItem(state)) {
								return exitList(state, dispatch);
							}
							return false;
						},
						(state, dispatch, view) => {
							if (isInList(state)) {
								return splitListItem(schema.nodes.list_item)(state, dispatch);
							}
							return false;
						},
						baseKeymap.Enter
					),
					// Prevent default tab navigation and provide indent/outdent behavior inside lists:
					Tab: (state, dispatch, view) => {
						const { $from } = state.selection;
						console.log('Tab key pressed', $from.parent, $from.parent.type);
						if (isInList(state)) {
							return sinkListItem(schema.nodes.list_item)(state, dispatch);
						}
						return true; // Prevent Tab from moving the focus
					},
					'Shift-Tab': (state, dispatch, view) => {
						const { $from } = state.selection;
						console.log('Shift-Tab key pressed', $from.parent, $from.parent.type);
						if (isInList(state)) {
							return liftListItem(schema.nodes.list_item)(state, dispatch);
						}
						return true; // Prevent Shift-Tab from moving the focus
					}
				})
			]
		});

		view = new EditorView(element, {
			state,
			dispatchTransaction(transaction) {
				// Update editor state
				let newState = view.state.apply(transaction);
				view.updateState(newState);

				value = serializeEditorContent(newState.doc); // Convert ProseMirror content to markdown text
			}
		});
	});

	// Reinitialize the editor if the value is externally changed (i.e. when `value` is updated)
	$: if (view && value !== serializeEditorContent(view.state.doc)) {
		const newDoc = markdownToProseMirrorDoc(value || '');
		const newState = EditorState.create({
			doc: newDoc,
			schema,
			plugins: view.state.plugins
		});
		view.updateState(newState);
	}

	// Destroy ProseMirror instance on unmount
	onDestroy(() => {
		view?.destroy();
	});
</script>

<div bind:this={element} class="relative w-full h-full {className}"></div>
