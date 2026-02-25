<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';
	import Spinner from './Spinner.svelte';

	export let url: string | null = null;
	export let data: ArrayBuffer | Uint8Array | null = null;
	export let className = 'w-full h-[70vh]';

	let container: HTMLDivElement;
	let loading = true;
	let error = '';
	let pdfDoc: any = null;

	const renderAllPages = async () => {
		if (!pdfDoc || !container) return;

		// Clear previous canvases
		container.innerHTML = '';

		for (let i = 1; i <= pdfDoc.numPages; i++) {
			const page = await pdfDoc.getPage(i);
			const viewport = page.getViewport({ scale: 1 });

			// Scale to fit container width
			const containerWidth = container.clientWidth || 800;
			const scale = containerWidth / viewport.width;
			const scaledViewport = page.getViewport({ scale });

			const canvas = document.createElement('canvas');
			canvas.width = scaledViewport.width;
			canvas.height = scaledViewport.height;
			canvas.style.width = '100%';
			canvas.style.height = 'auto';
			canvas.style.display = 'block';

			if (i > 1) {
				canvas.style.marginTop = '4px';
			}

			container.appendChild(canvas);

			const ctx = canvas.getContext('2d');
			await page.render({
				canvasContext: ctx,
				viewport: scaledViewport
			}).promise;
		}
	};

	const loadPdf = async () => {
		if (!url && !data) return;

		loading = true;
		error = '';

		try {
			const pdfjs = await import('pdfjs-dist');
			pdfjs.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

			let pdfData: ArrayBuffer | Uint8Array;
			if (data) {
				pdfData = data;
			} else {
				// Fetch with credentials so auth cookies are sent
				const res = await fetch(url!, { credentials: 'include' });
				if (!res.ok) throw new Error(`HTTP ${res.status}`);
				pdfData = await res.arrayBuffer();
			}
			pdfDoc = await pdfjs.getDocument({ data: pdfData }).promise;
			await renderAllPages();
		} catch (e) {
			console.error('PDF render error:', e);
			error = 'Failed to load PDF.';
		} finally {
			loading = false;
		}
	};

	// Re-render on resize
	let resizeObserver: ResizeObserver | null = null;

	onMount(() => {
		loadPdf();

		resizeObserver = new ResizeObserver(() => {
			if (pdfDoc && !loading) {
				renderAllPages();
			}
		});
		if (container) {
			resizeObserver.observe(container);
		}
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
		if (pdfDoc) {
			pdfDoc.destroy();
			pdfDoc = null;
		}
	});
</script>

<div class="overflow-auto {className}" bind:this={container}>
	{#if loading}
		<div class="flex items-center justify-center h-full">
			<Spinner className="size-5" />
		</div>
	{/if}

	{#if error}
		<div class="flex items-center justify-center h-full text-sm text-red-500">
			{error}
		</div>
	{/if}
</div>
