<script lang="ts">
	import { onMount, tick } from 'svelte';

	interface Props {
		value?: string;
		placeholder?: string;
		rows?: number;
		required?: boolean;
		className?: string;
	}

	let {
		value = $bindable(''),
		placeholder = '',
		rows = 1,
		required = false,
		className = 'w-full rounded-lg px-3 py-2 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden  h-full'
	}: Props = $props();

	let textareaElement = $state();

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
			textareaElement.style.height = `${textareaElement.scrollHeight}px`;
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
	oninput={(e) => {
		resize();
	}}
	onfocus={() => {
		resize();
	}}
></textarea>
