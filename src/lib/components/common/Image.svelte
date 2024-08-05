<script lang="ts">
	import { WEBUI_BASE_URL } from '$lib/constants';
	import ImagePreview from './ImagePreview.svelte';

	export let src = '';
	export let alt = '';

	export let className = '';

	let _src = '';
	$: _src = src.startsWith('/') ? `${WEBUI_BASE_URL}${src}` : src;

	let showImagePreview = false;
</script>

<div class={className}>
	<!-- svelte-ignore a11y-click-events-have-key-events -->
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<img
		on:click={() => {
			showImagePreview = true;
		}}
		src={_src}
		{alt}
		class=" rounded-lg cursor-pointer"
		draggable="false"
		data-cy="image"
	/>
</div>
<ImagePreview bind:show={showImagePreview} src={_src} {alt} />
