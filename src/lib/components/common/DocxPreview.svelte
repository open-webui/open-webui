<script lang="ts">
	import DOMPurify from 'dompurify';
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import type { Readable } from 'svelte/store';
	import { clampDocumentTargetPage } from '$lib/utils/documentPreview';

	import Spinner from './Spinner.svelte';

	type I18n = {
		t: (key: string, values?: Record<string, unknown>) => string;
	};

	const i18n = getContext<Readable<I18n>>('i18n');

	export let data: ArrayBuffer | null = null;
	export let className = '';
	export let targetPage: number | null = null;

	let outerContainer: HTMLDivElement;
	let containerEl: HTMLDivElement;
	let styleEl: HTMLDivElement;
	let fallbackHtml = '';
	let error = '';
	let loading = false;
	let renderId = 0;
	let mounted = false;
	let fitScale = 1;
	let zoomLevel = 1;
	let resizeObserver: ResizeObserver | null = null;

	$: docxScale = Math.max(0.25, fitScale * zoomLevel);

	const clearPreview = () => {
		if (containerEl) containerEl.innerHTML = '';
		if (styleEl) styleEl.innerHTML = '';
		fallbackHtml = '';
		error = '';
	};

	const updateFitScale = () => {
		const page = containerEl?.querySelector('section.docx') as HTMLElement | null;
		if (!outerContainer || !page) {
			fitScale = 1;
			return;
		}

		const computedWidth = parseFloat(getComputedStyle(page).width);
		const pageWidth = Number.isFinite(computedWidth)
			? computedWidth
			: page.getBoundingClientRect().width / docxScale;
		const availableWidth = Math.max(320, outerContainer.clientWidth - 32);
		fitScale = Math.min(1, availableWidth / pageWidth);
	};

	const zoomIn = () => {
		zoomLevel = Math.min(4, zoomLevel * 1.25);
	};

	const zoomOut = () => {
		zoomLevel = Math.max(0.25, zoomLevel * 0.8);
	};

	const handleWheel = (e: WheelEvent) => {
		if (!e.ctrlKey && !e.metaKey) return;
		if (!outerContainer) return;

		e.preventDefault();

		const oldScale = docxScale;
		const rect = outerContainer.getBoundingClientRect();
		const pointerX = e.clientX - rect.left + outerContainer.scrollLeft;
		const pointerY = e.clientY - rect.top + outerContainer.scrollTop;
		const factor = Math.exp(-e.deltaY * 0.002);

		zoomLevel = Math.max(0.25, Math.min(4, zoomLevel * factor));

		void tick().then(() => {
			const ratio = docxScale / oldScale;
			outerContainer.scrollLeft = pointerX * ratio - (e.clientX - rect.left);
			outerContainer.scrollTop = pointerY * ratio - (e.clientY - rect.top);
		});
	};

	export const resetView = () => {
		zoomLevel = 1;
		updateFitScale();
	};

	const scrollToTargetPage = async () => {
		if (!containerEl) return;
		const pages = containerEl.querySelectorAll('section.docx');
		const page = clampDocumentTargetPage(targetPage, pages.length);
		if (!page) return;

		await tick();
		(pages[page - 1] as HTMLElement | undefined)?.scrollIntoView({ block: 'start' });
	};

	const renderDocx = async (arrayBuffer: ArrayBuffer | null) => {
		const currentRender = ++renderId;
		clearPreview();
		zoomLevel = 1;

		if (!arrayBuffer || !containerEl || !styleEl) return;

		loading = true;
		await tick();

		try {
			const { renderAsync } = await import('docx-preview');

			if (currentRender !== renderId) return;

			await renderAsync(arrayBuffer.slice(0), containerEl, styleEl, {
				breakPages: true,
				className: 'docx',
				ignoreLastRenderedPageBreak: false,
				inWrapper: true,
				renderEndnotes: true,
				renderFooters: true,
				renderFootnotes: true,
				renderHeaders: true,
				useBase64URL: true
			});
			await tick();
			updateFitScale();
			await scrollToTargetPage();
		} catch (e) {
			console.error('Error rendering DOCX preview:', e);

			try {
				const { docxToHtml } = await import('$lib/utils/docxToHtml');
				if (currentRender !== renderId) return;
				fallbackHtml = DOMPurify.sanitize(await docxToHtml(arrayBuffer.slice(0)));
			} catch (fallbackError) {
				console.error('Error rendering DOCX fallback:', fallbackError);
				error = $i18n.t('Failed to load DOCX file. Please try downloading it instead.');
			}
		} finally {
			if (currentRender === renderId) loading = false;
		}
	};

	$: if (mounted) renderDocx(data);

	$: if (!loading && targetPage && !fallbackHtml) {
		void scrollToTargetPage();
	}

	onMount(() => {
		mounted = true;
		void tick().then(() => {
			if (!outerContainer) return;
			resizeObserver = new ResizeObserver(updateFitScale);
			resizeObserver.observe(outerContainer);
			updateFitScale();
		});
	});

	onDestroy(() => {
		renderId += 1;
		resizeObserver?.disconnect();
		clearPreview();
	});
</script>

<div
	class="relative min-h-full bg-transparent [&_.docx-wrapper]:flex [&_.docx-wrapper]:flex-col [&_.docx-wrapper]:items-center [&_.docx-wrapper]:!bg-transparent [&_.docx-wrapper]:pt-4 [&_.docx-wrapper]:pb-14 [&_.docx-wrapper>section.docx]:!mx-auto [&_.docx-wrapper>section.docx]:!mt-0 [&_.docx-wrapper>section.docx]:!mb-1 [&_.docx-wrapper>section.docx]:!bg-white [&_.docx-wrapper>section.docx]:!shadow-[0_1px_4px_rgba(0,0,0,0.18)] [&_.docx-wrapper>section.docx]:[zoom:var(--docx-scale)] {className}"
	style="--docx-scale: {docxScale};"
>
	<div bind:this={styleEl}></div>

	{#if loading}
		<div class="absolute inset-0 flex items-center justify-center bg-white/70 dark:bg-gray-950/60">
			<Spinner className="size-4" />
		</div>
	{/if}

	{#if error}
		<div class="text-red-500 text-sm p-4">{error}</div>
	{:else if fallbackHtml}
		<div bind:this={outerContainer} class="h-full overflow-auto overscroll-contain">
			<div
				class="max-w-[51rem] min-h-[66rem] my-4 mx-auto py-14 px-16 bg-white text-gray-900 shadow rounded-sm font-[Calibri,Arial,sans-serif] text-base leading-[1.45] [&_.docx-title]:m-0 [&_.docx-title]:mb-4 [&_.docx-title]:text-3xl [&_.docx-title]:leading-[1.2] [&_.docx-subtitle]:mt-[-0.5rem] [&_.docx-subtitle]:mb-5 [&_.docx-subtitle]:text-xl [&_.docx-subtitle]:text-gray-500 [&_.docx-caption]:text-center [&_.docx-caption]:text-sm [&_.docx-caption]:text-gray-500 [&_p]:mt-0 [&_p]:mb-[0.65rem] [&_img]:block [&_img]:max-w-full [&_img]:h-auto [&_img]:my-3 [&_img]:mx-auto [&_table]:w-full [&_table]:my-3 [&_table]:border-collapse [&_table]:font-[Calibri,Arial,sans-serif] [&_table]:text-[0.95rem] [&_td]:border [&_td]:border-gray-300/70 [&_td]:px-2 [&_td]:py-1.5 [&_td]:align-top [&_th]:border [&_th]:border-gray-300/70 [&_th]:px-2 [&_th]:py-1.5 [&_th]:align-top [&_blockquote]:my-4 [&_blockquote]:border-l-[3px] [&_blockquote]:border-gray-300 [&_blockquote]:pl-4 [&_blockquote]:text-gray-700"
			>
				<!-- eslint-disable-next-line svelte/no-at-html-tags -->
				{@html fallbackHtml}
			</div>
		</div>
	{:else}
		<div
			bind:this={outerContainer}
			class="h-full overflow-auto overscroll-contain"
			on:wheel|nonpassive={handleWheel}
		>
			<div bind:this={containerEl}></div>
		</div>
	{/if}

	{#if !loading && !error && data && !fallbackHtml}
		<div
			class="absolute bottom-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-0.5 rounded-lg bg-white/90 dark:bg-gray-850/90 backdrop-blur-sm shadow-lg border border-gray-200/60 dark:border-gray-700/60 px-1 py-0.5"
		>
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
