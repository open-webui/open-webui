<script lang="ts">
	import { onMount, tick } from 'svelte';

	export let value = '';
	export let placeholder = '';

	export let rows = 1;
	export let required = false;

	export let className =
		'w-full rounded-lg px-3 py-2 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none resize-none h-full';

	let textareaElement;

	onMount(async () => {
		await tick();
		if (textareaElement) {
			await tick();
			setTimeout(adjustHeight, 0);
		}
	});

	$: if (value) {
		setTimeout(adjustHeight, 0);
	}

	const adjustHeight = () => {
		if (textareaElement) {
			textareaElement.style.height = '';
			textareaElement.style.height = `${textareaElement.scrollHeight}px`;
		}
	};
</script>

<textarea
	bind:this={textareaElement}
	bind:value
	{placeholder}
	on:input={adjustHeight}
	on:focus={adjustHeight}
	class={className}
	{rows}
	{required}
/>
