<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	export let open = false;
	export let side: 'left' | 'right' = 'right';
	export let width = 350;
	export let minWidth = 300;
	export let maxWidth: number | null = null;
	export let storageKey = '';
	export let className = '';
	export let resizerId = 'controls-resizer';

	let isResizing = false;
	let startClientX = 0;
	let startWidth = 0;

	const clamp = (value: number) =>
		maxWidth === null ? Math.max(minWidth, value) : Math.min(maxWidth, Math.max(minWidth, value));

	const persistWidth = () => {
		if (storageKey) {
			localStorage.setItem(storageKey, String(width));
		}
	};

	const resizeStartHandler = (e: MouseEvent) => {
		if (!open) return;

		isResizing = true;
		startClientX = e.clientX;
		startWidth = width;
		document.body.style.userSelect = 'none';
	};

	const resizeEndHandler = () => {
		if (!isResizing) return;

		isResizing = false;
		document.body.style.userSelect = '';
		persistWidth();
	};

	const resizeHandler = (endClientX: number) => {
		const dx = endClientX - startClientX;
		width = clamp(side === 'right' ? startWidth - dx : startWidth + dx);
	};

	const resizeKeyHandler = (e: KeyboardEvent) => {
		if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;

		e.preventDefault();
		const delta = e.key === 'ArrowLeft' ? -10 : 10;
		width = clamp(width + (side === 'right' ? -delta : delta));
		persistWidth();
	};

	onMount(() => {
		if (!storageKey) return;

		const storedWidth = Number(localStorage.getItem(storageKey));
		if (!Number.isNaN(storedWidth)) {
			width = clamp(storedWidth);
		}
	});

	onDestroy(() => {
		if (isResizing) {
			document.body.style.userSelect = '';
		}
	});
</script>

<svelte:window
	on:mousemove={(e) => {
		if (!isResizing) return;
		resizeHandler(e.clientX);
	}}
	on:mouseup={resizeEndHandler}
/>

{#if open}
	{#if side === 'right'}
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_no_noninteractive_tabindex -->
		<div
			class="relative flex items-center justify-center group border-l border-gray-50 dark:border-gray-850/30 hover:border-gray-200 dark:hover:border-gray-800 transition z-20 bg-transparent p-0 appearance-none"
			id={resizerId}
			on:mousedown={resizeStartHandler}
			on:keydown={resizeKeyHandler}
			role="separator"
			tabindex="0"
			aria-label="Resize panel"
			aria-orientation="vertical"
		>
			<span
				class="absolute -left-1.5 -right-1.5 -top-0 -bottom-0 z-20 cursor-col-resize bg-transparent"
			></span>
		</div>
	{/if}

	<div class={className} style="width: {width}px; flex: 0 0 {width}px;">
		<slot />
	</div>

	{#if side === 'left'}
		<!-- svelte-ignore a11y_no_noninteractive_element_interactions, a11y_no_noninteractive_tabindex -->
		<div
			class="relative flex items-center justify-center group border-r border-gray-50 dark:border-gray-850/30 hover:border-gray-200 dark:hover:border-gray-800 transition z-20 bg-transparent p-0 appearance-none"
			id={resizerId}
			on:mousedown={resizeStartHandler}
			on:keydown={resizeKeyHandler}
			role="separator"
			tabindex="0"
			aria-label="Resize panel"
			aria-orientation="vertical"
		>
			<span
				class="absolute -left-1.5 -right-1.5 -top-0 -bottom-0 z-20 cursor-col-resize bg-transparent"
			></span>
		</div>
	{/if}
{/if}
