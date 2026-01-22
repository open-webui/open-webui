<script lang="ts">
	import { onMount, onDestroy, tick } from 'svelte';

	// Whether to render the full content
	export let visible = false;
	// Minimum height for placeholder (prevents layout shift)
	export let minHeight = '100px';
	// Root margin for IntersectionObserver (load content before it enters viewport)
	export let rootMargin = '200px 0px';
	// Whether to keep content rendered after it becomes visible (recommended for chat)
	export let keepRendered = true;
	// Force visible (for streaming messages that are being actively updated)
	export let forceVisible = false;

	let containerElement: HTMLElement;
	let observer: IntersectionObserver | null = null;
	let hasBeenVisible = false;

	$: isVisible = forceVisible || visible || (keepRendered && hasBeenVisible);

	onMount(() => {
		if (forceVisible) {
			visible = true;
			hasBeenVisible = true;
			return;
		}

		observer = new IntersectionObserver(
			(entries) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						visible = true;
						hasBeenVisible = true;
						if (keepRendered && observer) {
							// Stop observing once visible if we want to keep it rendered
							observer.unobserve(containerElement);
						}
					} else if (!keepRendered) {
						visible = false;
					}
				});
			},
			{
				root: null, // viewport
				rootMargin: rootMargin,
				threshold: 0
			}
		);

		observer.observe(containerElement);
	});

	onDestroy(() => {
		if (observer) {
			observer.disconnect();
			observer = null;
		}
	});
</script>

<div
	bind:this={containerElement}
	class="lazy-content-container"
	style={!isVisible ? `min-height: ${minHeight};` : ''}
>
	{#if isVisible}
		<slot />
	{:else}
		<slot name="placeholder">
			<div class="lazy-content-placeholder" style="min-height: {minHeight};">
				<div class="animate-pulse flex flex-col gap-2 p-2">
					<div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
					<div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
				</div>
			</div>
		</slot>
	{/if}
</div>

<style>
	.lazy-content-container {
		width: 100%;
	}

	.lazy-content-placeholder {
		display: flex;
		align-items: center;
		justify-content: flex-start;
		width: 100%;
	}
</style>
