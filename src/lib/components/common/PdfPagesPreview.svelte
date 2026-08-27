<script lang="ts">
	import { onDestroy } from 'svelte';
	import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';
	import Spinner from './Spinner.svelte';
	import PptxPreview from './PptxPreview.svelte';

	export let data: ArrayBuffer | Uint8Array | null = null;
	export let currentSlide = 0;
	export let className = '';
	export let targetPage: number | null = null;

	type PdfDocument = import('pdfjs-dist').PDFDocumentProxy;

	let loading = false;
	let error = '';
	let slides: string[] = [];
	let pagesPreviewRef: PptxPreview;
	let pdfDoc: PdfDocument | null = null;
	let loadToken = 0;

	const loadPdf = async (pdfData: ArrayBuffer | Uint8Array) => {
		const token = ++loadToken;
		loading = true;
		error = '';
		slides = [];

		try {
			const pdfjs = await import('pdfjs-dist');
			pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

			pdfDoc?.destroy();
			pdfDoc = await pdfjs.getDocument({ data: pdfData }).promise;

			const renderedSlides: string[] = [];
			for (let i = 1; i <= pdfDoc.numPages; i++) {
				if (token !== loadToken) return;

				const page = await pdfDoc.getPage(i);
				const viewport = page.getViewport({ scale: 2 });
				const canvas = document.createElement('canvas');
				canvas.width = viewport.width;
				canvas.height = viewport.height;

				const ctx = canvas.getContext('2d');
				if (!ctx) continue;

				await page.render({ canvas, canvasContext: ctx, viewport }).promise;
				renderedSlides.push(canvas.toDataURL('image/png'));
			}

			if (token === loadToken) slides = renderedSlides;
		} catch (e) {
			console.error('PDF deck render error:', e);
			if (token === loadToken) error = 'Failed to load preview.';
		} finally {
			if (token === loadToken) loading = false;
		}
	};

	$: if (data) {
		void loadPdf(data);
	}

	export const resetView = () => {
		pagesPreviewRef?.resetView();
	};

	onDestroy(() => {
		loadToken++;
		pdfDoc?.destroy();
	});
</script>

{#if loading}
	<div class="flex h-full items-center justify-center {className}">
		<Spinner className="size-5" />
	</div>
{:else if error}
	<div class="flex h-full items-center justify-center text-sm text-red-500 {className}">
		{error}
	</div>
{:else}
	<PptxPreview
		bind:this={pagesPreviewRef}
		{slides}
		bind:currentSlide
		{targetPage}
		{className}
		itemLabel="Page"
		listLabel="Pages"
	/>
{/if}
