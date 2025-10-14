<script lang="ts">
	import { createEventDispatcher, onDestroy, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	export let scrollContainer: HTMLElement | null = null;

	let loaderElement: HTMLElement;

	let observer;
	let intervalId;

	function createObserver() {
		return new IntersectionObserver(
			(entries, observer) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						intervalId = setInterval(() => {
							dispatch('visible');
						}, 100);
						// dispatch('visible');
						// observer.unobserve(loaderElement); // Stop observing until content is loaded
					} else {
						clearInterval(intervalId);
					}
				});
			},
			{
				root: scrollContainer,
				rootMargin: '0px',
				threshold: 0.1 // When 10% of the loader is visible
			}
		);
	}

	onMount(() => {
		observer = createObserver();
		observer.observe(loaderElement);
	});

	// Reactively recreate observer when scrollContainer changes after mount
	$: if (observer && scrollContainer !== undefined) {
		observer.disconnect();
		observer = createObserver();
		observer.observe(loaderElement);
	}

	onDestroy(() => {
		if (observer) {
			observer.disconnect();
		}

		if (intervalId) {
			clearInterval(intervalId);
		}
	});
</script>

<div bind:this={loaderElement}>
	<slot />
</div>
