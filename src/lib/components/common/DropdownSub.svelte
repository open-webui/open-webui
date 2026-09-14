<script lang="ts">
	import { flyAndScale } from '$lib/utils/transitions';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import { settings } from '$lib/stores';
	import { tick } from 'svelte';

	/** CSS classes for the sub-content container */
	export let contentClass =
		'select-none rounded-2xl p-1 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg border border-gray-100 dark:border-gray-800';

	/** Max width in px, enforced at the component level */
	export let maxWidth = 200;

	/** Side offset from the trigger in px (visual gap, bridged by invisible padding) */
	export let sideOffset = 8;

	let open = false;
	let triggerEl: HTMLElement | null = null;
	let contentEl: HTMLElement | null = null;

	function trigger(node: HTMLElement) {
		triggerEl = (node.firstElementChild as HTMLElement | null) || node;

		async function handleClick(event: MouseEvent) {
			event.preventDefault();
			await openSub(true);
		}

		async function handleKeydown(event: KeyboardEvent) {
			if (!['Enter', ' ', 'ArrowRight'].includes(event.key)) return;

			event.preventDefault();
			await openSub(true);
		}

		node.addEventListener('click', handleClick);
		node.addEventListener('keydown', handleKeydown);

		return {
			destroy() {
				node.removeEventListener('click', handleClick);
				node.removeEventListener('keydown', handleKeydown);
			}
		};
	}

	function positionContent() {
		if (!triggerEl || !contentEl) return;
		const rect = triggerEl.getBoundingClientRect();

		contentEl.style.position = 'fixed';
		contentEl.style.zIndex = '99999';

		// Reset bridge padding
		contentEl.style.paddingLeft = '0';
		contentEl.style.paddingRight = '0';

		// Inherit min-width from parent dropdown container (apply to inner content)
		const innerContent = contentEl.firstElementChild as HTMLElement | null;
		const parentContainer = triggerEl.closest('[class*="rounded"]')?.parentElement;
		if (parentContainer && innerContent) {
			const parentWidth = parentContainer.offsetWidth;
			if (parentWidth > 0) {
				innerContent.style.minWidth = `${parentWidth}px`;
			}
		}

		// Measure the inner content width for positioning decisions
		const contentWidth = innerContent?.offsetWidth || 200;
		const rightSpace = window.innerWidth - rect.right;

		if (rightSpace >= contentWidth + sideOffset) {
			// Open to the right: position flush with trigger, bridge gap with left padding
			contentEl.style.left = `${rect.right}px`;
			contentEl.style.right = 'auto';
			contentEl.style.paddingLeft = `${sideOffset}px`;
		} else {
			// Open to the left: position flush with trigger, bridge gap with right padding
			contentEl.style.right = `${window.innerWidth - rect.left}px`;
			contentEl.style.left = 'auto';
			contentEl.style.paddingRight = `${sideOffset}px`;
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

	async function openSub(focus = false) {
		open = true;
		await tick();
		positionContent();
		// Re-position after transition starts rendering real dimensions
		setTimeout(positionContent, 50);

		if (focus) {
			contentEl?.focus();
		}
	}

	async function handleMouseEnter() {
		await openSub();
	}

	function handleContentKeydown(event: KeyboardEvent) {
		if (event.key !== 'Escape') return;

		event.stopPropagation();
		open = false;
		triggerEl?.focus();
	}

	function handleMouseLeave(event: MouseEvent) {
		const relatedTarget = event.relatedTarget as Node | null;

		// Don't close if moving to the sub-content (including its bridge padding)
		if (relatedTarget && contentEl?.contains(relatedTarget)) return;
		if (relatedTarget && triggerEl?.contains(relatedTarget)) return;
		open = false;
	}

	function handleContentMouseLeave(event: MouseEvent) {
		const relatedTarget = event.relatedTarget as Node | null;

		if (relatedTarget && triggerEl?.contains(relatedTarget)) return;
		if (relatedTarget && contentEl?.contains(relatedTarget)) return;
		open = false;
	}

	function portal(node: HTMLElement) {
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
	use:trigger
	class="w-full {($settings?.highContrastMode ?? false)
		? '[&>button:hover]:bg-gray-200! dark:[&>button:hover]:bg-gray-800!'
		: '[&>button:hover]:bg-gray-50/60 dark:[&>button:hover]:bg-gray-800/60'}"
	on:mouseenter={handleMouseEnter}
	on:mouseleave={handleMouseLeave}
>
	<slot name="trigger" />
</div>

{#if open}
	<!-- svelte-ignore a11y-no-static-element-interactions -->
	<!-- Outer wrapper: positioned flush with trigger, invisible padding bridges the gap -->
	<div
		use:portal
		bind:this={contentEl}
		role="menu"
		tabindex="-1"
		on:mouseleave={handleContentMouseLeave}
		on:keydown={handleContentKeydown}
	>
		<!-- Inner content: visual styles and transition -->
		<div transition:flyAndScale>
			<DropdownMenu className={contentClass} style="max-width: {maxWidth}px;">
				<slot />
			</DropdownMenu>
		</div>
	</div>
{/if}
