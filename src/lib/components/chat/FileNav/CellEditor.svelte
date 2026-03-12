<script lang="ts">
	import '$lib/utils/codemirror';
	import { basicSetup, EditorView } from 'codemirror';
	import { keymap } from '@codemirror/view';
	import { Compartment, EditorState, Prec } from '@codemirror/state';
	import { indentWithTab } from '@codemirror/commands';
	import { indentUnit } from '@codemirror/language';
	import { languages } from '@codemirror/language-data';
	import { oneDark } from '@codemirror/theme-one-dark';
	import { onMount, onDestroy, createEventDispatcher } from 'svelte';

	const dispatch = createEventDispatcher();

	export let value = '';
	export let lang = 'python';

	let container: HTMLDivElement;
	let editor: EditorView | null = null;
	let editorTheme = new Compartment();
	let editorLanguage = new Compartment();

	const getLang = async () => {
		const language = languages.find((l) => l.alias.includes(lang));
		return await language?.load();
	};

	onMount(async () => {
		const isDark = document.documentElement.classList.contains('dark');

		const extensions = [
			Prec.highest(
				keymap.of([
					{
						key: 'Mod-Enter',
						run: () => {
							dispatch('run');
							return true;
						}
					},
					{
						key: 'Escape',
						run: () => {
							dispatch('cancel');
							return true;
						}
					}
				])
			),
			basicSetup,
			keymap.of([indentWithTab]),
			indentUnit.of('    '),
			EditorView.updateListener.of((e) => {
				if (e.docChanged) {
					value = e.state.doc.toString();
					dispatch('change', value);
				}
			}),
			editorTheme.of(isDark ? oneDark : []),
			editorLanguage.of([]),
			EditorView.theme({
				'&': { fontSize: '0.75rem' },
				'.cm-content': {
					padding: '0.35rem 0',
					fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace'
				},
				'.cm-gutters': { display: 'none' },
				'.cm-focused': { outline: 'none' },
				'.cm-scroller': { overflow: 'auto' }
			})
		];

		editor = new EditorView({
			state: EditorState.create({ doc: value, extensions }),
			parent: container
		});

		const language = await getLang();
		if (language && editor) {
			editor.dispatch({ effects: editorLanguage.reconfigure(language) });
		}

		// Watch dark mode
		const observer = new MutationObserver(() => {
			const dark = document.documentElement.classList.contains('dark');
			editor?.dispatch({ effects: editorTheme.reconfigure(dark ? oneDark : []) });
		});
		observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });

		editor.focus();

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

<div bind:this={container} class="nb-cm-editor" />

<style>
	.nb-cm-editor {
		width: 100%;
		background: #fffef5;
	}
	:global(.dark) .nb-cm-editor {
		background: transparent;
	}
</style>
