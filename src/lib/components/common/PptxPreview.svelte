<script lang="ts">
	import { onDestroy, onMount, tick } from 'svelte';
	import panzoom, { type PanZoom } from 'panzoom';

	export let slides: string[] = [];
	export let currentSlide = 0;
	export let className = '';

	let rootEl: HTMLDivElement;
	let stageEl: HTMLElement;
	let sceneEl: HTMLDivElement;
	let slideImgEl: HTMLImageElement;
	let naturalWidth = 1280;
	let naturalHeight = 720;
	let fitScale = 1;
	let zoomLevel = 1;
	let resizeObserver: ResizeObserver | null = null;
	let pzInstance: PanZoom | null = null;
	let mounted = false;
	let initializedSlide = '';
	let hideThumbs = false;

	$: safeSlide = Math.min(Math.max(0, currentSlide), Math.max(0, slides.length - 1));
	$: selectedSlide = slides[safeSlide] ?? '';
	$: slideWidth = Math.max(1, Math.round(naturalWidth * fitScale));
	$: slideHeight = Math.max(1, Math.round(naturalHeight * fitScale));

	const updateFitScale = () => {
		if (!stageEl || !naturalWidth || !naturalHeight) return;
		const availableWidth = Math.max(320, stageEl.clientWidth - 64);
		const availableHeight = Math.max(220, stageEl.clientHeight - 64);
		fitScale = Math.min(1, availableWidth / naturalWidth, availableHeight / naturalHeight);
	};

	const updateLayout = () => {
		hideThumbs = (rootEl?.clientWidth ?? window.innerWidth) < 720;
		void tick().then(updateFitScale);
	};

	const initPanzoom = () => {
		if (!sceneEl) return;

		pzInstance?.dispose();
		pzInstance = panzoom(sceneEl, {
			bounds: true,
			boundsPadding: 0.1,
			zoomSpeed: 0.065,
			beforeWheel: (e) => {
				if (!e.ctrlKey && !e.metaKey) return true;
				return false;
			},
			beforeMouseDown: () => {
				const transform = pzInstance?.getTransform();
				return !!transform && Math.abs(transform.scale - 1) < 0.01;
			}
		});
		pzInstance.on('zoom', () => {
			zoomLevel = pzInstance?.getTransform()?.scale ?? 1;
		});
		pzInstance.on('pan', () => {
			zoomLevel = pzInstance?.getTransform()?.scale ?? 1;
		});
	};

	const selectSlide = (index: number) => {
		currentSlide = index;
		void tick().then(() => {
			updateFitScale();
			resetView();
		});
	};

	const zoomIn = () => {
		if (!pzInstance || !stageEl) return;
		pzInstance.zoomTo(stageEl.clientWidth / 2, stageEl.clientHeight / 2, 1.25);
		zoomLevel = pzInstance.getTransform().scale;
	};

	const zoomOut = () => {
		if (!pzInstance || !stageEl) return;
		pzInstance.zoomTo(stageEl.clientWidth / 2, stageEl.clientHeight / 2, 0.8);
		zoomLevel = pzInstance.getTransform().scale;
	};

	export const resetView = () => {
		pzInstance?.moveTo(0, 0);
		pzInstance?.zoomAbs(0, 0, 1);
		zoomLevel = 1;
		updateFitScale();
	};

	const onSlideLoad = () => {
		if (slideImgEl?.naturalWidth && slideImgEl?.naturalHeight) {
			naturalWidth = slideImgEl.naturalWidth;
			naturalHeight = slideImgEl.naturalHeight;
		}
		updateFitScale();
		resetView();
	};

	const handleStageWheel = (e: WheelEvent) => {
		if (e.ctrlKey || e.metaKey || !pzInstance) return;

		e.preventDefault();
		const multiplier = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? stageEl.clientHeight : 1;
		pzInstance.moveBy(-e.deltaX * multiplier, -e.deltaY * multiplier, false);
		zoomLevel = pzInstance.getTransform().scale;
	};

	onMount(() => {
		mounted = true;
		resizeObserver = new ResizeObserver(updateLayout);
		if (rootEl) resizeObserver.observe(rootEl);
		if (stageEl) resizeObserver.observe(stageEl);
		updateLayout();
	});

	$: if (mounted && selectedSlide && selectedSlide !== initializedSlide) {
		initializedSlide = selectedSlide;
		void tick().then(() => {
			initPanzoom();
			resetView();
		});
	}

	onDestroy(() => {
		pzInstance?.dispose();
		resizeObserver?.disconnect();
	});
</script>

<div bind:this={rootEl} class="pptx-preview {hideThumbs ? 'pptx-preview-compact' : ''} {className}">
	<aside class="pptx-thumbs" aria-label="Slides">
		{#each slides as slide, index}
			<button
				type="button"
				class="pptx-thumb {safeSlide === index ? 'pptx-thumb-selected' : ''}"
				on:click={() => selectSlide(index)}
				aria-label="Slide {index + 1}"
				aria-current={safeSlide === index ? 'true' : undefined}
			>
				<span class="pptx-thumb-number">{index + 1}</span>
				<span class="pptx-thumb-frame">
					<img src={slide} alt="Slide {index + 1} thumbnail" draggable="false" />
				</span>
			</button>
		{/each}
	</aside>

	<section bind:this={stageEl} class="pptx-stage" on:wheel|nonpassive={handleStageWheel}>
		{#if selectedSlide}
			<div
				bind:this={sceneEl}
				class="pptx-stage-inner"
				style="width: {slideWidth}px; height: {slideHeight}px;"
			>
				<img
					bind:this={slideImgEl}
					src={selectedSlide}
					alt="Slide {safeSlide + 1}"
					class="pptx-slide"
					draggable="false"
					on:load={onSlideLoad}
				/>
			</div>
		{/if}
	</section>

	{#if slides.length > 0}
		<div class="pptx-controls">
			<button
				type="button"
				class="pptx-control"
				disabled={safeSlide === 0}
				on:click={() => selectSlide(safeSlide - 1)}
				aria-label="Previous slide"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						fill-rule="evenodd"
						d="M11.78 5.22a.75.75 0 0 1 0 1.06L8.06 10l3.72 3.72a.75.75 0 1 1-1.06 1.06l-4.25-4.25a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<span class="pptx-count">{safeSlide + 1} / {slides.length}</span>
			<button
				type="button"
				class="pptx-control"
				disabled={safeSlide === slides.length - 1}
				on:click={() => selectSlide(safeSlide + 1)}
				aria-label="Next slide"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						fill-rule="evenodd"
						d="M8.22 5.22a.75.75 0 0 1 1.06 0l4.25 4.25a.75.75 0 0 1 0 1.06l-4.25 4.25a.75.75 0 0 1-1.06-1.06L11.94 10 8.22 6.28a.75.75 0 0 1 0-1.06Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<button type="button" class="pptx-control" on:click={zoomOut} aria-label="Zoom out">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						fill-rule="evenodd"
						d="M4 10a.75.75 0 0 1 .75-.75h10.5a.75.75 0 0 1 0 1.5H4.75A.75.75 0 0 1 4 10Z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<button type="button" class="pptx-zoom" on:click={resetView} aria-label="Reset zoom">
				{Math.round(zoomLevel * 100)}%
			</button>
			<button type="button" class="pptx-control" on:click={zoomIn} aria-label="Zoom in">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-3.5"
				>
					<path
						d="M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5a.75.75 0 0 0 0 1.5h4.5v4.5a.75.75 0 0 0 1.5 0v-4.5h4.5a.75.75 0 0 0 0-1.5h-4.5v-4.5Z"
					/>
				</svg>
			</button>
		</div>
	{/if}
</div>

<style>
	.pptx-preview {
		position: relative;
		display: grid;
		grid-template-columns: 160px minmax(0, 1fr);
		height: 100%;
		min-height: 0;
		background: transparent;
		color: #111827;
	}

	:global(.dark) .pptx-preview {
		color: #f3f4f6;
	}

	.pptx-thumbs {
		overflow-y: auto;
		padding: 14px 10px 64px;
		border-right: 1px solid rgba(17, 24, 39, 0.1);
		background: transparent;
	}

	:global(.dark) .pptx-thumbs {
		border-right-color: rgba(255, 255, 255, 0.1);
	}

	.pptx-thumb {
		display: grid;
		grid-template-columns: 24px minmax(0, 1fr);
		align-items: start;
		gap: 8px;
		width: 100%;
		margin: 0 0 14px;
		padding: 0;
		color: #111827;
		text-align: left;
	}

	:global(.dark) .pptx-thumb {
		color: #f3f4f6;
	}

	.pptx-thumb-number {
		padding-top: 7px;
		font-size: 0.75rem;
		font-weight: 500;
		color: #374151;
		text-align: right;
	}

	:global(.dark) .pptx-thumb-number {
		color: #f3f4f6;
	}

	.pptx-thumb-frame {
		display: block;
		aspect-ratio: 16 / 9;
		overflow: hidden;
		border-radius: 7px;
		background: #fff;
		border: 2px solid transparent;
		box-shadow: 0 1px 3px rgba(15, 23, 42, 0.18);
	}

	:global(.dark) .pptx-thumb-frame {
		box-shadow: 0 1px 2px rgba(0, 0, 0, 0.25);
	}

	.pptx-thumb-selected .pptx-thumb-frame {
		border-color: #60a5fa;
	}

	.pptx-thumb-selected .pptx-thumb-number {
		color: #93c5fd;
	}

	.pptx-thumb img {
		width: 100%;
		height: 100%;
		object-fit: contain;
		display: block;
	}

	.pptx-stage {
		min-width: 0;
		min-height: 0;
		overflow: hidden;
		display: flex;
		align-items: center;
		justify-content: center;
		overscroll-behavior: contain;
	}

	.pptx-stage-inner {
		flex: 0 0 auto;
	}

	.pptx-slide {
		display: block;
		width: 100%;
		height: 100%;
		object-fit: contain;
		border-radius: 5px;
		background: #fff;
		box-shadow: 0 1px 3px rgba(0, 0, 0, 0.35);
	}

	.pptx-controls {
		position: absolute;
		left: calc(160px + (100% - 160px) / 2);
		bottom: 12px;
		z-index: 2;
		display: flex;
		align-items: center;
		gap: 2px;
		transform: translateX(-50%);
		border: 1px solid rgba(255, 255, 255, 0.14);
		border-radius: 8px;
		background: rgba(255, 255, 255, 0.92);
		padding: 2px;
		box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
		backdrop-filter: blur(8px);
	}

	:global(.dark) .pptx-controls {
		border-color: rgba(255, 255, 255, 0.14);
		background: rgba(32, 32, 32, 0.88);
		box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
	}

	.pptx-control,
	.pptx-zoom {
		min-width: 28px;
		height: 28px;
		border-radius: 6px;
		color: #4b5563;
	}

	:global(.dark) .pptx-control,
	:global(.dark) .pptx-zoom {
		color: #d1d5db;
	}

	.pptx-control {
		display: inline-flex;
		align-items: center;
		justify-content: center;
	}

	.pptx-zoom {
		padding: 0 8px;
		font-size: 0.7rem;
		font-variant-numeric: tabular-nums;
	}

	.pptx-count {
		min-width: 48px;
		text-align: center;
		font-size: 0.7rem;
		color: #4b5563;
		font-variant-numeric: tabular-nums;
	}

	:global(.dark) .pptx-count {
		color: #d1d5db;
	}

	.pptx-control:hover:not(:disabled),
	.pptx-zoom:hover {
		background: rgba(17, 24, 39, 0.08);
	}

	:global(.dark) .pptx-control:hover:not(:disabled),
	:global(.dark) .pptx-zoom:hover {
		background: rgba(255, 255, 255, 0.1);
	}

	.pptx-control:disabled {
		opacity: 0.35;
	}

	.pptx-preview-compact {
		grid-template-columns: minmax(0, 1fr);
	}

	.pptx-preview-compact .pptx-thumbs {
		display: none;
	}

	.pptx-preview-compact .pptx-controls {
		left: 50%;
	}
</style>
