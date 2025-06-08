<script lang="ts">
	import { createEventDispatcher, onDestroy, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	let loaderElement: HTMLElement;

	let observer;
	let intervalId;

	onMount(() => {
		observer = new IntersectionObserver(
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
				root: null, // viewport
				rootMargin: '0px',
				threshold: 0.1 // When 10% of the loader is visible
			}
		);

		observer.observe(loaderElement);
	});

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
