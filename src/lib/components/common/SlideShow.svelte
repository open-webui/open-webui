<script lang="ts">
	import { onMount } from 'svelte';

	export let imageUrls = [
		'/assets/images/adam.jpg',
		'/assets/images/galaxy.jpg',
		'/assets/images/earth.jpg',
		'/assets/images/space.jpg'
	];
	export let duration = 5000;
	let selectedImageIdx = 0;

	onMount(() => {
		setInterval(() => {
			selectedImageIdx = (selectedImageIdx + 1) % (imageUrls.length - 1);
		}, duration);
	});
</script>

{#each imageUrls as imageUrl, idx (idx)}
	<div
		class="image w-full h-full absolute top-0 left-0 bg-cover bg-center transition-opacity duration-1000"
		style="opacity: {selectedImageIdx === idx ? 1 : 0}; background-image: url('{imageUrl}')"
	></div>
{/each}

<style>
	.image {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		background-size: cover;
		background-position: center; /* Center the background images */
		transition: opacity 1s ease-in-out; /* Smooth fade effect */
		opacity: 0; /* Make images initially not visible */
	}
</style>
