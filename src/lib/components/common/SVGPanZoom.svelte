<script lang="ts">
	import { onMount } from 'svelte';
	import panzoom from 'panzoom';

	import DOMPurify from 'dompurify';

	export let className = '';
	export let svg = '';

	let instance;

	let sceneParentElement: HTMLElement;
	let sceneElement: HTMLElement;

	$: if (sceneElement) {
		instance = panzoom(sceneElement, {
			bounds: true,
			boundsPadding: 0.1,

			zoomSpeed: 0.065
		});
	}
</script>

<div bind:this={sceneParentElement} class={className}>
	<div bind:this={sceneElement} class="flex h-full max-h-full justify-center items-center">
		{@html svg}
	</div>
</div>
