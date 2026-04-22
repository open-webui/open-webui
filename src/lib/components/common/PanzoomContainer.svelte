<script lang="ts">
	import { onMount } from 'svelte';
	import panzoom, { type PanZoom, type PanZoomOptions } from 'panzoom';

	const defaultOpts: PanZoomOptions = {
		bounds: true,
		boundsPadding: 0.1,
		zoomSpeed: 0.065
	};

	export let className = '';
	export let options: Partial<PanZoomOptions> = {};

	let containerElement: HTMLElement;
	let instance: PanZoom | undefined;

	export const reset = () => {
		instance?.moveTo(0, 0);
		instance?.zoomAbs(0, 0, 1);
	};

	onMount(() => {
		const localInstance = panzoom(containerElement, { ...defaultOpts, ...options });
		instance = localInstance;
		return () => {
			localInstance.dispose();
		};
	});
</script>

<div bind:this={containerElement} class={className}>
	<slot />
</div>
