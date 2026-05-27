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
		'w-full rounded-lg px-3.5 py-2 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden  h-full';
	export let ariaLabel = null;

	export let onInput = () => {};
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
			// Find all ancestors that currently have an active scroll offset.
			// This is extremely fast because reading `scrollTop` on a clean layout doesn't trigger reflow,
			// and it makes the fix 100% robust without relying on hardcoded CSS classes.
			let activeScrollParents = [];
			let p = textareaElement.parentNode;
			while (p && p !== document.body) {
				if (p instanceof HTMLElement && p.scrollTop > 0) {
					activeScrollParents.push({ el: p, top: p.scrollTop });
				}
				p = p.parentNode;
			}
			const windowScrollY = window.scrollY;

			textareaElement.style.height = '';

			let height = textareaElement.scrollHeight;
			if (maxSize && height > maxSize) {
				height = maxSize;
			}
			if (minSize && height < minSize) {
				height = minSize;
			}

			textareaElement.style.height = `${height}px`;

			// Only restore scroll for elements that were actually scrolled.
			// This prevents layout thrashing that happens if we blindly set `.scrollTop` on every parent.
			activeScrollParents.forEach((p) => {
				if (p.el.scrollTop !== p.top) p.el.scrollTop = p.top;
			});
			if (window.scrollY !== windowScrollY) {
				window.scrollTo(window.scrollX, windowScrollY);
			}
		}
	};
</script>

<textarea
	bind:this={textareaElement}
	bind:value
	{placeholder}
	aria-label={ariaLabel || placeholder}
	class={className}
	style="field-sizing: content;"
	{rows}
	{required}
	{readonly}
	on:input={(e) => {
		resize();

		onInput(e);
	}}
	on:focus={() => {
		resize();
	}}
	on:blur={onBlur}
/>
