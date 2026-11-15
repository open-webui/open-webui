<script lang="ts">
	import '$lib/utils/codemirror';
	import { toast } from 'svelte-sonner';
	import { basicSetup, EditorView } from 'codemirror';
	import {
		keymap,
		placeholder as editorPlaceholder,
		GutterMarker,
		gutterLineClass
	} from '@codemirror/view';
	import {
		Compartment,
		EditorSelection,
		EditorState,
		Prec,
		RangeSet,
		StateEffect,
		StateField,
		type Range,
		type Text
	} from '@codemirror/state';
	import { Chunk } from '@codemirror/merge';
	import { indentWithTab, historyField } from '@codemirror/commands';
	import { acceptCompletion, completeAnyWord } from '@codemirror/autocomplete';
	import { indentUnit, LanguageDescription } from '@codemirror/language';
	import { languages } from '@codemirror/language-data';
	import { oneDark } from '@codemirror/theme-one-dark';
	import { onMount, onDestroy } from 'svelte';

	export let value = '';
	export let readOnly = false;
	export let placeholder = '';
	export let ariaLabel = '';
	export let filePath: string | null = null;
	export let gitBaseContent: string | null = null;
	export let onSave: ((content: string) => Promise<void>) | null = null;
	export let searchTarget: {
		line: number;
		column: number;
		length: number;
		requestId: number;
	} | null = null;

	class GitLineMarker extends GutterMarker {
		readonly elementClass: string;
		constructor(elementClass: string) {
			super();
			this.elementClass = elementClass;
		}
	}
	const added = new GitLineMarker('cm-git-line-added');
	const modified = new GitLineMarker('cm-git-line-modified');
	const diffConfig = { timeout: 50 };
	const setGitBase = StateEffect.define<string | null>();

	function markers(base: Text, doc: Text, chunks: readonly Chunk[]) {
		const ranges: Range<GutterMarker>[] = [];
		for (const chunk of chunks) {
			if (chunk.fromB === chunk.toB) continue;
			const removed =
				chunk.fromA === chunk.toA || !base.length
					? 0
					: base.lineAt(chunk.endA).number -
						base.lineAt(chunk.fromA).number +
						1 -
						Number(base.lineAt(chunk.endA).from === base.length);
			const start = doc.lineAt(chunk.fromB).number;
			const end = doc.lineAt(chunk.endB).number;
			for (let number = start; number <= end; number++) {
				const line = doc.line(number);
				if (line.from === doc.length && !line.length) continue;
				ranges.push((number - start < removed ? modified : added).range(line.from));
			}
		}
		return RangeSet.of(ranges);
	}

	const gitLineChanges = StateField.define<{
		base: Text | null;
		chunks: readonly Chunk[];
		markers: RangeSet<GutterMarker>;
	}>({
		create: () => ({ base: null, chunks: [], markers: RangeSet.empty }),
		update(value, transaction) {
			const effect = transaction.effects.find((effect) => effect.is(setGitBase));
			if (!effect && (!transaction.docChanged || value.base === null)) return value;
			const base = effect
				? effect.value === null
					? null
					: EditorState.create({ doc: effect.value }).doc
				: value.base;
			if (base === null) return { base, chunks: [], markers: RangeSet.empty };
			const doc = transaction.state.doc;
			const chunks = effect
				? Chunk.build(base, doc, diffConfig)
				: Chunk.updateB(value.chunks, base, doc, transaction.changes, diffConfig);
			return { base, chunks, markers: markers(base, doc, chunks) };
		},
		provide: (field) => gutterLineClass.from(field, (value) => value.markers)
	});

	let container: HTMLDivElement;
	let editor: EditorView | null = null;
	let editorTheme = new Compartment();
	let editorLanguage = new Compartment();
	let editorReadOnly = new Compartment();
	let internalValue = '';
	let extensions: any[] = [];
	let pendingView: any = null;
	export const captureView = () =>
		editor
			? {
					editorJSON: editor.state.toJSON({ history: historyField }),
					text: editor.state.doc.toString(),
					scrollTop: editor.scrollDOM.scrollTop,
					scrollLeft: editor.scrollDOM.scrollLeft
				}
			: pendingView;
	export function restoreView(view: any) {
		if (!view) return;
		pendingView = view;
		if (!editor || !view.editorJSON) return;
		editor.setState(
			EditorState.fromJSON(view.editorJSON, { extensions }, { history: historyField })
		);
		value = internalValue = editor.state.doc.toString();
		editor.dispatch({ effects: setGitBase.of(gitBaseContent) });
		editor.scrollDOM.scrollTop = view.scrollTop ?? 0;
		editor.scrollDOM.scrollLeft = view.scrollLeft ?? 0;
	}
	let lastSearchTargetRequestId = 0;

	export const getSelection = () => {
		if (!editor || editor.state.selection.main.empty) return undefined;
		const { from, to } = editor.state.selection.main;
		return {
			text: editor.state.sliceDoc(from, to),
			location: `Lines ${editor.state.doc.lineAt(from).number}–${editor.state.doc.lineAt(to).number}`
		};
	};

	/** Return the current editor content */
	export const getValue = (): string => {
		return editor?.state.doc.toString() ?? value;
	};

	/** Replace editor content */
	export const setValue = (newValue: string) => {
		if (!editor) return;
		internalValue = newValue;
		editor.dispatch({
			changes: { from: 0, to: editor.state.doc.length, insert: newValue }
		});
	};

	export const focus = () => {
		editor?.focus();
	};

	const revealSearchTarget = () => {
		if (!editor || !searchTarget || searchTarget.requestId === lastSearchTargetRequestId) return;
		lastSearchTargetRequestId = searchTarget.requestId;
		const lineNumber = Math.min(Math.max(searchTarget.line, 1), editor.state.doc.lines);
		const line = editor.state.doc.line(lineNumber);
		const from = line.from + Math.min(Math.max(searchTarget.column - 1, 0), line.length);
		const to = Math.min(from + Math.max(searchTarget.length, 1), line.to);
		editor.dispatch({
			selection: { anchor: from, head: to },
			effects: EditorView.scrollIntoView(from, { y: 'center' })
		});
		editor.focus();
	};

	let languageGeneration = 0;
	const detectLanguage = async (path: string | null) => {
		const version = ++languageGeneration;
		const filename = path?.split(/[\\/]/).pop() ?? '';
		const match =
			LanguageDescription.matchFilename(languages, filename) ??
			LanguageDescription.matchFilename(languages, filename.toLowerCase());
		editor?.dispatch({ effects: editorLanguage.reconfigure([]) });
		try {
			const language = await match?.load();
			if (version === languageGeneration && editor && language) {
				editor.dispatch({ effects: editorLanguage.reconfigure(language) });
			}
		} catch {
			// Keep the file editable if a language chunk cannot be loaded.
		}
	};

	$: if (editor)
		editor.dispatch({
			effects: editorReadOnly.reconfigure([
				EditorState.readOnly.of(readOnly),
				EditorView.editable.of(!readOnly),
				EditorView.contentAttributes.of(ariaLabel ? { 'aria-label': ariaLabel } : {}),
				placeholder ? editorPlaceholder(placeholder) : []
			])
		});

	// React to external value changes (e.g. switching files)
	$: if (editor && value !== internalValue) {
		internalValue = value;
		editor.dispatch({
			changes: { from: 0, to: editor.state.doc.length, insert: value }
		});
	}

	// React to filePath changes for language detection
	$: if (editor) {
		detectLanguage(filePath);
	}

	$: if (editor && searchTarget) {
		revealSearchTarget();
	}
	$: if (editor) editor.dispatch({ effects: setGitBase.of(gitBaseContent) });

	onMount(() => {
		const isDark = document.documentElement.classList.contains('dark');
		internalValue = value;

		extensions = [
			basicSetup,
			gitLineChanges,
			EditorState.languageData.of(() => [{ autocomplete: completeAnyWord }]),
			Prec.high(
				keymap.of(
					['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].map((key) => ({
						key,
						run: (view: EditorView) => {
							const { selection } = view.state;
							if (selection.ranges.some((range) => !range.empty)) {
								view.dispatch({
									selection: EditorSelection.create(
										selection.ranges.map((range) => EditorSelection.cursor(range.head)),
										selection.mainIndex
									)
								});
							}
							// Let the normal arrow command move on this same keypress.
							return false;
						}
					}))
				)
			),
			keymap.of([
				{ key: 'Tab', run: acceptCompletion },
				indentWithTab,
				{
					key: 'Mod-s',
					run: () => {
						if (onSave && !readOnly) {
							void onSave(editor?.state.doc.toString() ?? '').catch((e) => toast.error(String(e)));
						}
						return true;
					}
				}
			]),
			indentUnit.of('    '),
			EditorView.updateListener.of((e) => {
				if (e.docChanged) {
					internalValue = e.state.doc.toString();
					value = internalValue;
				}
			}),
			editorTheme.of(isDark ? oneDark : []),
			editorLanguage.of([]),
			editorReadOnly.of([
				EditorState.readOnly.of(readOnly),
				EditorView.editable.of(!readOnly),
				EditorView.contentAttributes.of(ariaLabel ? { 'aria-label': ariaLabel } : {}),
				placeholder ? editorPlaceholder(placeholder) : []
			]),
			EditorView.theme({
				'&': { fontSize: '0.8125rem', height: '100%' },
				'.cm-content': {
					padding: '0.5rem 0'
				},
				'.cm-scroller': {
					overflow: 'auto',
					fontFamily: '"JetBrains Mono", "Fira Code", ui-monospace, monospace'
				},
				'&.cm-focused': { outline: 'none' }
			})
		];

		editor = new EditorView({
			state: EditorState.create({ doc: value, extensions }),
			parent: container
		});

		if (pendingView) restoreView(pendingView);
		revealSearchTarget();

		// Watch dark mode
		const observer = new MutationObserver(() => {
			const dark = document.documentElement.classList.contains('dark');
			editor?.dispatch({ effects: editorTheme.reconfigure(dark ? oneDark : []) });
		});
		observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

		return () => {
			observer.disconnect();
			editor?.destroy();
			editor = null;
		};
	});

	onDestroy(() => {
		editor?.destroy();
		editor = null;
	});
</script>

<div bind:this={container} class="file-code-editor" />

<style>
	.file-code-editor {
		--editor-bg: #fff;
		--editor-fg: #525252;
		width: 100%;
		height: 100%;
	}
	:global(.dark) .file-code-editor {
		--editor-bg: #121212;
		--editor-fg: #d4d4d4;
	}
	.file-code-editor :global(.cm-editor) {
		height: 100%;
		background-color: var(--editor-bg);
		color: var(--editor-fg);
	}
	.file-code-editor :global(.cm-gutters) {
		background-color: var(--editor-bg) !important;
		color: color-mix(in oklab, var(--editor-fg) 48%, var(--editor-bg));
	}
	.file-code-editor :global(.cm-activeLine),
	.file-code-editor :global(.cm-activeLineGutter) {
		background-color: color-mix(in oklab, var(--editor-fg) 6%, transparent);
	}

	.file-code-editor :global(.cm-lineNumbers .cm-git-line-added) {
		box-shadow: inset 2px 0 0 rgba(5, 150, 105, 0.65);
	}
	.file-code-editor :global(.cm-lineNumbers .cm-git-line-modified) {
		box-shadow: inset 2px 0 0 rgba(217, 119, 6, 0.6);
	}
	:global(.dark) .file-code-editor :global(.cm-lineNumbers .cm-git-line-added) {
		box-shadow: inset 2px 0 0 rgba(52, 211, 153, 0.75);
	}
	:global(.dark) .file-code-editor :global(.cm-lineNumbers .cm-git-line-modified) {
		box-shadow: inset 2px 0 0 rgba(251, 191, 36, 0.7);
	}
</style>
