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
	let wheelDelta = 0;
	let lastWheelNavigationAt = 0;
	let lastScrolledSlide = -1;
	let thumbnailButtons: Array<HTMLButtonElement | undefined> = [];
	const slideShortcutKeys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'];
	const wheelNavigationThreshold = 80;
	const wheelNavigationCooldown = 450;

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
		void tick().then(() => {
			updateFitScale();
			scrollSelectedThumbnailIntoView();
		});
	};

	const trackThumbnail = (node: HTMLButtonElement, index: number) => {
		thumbnailButtons[index] = node;
		return {
			destroy: () => {
				if (thumbnailButtons[index] === node) thumbnailButtons[index] = undefined;
			}
		};
	};

	const scrollSelectedThumbnailIntoView = () => {
		if (hideThumbs) return;
		thumbnailButtons[safeSlide]?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
	};

	const initPanzoom = () => {
		if (!sceneEl) return;

		pzInstance?.dispose();
		pzInstance = panzoom(sceneEl, {
			bounds: true,
			boundsPadding: 0.1,
			pinchSpeed: 3.5,
			filterKey: (e?: KeyboardEvent) => !!e && slideShortcutKeys.includes(e.key),
			beforeWheel: () => true,
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
		const nextSlide = Math.min(Math.max(0, index), Math.max(0, slides.length - 1));
		if (nextSlide === safeSlide) return;

		currentSlide = nextSlide;
		void tick().then(() => {
			updateFitScale();
			resetView();
		});
	};

	const handleKeyDown = (e: KeyboardEvent) => {
		if (
			e.defaultPrevented ||
			e.altKey ||
			e.ctrlKey ||
			e.metaKey ||
			slides.length === 0 ||
			!slideShortcutKeys.includes(e.key)
		) {
			return;
		}

		e.preventDefault();
		if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
			selectSlide(safeSlide - 1);
		} else {
			selectSlide(safeSlide + 1);
		}
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
		if (e.ctrlKey || e.metaKey) {
			if (!pzInstance || !sceneEl) return;

			e.preventDefault();

			const rect = sceneEl.getBoundingClientRect();
			pzInstance.zoomTo(e.clientX - rect.left, e.clientY - rect.top, Math.exp(-e.deltaY * 0.002));
			zoomLevel = pzInstance.getTransform().scale;
			return;
		}

		const transform = pzInstance?.getTransform();
		if (
			transform &&
			Math.abs(transform.scale - 1) >= 0.01 &&
			Math.abs(e.deltaX) > Math.abs(e.deltaY)
		) {
			e.preventDefault();
			pzInstance?.moveBy(-e.deltaX, -e.deltaY);
			zoomLevel = pzInstance?.getTransform().scale ?? 1;
			return;
		}

		e.preventDefault();
		if (slides.length <= 1) return;

		const multiplier = e.deltaMode === 1 ? 16 : e.deltaMode === 2 ? stageEl.clientHeight : 1;
		const dominantDelta = Math.abs(e.deltaY) >= Math.abs(e.deltaX) ? e.deltaY : e.deltaX;
		wheelDelta += dominantDelta * multiplier;

		const now = Date.now();
		if (Math.abs(wheelDelta) < wheelNavigationThreshold) return;
		if (now - lastWheelNavigationAt < wheelNavigationCooldown) {
			wheelDelta = 0;
			return;
		}

		lastWheelNavigationAt = now;
		selectSlide(safeSlide + (wheelDelta > 0 ? 1 : -1));
		wheelDelta = 0;
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

	$: if (mounted && safeSlide !== lastScrolledSlide) {
		lastScrolledSlide = safeSlide;
		void tick().then(scrollSelectedThumbnailIntoView);
	}

	onDestroy(() => {
		pzInstance?.dispose();
		resizeObserver?.disconnect();
	});
</script>

<svelte:window on:keydown={handleKeyDown} />

<div
	bind:this={rootEl}
	class="relative grid {hideThumbs
		? 'grid-cols-[minmax(0,1fr)]'
		: 'grid-cols-[144px_minmax(0,1fr)]'} h-full min-h-0 bg-transparent text-gray-900 dark:text-gray-100 {className}"
>
	<aside
		class={hideThumbs
			? 'hidden'
			: 'pptx-slide-rail overflow-y-auto px-2 pt-3 pb-16 border-r border-gray-50 dark:border-gray-850/30 bg-transparent'}
		aria-label="Slides"
	>
		{#each slides as slide, index}
			<button
				use:trackThumbnail={index}
				type="button"
				class="grid grid-cols-[20px_minmax(0,1fr)] items-start gap-2 w-full mb-3 p-0 text-left text-gray-900 dark:text-gray-100"
				on:click={() => selectSlide(index)}
				aria-label="Slide {index + 1}"
				aria-current={safeSlide === index ? 'true' : undefined}
			>
				<span
					class="pt-1.5 text-[0.6875rem] font-medium text-right {safeSlide === index
						? 'text-gray-400 dark:text-gray-500'
						: 'text-gray-300/70 dark:text-gray-700'}">{index + 1}</span
				>
				<span
					class="block aspect-video overflow-hidden rounded-md bg-transparent {safeSlide === index
						? 'opacity-100'
						: 'opacity-55 hover:opacity-80'}"
				>
					<img
						src={slide}
						alt="Slide {index + 1} thumbnail"
						class="block w-full h-full object-contain"
						draggable="false"
					/>
				</span>
			</button>
		{/each}
	</aside>

	<section
		bind:this={stageEl}
		class="min-w-0 min-h-0 overflow-hidden flex items-center justify-center overscroll-contain"
		on:wheel|nonpassive={handleStageWheel}
	>
		{#if selectedSlide}
			<div
				bind:this={sceneEl}
				class="shrink-0"
				style="width: {slideWidth}px; height: {slideHeight}px;"
			>
				<img
					bind:this={slideImgEl}
					src={selectedSlide}
					alt="Slide {safeSlide + 1}"
					class="block w-full h-full object-contain rounded"
					draggable="false"
					on:load={onSlideLoad}
				/>
			</div>
		{/if}
	</section>

	{#if slides.length > 0}
		<div
			class="absolute bottom-3 {hideThumbs
				? 'left-1/2'
				: 'left-[calc(144px+(100%-144px)/2)]'} -translate-x-1/2 z-10 flex items-center gap-0.5 rounded-lg bg-white/90 dark:bg-gray-850/90 backdrop-blur-sm shadow-lg border border-gray-200/60 dark:border-gray-700/60 px-1 py-0.5"
		>
			<button
				type="button"
				class="shrink-0 min-w-7 h-7 inline-flex items-center justify-center p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400 disabled:opacity-30"
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
			<span
				class="shrink-0 min-w-12 text-center text-[0.6875rem] text-gray-500 dark:text-gray-400 tabular-nums"
				>{safeSlide + 1} / {slides.length}</span
			>
			<button
				type="button"
				class="shrink-0 min-w-7 h-7 inline-flex items-center justify-center p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400 disabled:opacity-30"
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
			<button
				type="button"
				class="shrink-0 min-w-7 h-7 inline-flex items-center justify-center p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
				on:click={zoomOut}
				aria-label="Zoom out"
			>
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
			<button
				type="button"
				class="shrink-0 min-w-12 h-7 px-1.5 py-1 text-center text-[0.6875rem] font-normal text-gray-500 dark:text-gray-400 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition tabular-nums"
				on:click={resetView}
				aria-label="Reset zoom"
			>
				{Math.round(zoomLevel * 100)}%
			</button>
			<button
				type="button"
				class="shrink-0 min-w-7 h-7 inline-flex items-center justify-center p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
				on:click={zoomIn}
				aria-label="Zoom in"
			>
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
	.pptx-slide-rail {
		scrollbar-color: transparent transparent;
	}

	.pptx-slide-rail:hover,
	.pptx-slide-rail:focus,
	.pptx-slide-rail:focus-within,
	.pptx-slide-rail:active {
		scrollbar-color: rgba(215, 215, 215, 0.6) transparent;
	}

	:global(.dark) .pptx-slide-rail:hover,
	:global(.dark) .pptx-slide-rail:focus,
	:global(.dark) .pptx-slide-rail:focus-within,
	:global(.dark) .pptx-slide-rail:active {
		scrollbar-color: rgba(67, 67, 67, 0.6) transparent;
	}

	.pptx-slide-rail::-webkit-scrollbar-thumb {
		visibility: hidden;
	}

	.pptx-slide-rail:hover::-webkit-scrollbar-thumb,
	.pptx-slide-rail:focus::-webkit-scrollbar-thumb,
	.pptx-slide-rail:focus-within::-webkit-scrollbar-thumb,
	.pptx-slide-rail:active::-webkit-scrollbar-thumb {
		visibility: visible;
	}

	.pptx-slide-rail::-webkit-scrollbar-corner {
		display: none;
	}
</style>
