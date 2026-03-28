<script lang="ts">
	import { fade, slide } from 'svelte/transition';
	import { onMount, onDestroy } from 'svelte';

	export let show = false;
	export let side = 'right';
	export let width = '200px';

	export let className = '';
	export let duration = 100;

	// WCAG 2.1 AA: Accessible labels
	export let ariaLabel = 'Sidebar';

	let sidebarElement: HTMLElement | null = null;

	// WCAG 2.1.1: Keyboard navigation - Escape key closes sidebar
	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Escape' && show) {
			event.preventDefault();
			show = false;
		}
	};

	// WCAG 2.4.3: Focus management
	$: if (show && sidebarElement) {
		// Focus first interactive element in sidebar
		setTimeout(() => {
			const focusable = sidebarElement?.querySelector(
				'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
			) as HTMLElement;
			focusable?.focus();
		}, duration + 10);
	}

	onMount(() => {
		window.addEventListener('keydown', handleKeyDown);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', handleKeyDown);
	});
</script>

{#if show}
	<div
		class="absolute z-20 top-0 right-0 left-0 bottom-0 bg-white/20 dark:bg-black/5 w-full min-h-full h-full flex justify-center overflow-hidden overscroll-contain"
		on:mousedown={() => {
			show = false;
		}}
		on:keydown={handleKeyDown}
		transition:fade={{ duration: duration }}
		role="presentation"
	/>

	<aside
		bind:this={sidebarElement}
		class="absolute z-30 shadow-xl {side === 'right' ? 'right-0' : 'left-0'} top-0 bottom-0"
		transition:slide={{ duration: duration, axis: side === 'right' ? 'x' : 'y' }}
		role="complementary"
		aria-label={ariaLabel}
	>
		<div class="{className} h-full" style="width: {show ? width : '0px'}">
			<slot />
		</div>
	</aside>
{/if}
