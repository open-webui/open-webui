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
	export let zoomLevel = 1;

	let containerElement: HTMLElement;
	let instance: PanZoom | undefined;

	const updateZoomLevel = () => {
		zoomLevel = instance?.getTransform().scale ?? 1;
	};

	const center = () => ({
		x: containerElement?.clientWidth ? containerElement.clientWidth / 2 : 0,
		y: containerElement?.clientHeight ? containerElement.clientHeight / 2 : 0
	});

	export const zoomIn = () => {
		if (!instance) return;
		const { x, y } = center();
		instance.zoomTo(x, y, 1.25);
		updateZoomLevel();
	};

	export const zoomOut = () => {
		if (!instance) return;
		const { x, y } = center();
		instance.zoomTo(x, y, 0.8);
		updateZoomLevel();
	};

	export const reset = () => {
		instance?.moveTo(0, 0);
		instance?.zoomAbs(0, 0, 1);
		updateZoomLevel();
	};

	onMount(() => {
		const localInstance = panzoom(containerElement, { ...defaultOpts, ...options });
		instance = localInstance;
		updateZoomLevel();
		localInstance.on('zoom', updateZoomLevel);
		return () => {
			localInstance.dispose();
		};
	});
</script>

<div bind:this={containerElement} class={className}>
	<slot />
</div>
