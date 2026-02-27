<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import panzoom, { type PanZoom } from 'panzoom';
	import { marked } from 'marked';
	import DOMPurify from 'dompurify';
	import Spinner from '../../common/Spinner.svelte';
	import PDFViewer from '../../common/PDFViewer.svelte';
	import Tooltip from '../../common/Tooltip.svelte';
	import Reset from '../../icons/Reset.svelte';

	const i18n = getContext('i18n');

	export let selectedFile: string | null = null;
	export let fileLoading = false;
	export let fileImageUrl: string | null = null;
	export let filePdfData: ArrayBuffer | null = null;
	export let fileContent: string | null = null;

	export let onDownload: () => void = () => {};

	const MD_EXTS = new Set(['md', 'markdown', 'mdx']);
	$: isMarkdown = MD_EXTS.has(selectedFile?.split('.').pop()?.toLowerCase() ?? '');
	$: renderedHtml =
		isMarkdown && fileContent
			? DOMPurify.sanitize(marked.parse(fileContent, { async: false }) as string)
			: '';

	let showRaw = false;
	// Reset to preview mode when switching files
	$: if (selectedFile) showRaw = false;

	let pzInstance: PanZoom | null = null;

	const initImagePanzoom = (node: HTMLElement) => {
		pzInstance = panzoom(node, {
			bounds: true,
			boundsPadding: 0.1,
			zoomSpeed: 0.065
		});
	};

	const resetImageView = () => {
		if (pzInstance) {
			pzInstance.moveTo(0, 0);
			pzInstance.zoomAbs(0, 0, 1);
		}
	};

	export const disposePanzoom = () => {
		if (pzInstance) {
			pzInstance.dispose();
			pzInstance = null;
		}
	};

	onDestroy(() => {
		disposePanzoom();
	});
</script>

<div
	class="flex-1 {fileImageUrl !== null || filePdfData !== null
		? 'overflow-hidden'
		: 'overflow-y-auto'} min-h-0 relative h-full"
>
	<!-- Floating action buttons -->
	<div class="absolute top-2 right-2 z-10 flex gap-1">
		{#if fileImageUrl !== null}
			<Tooltip content={$i18n.t('Reset view')}>
				<button
					class="p-1.5 rounded-lg bg-white/80 dark:bg-gray-850/80 backdrop-blur-sm shadow-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
					on:click={resetImageView}
					aria-label={$i18n.t('Reset view')}
				>
					<Reset className="size-4" />
				</button>
			</Tooltip>
		{/if}
		{#if isMarkdown && fileContent !== null}
			<Tooltip content={showRaw ? $i18n.t('Preview') : $i18n.t('Source')}>
				<button
					class="p-1.5 rounded-lg bg-white/80 dark:bg-gray-850/80 backdrop-blur-sm shadow-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
					on:click={() => (showRaw = !showRaw)}
					aria-label={showRaw ? $i18n.t('Preview') : $i18n.t('Source')}
				>
					{#if showRaw}
						<!-- Eye icon: switch to preview -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M2.036 12.322a1.012 1.012 0 0 1 0-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178Z"
							/>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
							/>
						</svg>
					{:else}
						<!-- Code icon: switch to raw -->
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 24 24"
							fill="none"
							stroke="currentColor"
							stroke-width="1.5"
							class="size-4"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								d="M17.25 6.75 22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3-4.5 16.5"
							/>
						</svg>
					{/if}
				</button>
			</Tooltip>
		{/if}
		<button
			class="p-1.5 rounded-lg bg-white/80 dark:bg-gray-850/80 backdrop-blur-sm shadow-sm hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
			on:click={onDownload}
			aria-label={$i18n.t('Download')}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="1.5"
				class="size-4"
			>
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
				/>
			</svg>
		</button>
	</div>

	<!-- File preview -->
	{#if fileLoading}
		<div class="flex items-center justify-center h-full"><Spinner className="size-4" /></div>
	{:else if fileImageUrl !== null}
		<div class="w-full h-full flex items-center justify-center" use:initImagePanzoom>
			<img
				src={fileImageUrl}
				alt={selectedFile?.split('/').pop()}
				class="max-w-full max-h-full object-contain p-3"
				draggable="false"
			/>
		</div>
	{:else if filePdfData !== null}
		<PDFViewer data={filePdfData} className="w-full h-full" />
	{:else if fileContent !== null}
		{#if isMarkdown && !showRaw}
			<div class="prose dark:prose-invert max-w-full text-sm p-3">
				{@html renderedHtml}
			</div>
		{:else}
			<pre
				class="text-xs font-mono text-gray-800 dark:text-gray-200 whitespace-pre-wrap break-all leading-relaxed p-3">{fileContent}</pre>
		{/if}
	{:else}
		<div class="text-sm text-gray-400 text-center pt-8">
			{$i18n.t('Could not read file.')}
		</div>
	{/if}
</div>
