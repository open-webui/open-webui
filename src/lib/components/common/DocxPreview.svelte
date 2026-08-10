<script lang="ts">
	import DOMPurify from 'dompurify';
	import { getContext, onDestroy, onMount, tick } from 'svelte';
	import type { Readable } from 'svelte/store';

	import Spinner from './Spinner.svelte';

	type I18n = {
		t: (key: string, values?: Record<string, unknown>) => string;
	};

	const i18n = getContext<Readable<I18n>>('i18n');

	export let data: ArrayBuffer | null = null;
	export let className = '';

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

<div class="owui-docx-preview {className}" style="--docx-scale: {docxScale};">
	<div bind:this={styleEl}></div>

	{#if loading}
		<div class="absolute inset-0 flex items-center justify-center bg-white/70 dark:bg-gray-950/60">
			<Spinner className="size-4" />
		</div>
	{/if}

	{#if error}
		<div class="text-red-500 text-sm p-4">{error}</div>
	{:else if fallbackHtml}
		<div bind:this={outerContainer} class="owui-docx-scroll">
			<div class="owui-docx-fallback">
				<!-- eslint-disable-next-line svelte/no-at-html-tags -->
				{@html fallbackHtml}
			</div>
		</div>
	{:else}
		<div bind:this={outerContainer} class="owui-docx-scroll" on:wheel|nonpassive={handleWheel}>
			<div bind:this={containerEl}></div>
		</div>
	{/if}

	{#if !loading && !error && data && !fallbackHtml}
		<div
			class="absolute bottom-3 left-1/2 -translate-x-1/2 z-10 flex items-center gap-0.5 rounded-lg bg-white/90 dark:bg-gray-850/90 backdrop-blur-sm shadow-lg border border-gray-200/60 dark:border-gray-700/60 px-1 py-0.5"
		>
			<button
				class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
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
				class="px-1.5 py-1 min-w-[3rem] text-center text-[11px] font-normal text-gray-500 dark:text-gray-400 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition tabular-nums"
				on:click={resetView}
				aria-label="Reset zoom"
			>
				{Math.round(zoomLevel * 100)}%
			</button>
			<button
				class="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
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
	.owui-docx-preview {
		position: relative;
		min-height: 100%;
		background: #f3f4f6;
	}

	:global(.dark) .owui-docx-preview {
		background: #111827;
	}

	.owui-docx-scroll {
		height: 100%;
		overflow: auto;
		overscroll-behavior: contain;
	}

	.owui-docx-preview :global(.docx-wrapper) {
		background: transparent;
		display: flex;
		flex-direction: column;
		align-items: center;
		padding: 16px 0 56px;
	}

	.owui-docx-preview :global(.docx-wrapper > section.docx) {
		margin: 0 auto 4px !important;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.18) !important;
		zoom: var(--docx-scale);
	}

	.owui-docx-fallback {
		max-width: 816px;
		min-height: 1056px;
		margin: 16px auto;
		padding: 56px 64px;
		background: #fff;
		color: #111827;
		box-shadow: 0 1px 4px rgba(0, 0, 0, 0.16);
		border-radius: 2px;
		font-family: Calibri, Arial, sans-serif;
		font-size: 1rem;
		line-height: 1.45;
	}

	.owui-docx-fallback :global(.docx-title) {
		font-size: 2rem;
		line-height: 1.2;
		margin: 0 0 1rem;
	}

	.owui-docx-fallback :global(.docx-subtitle) {
		font-size: 1.25rem;
		color: #6b7280;
		margin: -0.5rem 0 1.25rem;
	}

	.owui-docx-fallback :global(.docx-caption) {
		color: #6b7280;
		font-size: 0.875rem;
		text-align: center;
	}

	.owui-docx-fallback :global(p) {
		margin: 0 0 0.65rem;
	}

	.owui-docx-fallback :global(img) {
		display: block;
		max-width: 100%;
		height: auto;
		margin: 0.75rem auto;
	}

	.owui-docx-fallback :global(table) {
		width: 100%;
		margin: 0.75rem 0;
		border-collapse: collapse;
		font-family: Calibri, Arial, sans-serif;
		font-size: 0.95rem;
	}

	.owui-docx-fallback :global(table td),
	.owui-docx-fallback :global(table th) {
		border: 1px solid rgba(200, 200, 200, 0.6);
		padding: 6px 8px;
		vertical-align: top;
	}

	.owui-docx-fallback :global(blockquote) {
		margin: 1rem 0;
		padding-left: 1rem;
		border-left: 3px solid #d1d5db;
		color: #374151;
	}
</style>
