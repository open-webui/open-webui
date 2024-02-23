<script lang="ts">
	import ImagePreview from './ImagePreview.svelte';

	export let src = '';
	export let alt = '';

	let showImagePreview = false;
</script>

<ImagePreview bind:show={showImagePreview} {src} {alt} />
<button
	on:click={() => {
		console.log('image preview');
		showImagePreview = true;
	}}
>
	<img {src} {alt} class=" max-h-96 rounded-lg" draggable="false" />
</button>
