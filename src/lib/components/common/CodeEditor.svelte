<script lang="ts">
	import { basicSetup, EditorView } from 'codemirror';
	import { keymap, placeholder } from '@codemirror/view';
	import { Compartment, EditorState } from '@codemirror/state';

	import { acceptCompletion } from '@codemirror/autocomplete';
	import { indentWithTab } from '@codemirror/commands';

	import { python } from '@codemirror/lang-python';
	import { oneDark } from '@codemirror/theme-one-dark';

	import { onMount } from 'svelte';

	export let boilerplate = '';
	export let value = '';

	let codeEditor;

	let isDarkMode = false;
	let editorTheme = new Compartment();

	let extensions = [
		basicSetup,
		keymap.of([{ key: 'Tab', run: acceptCompletion }, indentWithTab]),
		python(),
		placeholder('Enter your code here...'),
		EditorView.updateListener.of((e) => {
			if (e.docChanged) {
				value = e.state.doc.toString();
			}
		}),
		editorTheme.of([])
	];

	onMount(() => {
		// Check if html class has dark mode
		isDarkMode = document.documentElement.classList.contains('dark');

		// python code editor, highlight python code
		codeEditor = new EditorView({
			state: EditorState.create({
				doc: boilerplate,
				extensions: extensions
			}),
			parent: document.getElementById('code-textarea')
		});

		if (isDarkMode) {
			codeEditor.dispatch({
				effects: editorTheme.reconfigure(oneDark)
			});
		}

		// listen to html class changes this should fire only when dark mode is toggled
		const observer = new MutationObserver((mutations) => {
			mutations.forEach((mutation) => {
				if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
					const _isDarkMode = document.documentElement.classList.contains('dark');

					if (_isDarkMode !== isDarkMode) {
						isDarkMode = _isDarkMode;
						if (_isDarkMode) {
							codeEditor.dispatch({
								effects: editorTheme.reconfigure(oneDark)
							});
						} else {
							codeEditor.dispatch({
								effects: editorTheme.reconfigure()
							});
						}
					}
				}
			});
		});

		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class']
		});

		return () => {
			observer.disconnect();
		};
	});
</script>

<div id="code-textarea" class="h-full w-full" />
