<script lang="ts">
	import { onMount } from 'svelte';
	import type { HTMLTextareaAttributes } from 'svelte/elements';

	export let value = '';
	export let placeholder = '';
	export let rows = 1;
	export let minSize: number | null = null;
	export let maxSize: number | null = null;
	export let required = false;
	export let readonly = false;
	export let disabled = false;
	export let id: string | undefined = undefined;
	export let autocomplete: HTMLTextareaAttributes['autocomplete'] = undefined;
	export let spellcheck: boolean | undefined = undefined;
	export let autocapitalize: HTMLTextareaAttributes['autocapitalize'] = undefined;
	export let onKeydown: (event: KeyboardEvent) => void = () => {};
	export let className =
		'w-full rounded-lg px-3.5 py-2 text-sm bg-gray-50 dark:text-gray-300 dark:bg-gray-850 outline-hidden  h-full';
	export let ariaLabel: string | null = null;

	export let onInput: (event: Event) => void = () => {};
	export let onBlur: (event: FocusEvent) => void = () => {};

	let textareaElement: HTMLTextAreaElement | null = null;

	// The bound element exists on mount. Cancel the layout callback on navigation.
	onMount(() => {
		resize();
		const frame = requestAnimationFrame(resize);
		return () => cancelAnimationFrame(frame);
	});

	const resize = () => {
		if (textareaElement) {
			// Find all ancestors that currently have an active scroll offset.
			// This is extremely fast because reading `scrollTop` on a clean layout doesn't trigger reflow,
			// and it makes the fix 100% robust without relying on hardcoded CSS classes.
			const activeScrollParents: { el: HTMLElement; top: number }[] = [];
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
	{disabled}
	{id}
	{autocomplete}
	{spellcheck}
	{autocapitalize}
	on:keydown={onKeydown}
	on:input={(e) => {
		resize();

		onInput(e);
	}}
	on:focus={() => {
		resize();
	}}
	on:blur={onBlur}
	on:change
></textarea>
