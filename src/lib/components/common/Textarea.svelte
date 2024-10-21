<script lang="ts">
	import { onMount, tick } from 'svelte';

	export let value = '';
	export let placeholder = '';

	export let className =
		'w-full rounded-lg px-3 py-2 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-none resize-none h-full';

	let textareaElement;

	onMount(async () => {
		await tick();
		if (textareaElement) {
			setInterval(adjustHeight, 0);
		}
	});

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
	class={className}
	on:input={(e) => {
		e.target.style.height = '';
		e.target.style.height = `${e.target.scrollHeight}px`;
	}}
	rows="1"
/>
