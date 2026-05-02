<script lang="ts">
	import { onMount, tick } from 'svelte';

	export let value = '';
	export let placeholder = '';
	export let rows = 1;
	export let minSize = null;
	export let maxSize = null;
	export let required = false;
	export let readonly = false;
	export let className =
		'w-full rounded-lg px-3.5 py-2 text-sm bg-white border-hairline border-gray-300 dark:text-gray-300 dark:bg-gray-900 dark:border-gray-700 outline-hidden focus-visible:ring-2 focus-visible:ring-[#61AAF2]/40 focus-visible:border-[#61AAF2] transition-colors duration-200 ease-paper h-full';

	export let onBlur = () => {};
	let textareaElement;

	// Adjust height on mount and after setting the element.
	onMount(async () => {
		await tick();
		resize();

		requestAnimationFrame(() => {
			// setInterveal to cehck until textareaElement is set
			const interval = setInterval(() => {
				if (textareaElement) {
					clearInterval(interval);
					resize();
				}
			}, 100);
		});
	});

	const resize = () => {
		if (textareaElement) {
			textareaElement.style.height = '';

			let height = textareaElement.scrollHeight;
			if (maxSize && height > maxSize) {
				height = maxSize;
			}
			if (minSize && height < minSize) {
				height = minSize;
			}

			textareaElement.style.height = `${height}px`;
		}
	};
</script>

<textarea
	bind:this={textareaElement}
	bind:value
	{placeholder}
	class={className}
	style="field-sizing: content;"
	{rows}
	{required}
	{readonly}
	on:input={(e) => {
		resize();
	}}
	on:focus={() => {
		resize();
	}}
	on:blur={onBlur}
/>
