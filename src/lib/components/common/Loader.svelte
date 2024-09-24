<script lang="ts">
	import { createEventDispatcher, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	let loaderElement: HTMLElement;

	onMount(() => {
		const observer = new IntersectionObserver(
			(entries, observer) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						dispatch('visible');
						// observer.unobserve(loaderElement); // Stop observing until content is loaded
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
</script>

<div bind:this={loaderElement}>
	<slot />
</div>
