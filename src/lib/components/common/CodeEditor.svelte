<script lang="ts">
	import { basicSetup, EditorView } from 'codemirror';
	import { keymap, placeholder } from '@codemirror/view';
	import { Compartment, EditorState } from '@codemirror/state';

	import { acceptCompletion } from '@codemirror/autocomplete';
	import { indentWithTab } from '@codemirror/commands';

	import { indentUnit } from '@codemirror/language';
	import { python } from '@codemirror/lang-python';
	import { oneDark } from '@codemirror/theme-one-dark';

	import { onMount, createEventDispatcher } from 'svelte';
	import { formatPythonCode } from '$lib/apis/utils';
	import { toast } from 'svelte-sonner';

	const dispatch = createEventDispatcher();

	export let boilerplate = '';
	export let value = '';

	let codeEditor;

	let isDarkMode = false;
	let editorTheme = new Compartment();

	const formatPythonCodeHandler = async () => {
		if (codeEditor) {
			console.log('formatPythonCodeHandler');
			const res = await formatPythonCode(value).catch((error) => {
				toast.error(error);
				return null;
			});

			if (res && res.code) {
				const formattedCode = res.code;
				codeEditor.dispatch({
					changes: [{ from: 0, to: codeEditor.state.doc.length, insert: formattedCode }]
				});
				return true;
			}

			return false;
		}
	};

	let extensions = [
		basicSetup,
		keymap.of([{ key: 'Tab', run: acceptCompletion }, indentWithTab]),
		python(),
		indentUnit.of('    '),
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

		// Add a keyboard shortcut to format the code when Ctrl/Cmd + S is pressed
		// Override the default browser save functionality

		const handleSave = (e) => {
			if ((e.ctrlKey || e.metaKey) && e.key === 's') {
				e.preventDefault();
				formatPythonCodeHandler();
				dispatch('save');
			}
		};

		document.addEventListener('keydown', handleSave);

		return () => {
			observer.disconnect();
			document.removeEventListener('keydown', handleSave);
		};
	});
</script>

<div id="code-textarea" class="h-full w-full" />
