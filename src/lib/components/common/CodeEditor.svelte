<script lang="ts">
	import { basicSetup, EditorView } from 'codemirror';
	import { keymap, placeholder } from '@codemirror/view';
	import { EditorState } from '@codemirror/state';

	import { acceptCompletion } from '@codemirror/autocomplete';
	import { indentWithTab } from '@codemirror/commands';

	import { python } from '@codemirror/lang-python';
	import { oneDark } from '@codemirror/theme-one-dark';

	import { onMount } from 'svelte';

	export let value = '';

	onMount(() => {
		// python code editor, highlight python code
		const codeEditor = new EditorView({
			state: EditorState.create({
				doc: value,
				extensions: [
					basicSetup,
					keymap.of([{ key: 'Tab', run: acceptCompletion }, indentWithTab]),
					python(),
					oneDark,
					placeholder('Enter your code here...')
				]
			}),
			parent: document.getElementById('code-textarea')
		});
	});
</script>

<div id="code-textarea" />
