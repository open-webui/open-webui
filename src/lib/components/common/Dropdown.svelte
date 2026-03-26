<script lang="ts">
	import { flyAndScale } from '$lib/utils/transitions';
	import { tick } from 'svelte';

	/** Whether the dropdown is open */
	export let show = false;

	/** Side to open on: 'bottom' | 'top' */
	export let side = 'bottom';

	/** Alignment: 'start' | 'end' */
	export let align = 'start';

	/** Close when clicking outside */
	export let closeOnOutsideClick = true;

	/** Called when open/close state changes */
	export let onOpenChange: (state: boolean) => void = () => {};

	/** CSS classes for the dropdown content container */
	export let contentClass = '';

	/** Side offset in px */
	export let sideOffset = 4;

	let triggerEl;
	let contentEl;

	/** Svelte action: moves the node to document.body */
	function portal(node) {
		document.body.appendChild(node);
		return {
			destroy() {
				if (node.parentNode) {
					node.parentNode.removeChild(node);
				}
			}
		};
	}

	/** Svelte action: captures the first child element as the trigger reference */
	function trigger(node) {
		triggerEl = node.firstElementChild || node;
		function handleClick(e) {
			e.preventDefault();
			toggleOpen();
		}
		node.addEventListener('click', handleClick);
		return {
			destroy() {
				node.removeEventListener('click', handleClick);
			}
		};
	}

	function positionContent() {
		if (!triggerEl || !contentEl) return;
		const rect = triggerEl.getBoundingClientRect();

		contentEl.style.position = 'fixed';
		contentEl.style.zIndex = '9999';

		const contentHeight = contentEl.offsetHeight || 0;
		const spaceBelow = window.innerHeight - rect.bottom - sideOffset;
		const spaceAbove = rect.top - sideOffset;

		// Auto-flip: prefer the requested side, but flip if not enough space
		let openAbove = side === 'top';
		if (side === 'bottom' && spaceBelow < contentHeight && spaceAbove > spaceBelow) {
			openAbove = true;
		} else if (side === 'top' && spaceAbove < contentHeight && spaceBelow > spaceAbove) {
			openAbove = false;
		}

		if (openAbove) {
			contentEl.style.bottom = `${window.innerHeight - rect.top + sideOffset}px`;
			contentEl.style.top = 'auto';
		} else {
			contentEl.style.top = `${rect.bottom + sideOffset}px`;
			contentEl.style.bottom = 'auto';
		}

		if (align === 'end') {
			let right = window.innerWidth - rect.right;
			// Shift if overflowing left edge
			const contentWidth = contentEl.offsetWidth || 0;
			if (right + contentWidth > window.innerWidth) {
				right = window.innerWidth - contentWidth - 16;
			}
			contentEl.style.right = `${Math.max(16, right)}px`;
			contentEl.style.left = 'auto';
		} else {
			let left = rect.left;
			// Shift if overflowing right edge
			const contentWidth = contentEl.offsetWidth || 0;
			if (left + contentWidth + 16 > window.innerWidth) {
				left = window.innerWidth - contentWidth - 16;
			}
			contentEl.style.left = `${Math.max(16, left)}px`;
			contentEl.style.right = 'auto';
		}
	}

	async function toggleOpen() {
		show = !show;
		onOpenChange(show);
		if (show) {
			await tick();
			positionContent();
			// Re-check after transition renders real dimensions
			setTimeout(positionContent, 50);
		}
	}

	// React to external show changes (e.g. bind:show toggled by parent component)
	$: if (show) {
		tick().then(() => {
			positionContent();
			setTimeout(positionContent, 50);
		});
	}

	function handleWindowPointerDown(event) {
		if (!show || !closeOnOutsideClick) return;
		if (triggerEl?.contains(event.target)) return;
		if (contentEl?.contains(event.target)) return;
		show = false;
		onOpenChange(false);
	}

	function handleKeydown(event) {
		if (event.key === 'Escape' && show) {
			show = false;
			onOpenChange(false);
		}
	}

	/** Close the dropdown programmatically */
	export function close() {
		show = false;
		onOpenChange(false);
	}

	import { onMount, onDestroy } from 'svelte';

	let onPointerDown;
	onMount(() => {
		onPointerDown = (e) => handleWindowPointerDown(e);
		document.addEventListener('pointerdown', onPointerDown, true);
	});
	onDestroy(() => {
		if (onPointerDown) {
			document.removeEventListener('pointerdown', onPointerDown, true);
		}
	});
</script>

<svelte:window
	on:keydown={handleKeydown}
	on:scroll|capture={positionContent}
	on:resize={positionContent}
/>

<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<span use:trigger style="display: contents; cursor: pointer;">
	<slot />
</span>

{#if show}
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		use:portal
		bind:this={contentEl}
		class={contentClass}
		transition:flyAndScale
		on:click|stopPropagation
	>
		<slot name="content" />
	</div>
{/if}
