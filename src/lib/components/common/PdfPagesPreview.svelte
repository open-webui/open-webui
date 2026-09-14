<script lang="ts">
	import { onDestroy, onMount, tick } from 'svelte';
	import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';
	import Spinner from './Spinner.svelte';
	import PDFViewer from './PDFViewer.svelte';

	export let data: ArrayBuffer | Uint8Array | null = null;
	export let currentSlide = 0;
	export let className = '';
	export let targetPage: number | null = null;
	export let singlePage = false;
	export let itemLabel = 'Page';
	export let listLabel = 'Pages';

	type PdfDocument = import('pdfjs-dist').PDFDocumentProxy;

	let rootEl: HTMLDivElement;
	let pdfViewerRef: PDFViewer;
	let viewerData: ArrayBuffer | Uint8Array | null = null;
	let pageTarget: number | null = null;
	let thumbsLoading = false;
	let thumbnails: string[] = [];
	let thumbnailButtons: Array<HTMLButtonElement | undefined> = [];
	let hideThumbs = false;
	let resizeObserver: ResizeObserver | null = null;
	let pdfDoc: PdfDocument | null = null;
	let loadToken = 0;

	$: safePage = Math.min(Math.max(0, currentSlide), Math.max(0, thumbnails.length - 1));

	const copyPdfData = (pdfData: ArrayBuffer | Uint8Array) =>
		pdfData instanceof Uint8Array ? pdfData.slice() : pdfData.slice(0);

	const updateLayout = () => {
		hideThumbs = (rootEl?.clientWidth ?? window.innerWidth) < 720;
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
		thumbnailButtons[safePage]?.scrollIntoView({ block: 'nearest', inline: 'nearest' });
	};

	const selectPage = async (index: number) => {
		currentSlide = Math.min(Math.max(0, index), Math.max(0, thumbnails.length - 1));
		pageTarget = currentSlide + 1;
		await tick();
		await pdfViewerRef?.scrollToPage?.(pageTarget);
		scrollSelectedThumbnailIntoView();
	};

	const loadThumbnails = async (pdfData: ArrayBuffer | Uint8Array) => {
		const token = ++loadToken;
		thumbsLoading = true;
		thumbnails = [];

		try {
			const pdfjs = await import('pdfjs-dist');
			pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

			pdfDoc?.destroy();
			pdfDoc = await pdfjs.getDocument({ data: pdfData }).promise;

			const rendered: string[] = [];
			for (let i = 1; i <= pdfDoc.numPages; i++) {
				if (token !== loadToken) return;

				const page = await pdfDoc.getPage(i);
				const viewport = page.getViewport({ scale: 0.28 });
				const canvas = document.createElement('canvas');
				canvas.width = viewport.width;
				canvas.height = viewport.height;

				const ctx = canvas.getContext('2d');
				if (!ctx) continue;

				await page.render({ canvas, canvasContext: ctx, viewport }).promise;
				rendered.push(canvas.toDataURL('image/png'));
			}

			if (token === loadToken) thumbnails = rendered;
		} catch (e) {
			console.error('PDF thumbnail render error:', e);
			if (token === loadToken) thumbnails = [];
		} finally {
			if (token === loadToken) thumbsLoading = false;
		}
	};

	$: if (data) {
		viewerData = copyPdfData(data);
		void loadThumbnails(copyPdfData(data));
	} else {
		viewerData = null;
		thumbnails = [];
	}

	$: if (targetPage) {
		currentSlide = Math.max(0, targetPage - 1);
		pageTarget = targetPage;
	}

	$: if (thumbnails.length > 0) {
		void tick().then(scrollSelectedThumbnailIntoView);
	}

	export const resetView = () => {
		pdfViewerRef?.resetView();
	};

	const handlePageChange = (page: number) => {
		currentSlide = page - 1;
		if (singlePage) pageTarget = page;
		void tick().then(scrollSelectedThumbnailIntoView);
	};

	onMount(() => {
		resizeObserver = new ResizeObserver(updateLayout);
		if (rootEl) resizeObserver.observe(rootEl);
		updateLayout();
	});

	onDestroy(() => {
		loadToken++;
		resizeObserver?.disconnect();
		pdfDoc?.destroy();
	});
</script>

<div
	bind:this={rootEl}
	class="relative grid {hideThumbs
		? 'grid-cols-[minmax(0,1fr)]'
		: 'grid-cols-[144px_minmax(0,1fr)]'} min-h-0 bg-transparent text-gray-900 dark:text-gray-100 {className}"
>
	<aside
		class={hideThumbs
			? 'hidden'
			: 'thumbnail-sidebar overflow-y-auto px-2 pt-3 pb-16 border-r border-gray-50 dark:border-gray-850/30 bg-transparent'}
		aria-label={listLabel}
	>
		{#if thumbsLoading && thumbnails.length === 0}
			<div class="flex h-full items-center justify-center">
				<Spinner className="size-4" />
			</div>
		{:else}
			{#each thumbnails as thumbnail, index}
				<button
					use:trackThumbnail={index}
					type="button"
					class="grid grid-cols-[20px_minmax(0,1fr)] items-start gap-2 w-full mb-3 p-0 text-left text-gray-900 dark:text-gray-100"
					on:click={() => selectPage(index)}
					aria-label="{itemLabel} {index + 1}"
					aria-current={safePage === index ? 'true' : undefined}
				>
					<span
						class="pt-1.5 text-[0.6875rem] font-medium text-right {safePage === index
							? 'text-gray-400 dark:text-gray-500'
							: 'text-gray-300/70 dark:text-gray-700'}">{index + 1}</span
					>
					<span
						class="block overflow-hidden rounded-md bg-transparent {safePage === index
							? 'opacity-100'
							: 'opacity-55 hover:opacity-80'}"
					>
						<img
							src={thumbnail}
							alt="{itemLabel} {index + 1} thumbnail"
							class="block w-full h-full object-contain"
							draggable="false"
						/>
					</span>
				</button>
			{/each}
		{/if}
	</aside>

	<section class="min-w-0 min-h-0 overflow-hidden">
		{#if viewerData}
			<PDFViewer
				bind:this={pdfViewerRef}
				data={viewerData}
				targetPage={pageTarget}
				{singlePage}
				{itemLabel}
				onPageChange={handlePageChange}
				className="w-full h-full"
			/>
		{:else}
			<div class="flex h-full items-center justify-center">
				<Spinner className="size-5" />
			</div>
		{/if}
	</section>
</div>

<style>
	.thumbnail-sidebar {
		scrollbar-color: transparent transparent;
	}

	.thumbnail-sidebar:hover,
	.thumbnail-sidebar:focus,
	.thumbnail-sidebar:focus-within,
	.thumbnail-sidebar:active {
		scrollbar-color: rgba(215, 215, 215, 0.6) transparent;
	}

	:global(.dark) .thumbnail-sidebar:hover,
	:global(.dark) .thumbnail-sidebar:focus,
	:global(.dark) .thumbnail-sidebar:focus-within,
	:global(.dark) .thumbnail-sidebar:active {
		scrollbar-color: rgba(67, 67, 67, 0.6) transparent;
	}

	.thumbnail-sidebar::-webkit-scrollbar-thumb {
		visibility: hidden;
	}

	.thumbnail-sidebar:hover::-webkit-scrollbar-thumb,
	.thumbnail-sidebar:focus::-webkit-scrollbar-thumb,
	.thumbnail-sidebar:focus-within::-webkit-scrollbar-thumb,
	.thumbnail-sidebar:active::-webkit-scrollbar-thumb {
		visibility: visible;
	}

	.thumbnail-sidebar::-webkit-scrollbar-corner {
		display: none;
	}
</style>
