<script lang="ts">
	import { copyToClipboard } from '$lib/utils';
	import hljs from 'highlight.js';
	import 'highlight.js/styles/github-dark.min.css';
	import { onMount, tick } from 'svelte';

	export let id = '';
	export let lang = '';
	export let code = '';

	let highlightedCode = null;
	let copied = false;

	const copyCode = async () => {
		copied = true;
		await copyToClipboard(code);

		setTimeout(() => {
			copied = false;
		}, 1000);
	};

	let debounceTimeout;
	$: if (code) {
		// Function to perform the code highlighting
		const highlightCode = () => {
			highlightedCode = hljs.highlightAuto(code, hljs.getLanguage(lang)?.aliases).value || code;
		};

		// Clear the previous timeout if it exists
		clearTimeout(debounceTimeout);

		// Set a new timeout to debounce the code highlighting
		debounceTimeout = setTimeout(highlightCode, 10);
	}
</script>

<div class="mb-4" dir="ltr">
	<div
		class="flex justify-between bg-[#202123] text-white text-xs px-4 pt-1 pb-0.5 rounded-t-lg overflow-x-auto"
	>
		<div class="p-1">{@html lang}</div>

		<div class="flex items-center">
			<button class="copy-code-button bg-none border-none p-1" on:click={copyCode}
				>{copied ? 'Copied' : 'Copy Code'}</button
			>
		</div>
	</div>

	<pre
		class="hljs p-4 px-5 overflow-x-auto"
		style="border-top-left-radius: 0px; border-top-right-radius: 0px;">
		<code
			class="language-{lang} rounded-t-none whitespace-pre"
			>{#if highlightedCode}{@html highlightedCode}{:else}{code}{/if}</code
		>
	</pre>
</div>