<script lang="ts">
	import { onMount, tick } from 'svelte';

	export let value = '';
	export let placeholder = '';
	export let className =
		'w-full rounded-lg px-3 py-2 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none resize-none h-full';

	let textareaElement;

	$: if (textareaElement) {
		if (textareaElement.innerText !== value && value !== '') {
			textareaElement.innerText = value ?? '';
		}
	}

	// Adjust height on mount and after setting the element.
	onMount(async () => {
		await tick();
	});

	// Handle paste event to ensure only plaintext is pasted
	function handlePaste(event: ClipboardEvent) {
		event.preventDefault(); // Prevent the default paste action
		const clipboardData = event.clipboardData?.getData('text/plain'); // Get plaintext from clipboard

		// Insert plaintext into the textarea
		document.execCommand('insertText', false, clipboardData);
	}
</script>

<div
	contenteditable="true"
	bind:this={textareaElement}
	class="{className} whitespace-pre-wrap relative {value
		? !value.trim()
			? 'placeholder'
			: ''
		: 'placeholder'}"
	style="field-sizing: content; -moz-user-select: text !important;"
	on:input={() => {
		const text = textareaElement.innerText;
		if (text === '\n') {
			value = '';
			return;
		}

		value = text;
	}}
	on:paste={handlePaste}
	data-placeholder={placeholder}
/>

<style>
	.placeholder::before {
		/* abolute */
		position: absolute;
		content: attr(data-placeholder);
		color: #adb5bd;
		overflow: hidden;
		display: -webkit-box;
		-webkit-box-orient: vertical;
		-webkit-line-clamp: 1;
		pointer-events: none;
		touch-action: none;
	}
</style>
