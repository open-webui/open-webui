<script lang="ts">
	import { onMount, tick } from 'svelte';

	export let value = '';
	export let placeholder = '';
	export let rows = 1;
	export let required = false;
	export let className =
		'w-full rounded-lg px-3 py-2 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none resize-none h-full';

	let textareaElement;

	// Adjust height on mount and after setting the element.
	onMount(async () => {
		await tick();
		adjustHeight();
	});

	// This reactive statement runs whenever `value` changes
	$: adjustHeight();

	// Adjust height to match content
	const adjustHeight = () => {
		if (textareaElement) {
			// Reset height to calculate the correct scroll height
			textareaElement.style.height = 'auto';
			textareaElement.style.height = `${textareaElement.scrollHeight}px`;
		}
	};
</script>

<textarea
	bind:this={textareaElement}
	bind:value
	{placeholder}
	on:input={adjustHeight}
	class={className}
	{rows}
	{required}
/>
