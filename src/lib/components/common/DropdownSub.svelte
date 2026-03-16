<script lang="ts">
	import { flyAndScale } from '$lib/utils/transitions';
	import { tick } from 'svelte';

	/** CSS classes for the sub-content container */
	export let contentClass = 'select-none rounded-2xl p-1 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg border border-gray-100 dark:border-gray-800';

	/** Max width in px, enforced at the component level */
	export let maxWidth = 200;

	/** Side offset from the trigger in px */
	export let sideOffset = 8;

	let open = false;
	let triggerEl;
	let contentEl;

	function positionContent() {
		if (!triggerEl || !contentEl) return;
		const rect = triggerEl.getBoundingClientRect();

		contentEl.style.position = 'fixed';
		contentEl.style.zIndex = '99999';

		// Inherit min-width from parent dropdown container
		const parentContainer = triggerEl.closest('[class*="rounded"]')?.parentElement;
		if (parentContainer) {
			const parentWidth = parentContainer.offsetWidth;
			if (parentWidth > 0) {
				contentEl.style.minWidth = `${parentWidth}px`;
			}
		}

		// Position to the right of the trigger
		const rightSpace = window.innerWidth - rect.right;
		const contentWidth = contentEl.offsetWidth || 200;

		if (rightSpace >= contentWidth + sideOffset) {
			// Open to the right
			contentEl.style.left = `${rect.right + sideOffset}px`;
			contentEl.style.right = 'auto';
		} else {
			// Open to the left
			contentEl.style.right = `${window.innerWidth - rect.left + sideOffset}px`;
			contentEl.style.left = 'auto';
		}

		// Vertical positioning with robust bounds clamping (shift method)
		const contentHeight = contentEl.offsetHeight || 0;
		let top = rect.top;
		
		// If it overflows the bottom edge
		if (top + contentHeight + 16 > window.innerHeight) {
			top = window.innerHeight - contentHeight - 16;
		}
		
		// If shifting it up causes it to overflow the top edge, cap it at 16px
		if (top < 16) {
			top = 16;
		}

		contentEl.style.top = `${top}px`;
	}

	async function handleMouseEnter() {
		open = true;
		await tick();
		positionContent();
		// Re-position after transition starts rendering real dimensions
		setTimeout(positionContent, 50);
	}

	function handleMouseLeave(event) {
		// Don't close if moving to the sub-content
		if (contentEl?.contains(event.relatedTarget)) return;
		if (triggerEl?.contains(event.relatedTarget)) return;
		open = false;
	}

	function handleContentMouseLeave(event) {
		if (triggerEl?.contains(event.relatedTarget)) return;
		if (contentEl?.contains(event.relatedTarget)) return;
		open = false;
	}

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
</script>

<svelte:window on:scroll|capture={positionContent} on:resize={positionContent} />

<!-- svelte-ignore a11y-no-static-element-interactions -->
<div
	bind:this={triggerEl}
	class="w-full"
	on:mouseenter={handleMouseEnter}
	on:mouseleave={handleMouseLeave}
>
	<slot name="trigger" />
</div>

{#if open}
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<div
		use:portal
		bind:this={contentEl}
		class={contentClass}
		style="max-width: {maxWidth}px;"
		transition:flyAndScale
		on:mouseleave={handleContentMouseLeave}
	>
		<slot />
	</div>
{/if}
