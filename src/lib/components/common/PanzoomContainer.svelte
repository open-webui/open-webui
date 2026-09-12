<script lang="ts">
	import { onMount } from 'svelte';
	import panzoom, { type PanZoom, type PanZoomOptions } from 'panzoom';

	const defaultOpts: PanZoomOptions = {
		bounds: true,
		boundsPadding: 0.1,
		pinchSpeed: 3.5,
		beforeWheel: () => true
	};

	export let className = '';
	export let options: Partial<PanZoomOptions> = {};
	export let zoomLevel = 1;

	let containerElement: HTMLElement;
	let instance: PanZoom | undefined;

	const updateZoomLevel = () => {
		zoomLevel = instance?.getTransform().scale ?? 1;
	};

	const handleWheel = (e: WheelEvent) => {
		if (!instance || !containerElement) return;

		if (!e.ctrlKey && !e.metaKey) {
			const transform = instance.getTransform();
			if (Math.abs(transform.scale - 1) < 0.01) return;
			if (Math.abs(e.deltaY) >= Math.abs(e.deltaX)) return;

			e.preventDefault();
			instance.moveBy(-e.deltaX, -e.deltaY);
			updateZoomLevel();
			return;
		}

		e.preventDefault();

		const rect = containerElement.getBoundingClientRect();
		instance.zoomTo(e.clientX - rect.left, e.clientY - rect.top, Math.exp(-e.deltaY * 0.002));
		updateZoomLevel();
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

<div bind:this={containerElement} class={className} on:wheel|nonpassive={handleWheel}>
	<slot />
</div>
