<script lang="ts">
	import '$lib/utils/codemirror';
	import { basicSetup, EditorView } from 'codemirror';
	import { keymap } from '@codemirror/view';
	import { Compartment, EditorState } from '@codemirror/state';
	import { indentWithTab } from '@codemirror/commands';
	import { indentUnit, LanguageDescription } from '@codemirror/language';
	import { languages } from '@codemirror/language-data';
	import { oneDark } from '@codemirror/theme-one-dark';
	import { onMount, onDestroy } from 'svelte';

	export let value = '';
	export let filePath: string | null = null;
	export let onSave: ((content: string) => Promise<void>) | null = null;

	let container: HTMLDivElement;
	let editor: EditorView | null = null;
	let editorTheme = new Compartment();
	let editorLanguage = new Compartment();
	let internalValue = '';

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

	const detectLanguage = async (path: string | null) => {
		if (!path) return;
		const match = LanguageDescription.matchFilename(languages, path);
		if (match) {
			const lang = await match.load();
			if (lang && editor) {
				editor.dispatch({ effects: editorLanguage.reconfigure(lang) });
			}
		}
	};

	// React to external value changes (e.g. switching files)
	$: if (editor && value !== internalValue) {
		internalValue = value;
		editor.dispatch({
			changes: { from: 0, to: editor.state.doc.length, insert: value }
		});
	}

	// React to filePath changes for language detection
	$: if (editor && filePath) {
		detectLanguage(filePath);
	}

	onMount(() => {
		const isDark = document.documentElement.classList.contains('dark');
		internalValue = value;

		const extensions = [
			basicSetup,
			keymap.of([
				indentWithTab,
				{
					key: 'Mod-s',
					run: () => {
						if (onSave) {
							onSave(editor?.state.doc.toString() ?? '');
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
			EditorView.theme({
				'&': { fontSize: '0.75rem', height: '100%' },
				'.cm-content': {
					padding: '0.5rem 0',
					fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace'
				},
				'.cm-scroller': { overflow: 'auto' },
				'.cm-focused': { outline: 'none' }
			})
		];

		editor = new EditorView({
			state: EditorState.create({ doc: value, extensions }),
			parent: container
		});

		detectLanguage(filePath);

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
		width: 100%;
		height: 100%;
	}
	.file-code-editor :global(.cm-editor) {
		height: 100%;
	}
</style>
