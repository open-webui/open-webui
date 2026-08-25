<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	export let open = false;
	export let side: 'left' | 'right' = 'right';
	export let width = 350;
	export let minWidth = 300;
	export let maxWidth: number | null = null;
	export let minSiblingWidth = 0;
	export let closeOnDragBelowMinWidth = false;
	export let storageKey = '';
	export let className = '';
	export let resizerId = 'controls-resizer';
	export let onClose: () => void = () => {};

	let panelElement: HTMLDivElement | null = null;
	let isResizing = false;
	let startClientX = 0;
	let startWidth = 0;

	const getMaxWidth = () => {
		const siblingMaxWidth =
			minSiblingWidth > 0 && panelElement?.parentElement
				? Math.max(0, panelElement.parentElement.clientWidth - minSiblingWidth)
				: null;

		if (maxWidth === null) {
			return siblingMaxWidth;
		}
		return siblingMaxWidth === null ? maxWidth : Math.min(maxWidth, siblingMaxWidth);
	};

	const clamp = (value: number) => {
		const resolvedMaxWidth = getMaxWidth();
		const minimum = resolvedMaxWidth === null ? minWidth : Math.min(minWidth, resolvedMaxWidth);
		const clampedToMin = Math.max(minimum, value);
		return resolvedMaxWidth === null ? clampedToMin : Math.min(resolvedMaxWidth, clampedToMin);
	};

	const persistWidth = () => {
		if (storageKey) {
			localStorage.setItem(storageKey, String(width));
		}
	};

	const close = () => {
		open = false;
		onClose();
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
		const nextWidth = side === 'right' ? startWidth - dx : startWidth + dx;
		if (closeOnDragBelowMinWidth && nextWidth < minWidth) {
			close();
			resizeEndHandler();
			return;
		}
		width = clamp(nextWidth);
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

	$: if (open && panelElement) {
		const clampedWidth = clamp(width);
		if (clampedWidth !== width) {
			width = clampedWidth;
		}
	}

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
	on:resize={() => {
		if (open) width = clamp(width);
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

	<div bind:this={panelElement} class={className} style="width: {width}px; flex: 0 0 {width}px;">
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
