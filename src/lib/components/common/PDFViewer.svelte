<script lang="ts">
	import { onMount, onDestroy, getContext } from 'svelte';
	import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.mjs?url';
	import panzoom, { type PanZoom } from 'panzoom';
	import Spinner from './Spinner.svelte';
	import Tooltip from './Tooltip.svelte';
	import Reset from '../icons/Reset.svelte';

	const i18n = getContext('i18n');

	export let url: string | null = null;
	export let data: ArrayBuffer | Uint8Array | null = null;
	export let className = 'w-full h-[70vh]';

	let outerContainer: HTMLDivElement;
	let sceneElement: HTMLDivElement;
	let loading = true;
	let error = '';
	let pdfDoc: any = null;
	let pzInstance: PanZoom | null = null;

	const initPanzoom = () => {
		if (pzInstance) {
			pzInstance.dispose();
		}
		if (sceneElement) {
			pzInstance = panzoom(sceneElement, {
				bounds: true,
				boundsPadding: 0.1,
				zoomSpeed: 0.065
			});
		}
	};

	const resetView = () => {
		if (pzInstance) {
			pzInstance.moveTo(0, 0);
			pzInstance.zoomAbs(0, 0, 1);
		}
	};

	const renderAllPages = async () => {
		if (!pdfDoc || !sceneElement) return;

		// Clear previous canvases
		sceneElement.innerHTML = '';

		for (let i = 1; i <= pdfDoc.numPages; i++) {
			const page = await pdfDoc.getPage(i);
			const viewport = page.getViewport({ scale: 1 });

			// Scale to fit container width
			const containerWidth = outerContainer?.clientWidth || 800;
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

			sceneElement.appendChild(canvas);

			const ctx = canvas.getContext('2d');
			await page.render({
				canvasContext: ctx,
				viewport: scaledViewport
			}).promise;
		}

		initPanzoom();
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

	onMount(() => {
		loadPdf();
	});

	onDestroy(() => {
		pzInstance?.dispose();
		if (pdfDoc) {
			pdfDoc.destroy();
			pdfDoc = null;
		}
	});
</script>

<div class="relative overflow-hidden {className}" bind:this={outerContainer}>
	<div bind:this={sceneElement} class="w-full">
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

	{#if !loading && !error && pdfDoc}
		<div class="absolute top-2 right-2 z-10">
			<Tooltip content={$i18n.t('Reset view')}>
				<button
					class="p-1.5 rounded-lg bg-white/80 dark:bg-gray-850/80 backdrop-blur-sm shadow-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
					on:click={resetView}
				>
					<Reset className="size-4" />
				</button>
			</Tooltip>
		</div>
	{/if}
</div>
