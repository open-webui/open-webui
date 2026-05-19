<script lang="ts">
	import { getContext, tick } from 'svelte';
	import { formatFileSize } from '$lib/utils';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { config } from '$lib/stores';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	import Modal from './Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import Spinner from './Spinner.svelte';
	import { getFileById, getFileContentById, updateFileProcessingMode } from '$lib/apis/files';

	const EXTRACTABLE_EXTS = new Set([
		'docx', 'doc', 'odt', 'rtf',
		'pptx', 'ppt',
		'xlsx', 'xls',
		'html', 'htm',
		'epub'
	]);

	const getExt = (filename: string) => {
		const dot = (filename || '').toLowerCase().lastIndexOf('.');
		return dot >= 0 ? (filename || '').slice(dot + 1).toLowerCase() : '';
	};

	const TEXT_FILE_EXTS = new Set([
		'txt', 'md', 'markdown', 'rst', 'csv', 'tsv', 'json', 'jsonl', 'ndjson',
		'yaml', 'yml', 'toml', 'ini', 'cfg', 'conf', 'env', 'log', 'xml', 'svg',
		'py', 'pyi', 'ipynb', 'js', 'mjs', 'cjs', 'ts', 'tsx', 'jsx', 'vue',
		'svelte', 'java', 'kt', 'kts', 'scala', 'groovy', 'c', 'cc', 'cpp',
		'cxx', 'h', 'hpp', 'hxx', 'rs', 'go', 'rb', 'php', 'pl', 'pm', 'lua',
		'r', 'jl', 'dart', 'swift', 'm', 'mm', 'cs', 'fs', 'fsx', 'ex', 'exs',
		'erl', 'hs', 'ml', 'mli', 'clj', 'cljs', 'sh', 'bash', 'zsh', 'fish',
		'ps1', 'bat', 'cmd', 'sql', 'graphql', 'gql', 'proto', 'css', 'scss',
		'sass', 'less', 'tex', 'bib', 'srt', 'vtt', 'patch', 'diff',
		'gitignore', 'dockerignore', 'editorconfig'
	]);

	const isTextLikeFile = (name: string, contentType: string) => {
		const n = (name || '').toLowerCase();
		if (n.endsWith('.pdf')) return false;
		const dot = n.lastIndexOf('.');
		const ext = dot >= 0 ? n.slice(dot + 1) : n;
		if (ext && TEXT_FILE_EXTS.has(ext)) return true;
		const ct = (contentType || '').toLowerCase();
		return ct.startsWith('text/') && !ct.includes('html');
	};

	export let item;
	export let show = false;
	export let edit = false;

	let isPDF = false;
	let isAudio = false;
	let loading = false;

	$: isPDF =
		item?.meta?.content_type === 'application/pdf' ||
		(item?.name && item?.name.toLowerCase().endsWith('.pdf'));

	$: isAudio =
		(item?.meta?.content_type ?? '').startsWith('audio/') ||
		(item?.name && item?.name.toLowerCase().endsWith('.mp3')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.wav')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.ogg')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.m4a')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.webm'));

	$: itemExt = getExt(item?.name || item?.file?.filename || '');
	$: showModeToggle = item?.type === 'file' && !item?.locked && EXTRACTABLE_EXTS.has(itemExt);
	$: currentMode = (item?.processing_mode as 'text' | 'pdf') || 'text';
	$: pdfConversionAvailable = $config?.features?.pdf_conversion_available ?? true;
	$: extractedContent = (item?.file?.data?.content ?? '').trim();
	$: extractionStatus = item?.file?.data?.status as
		| 'pending'
		| 'processing'
		| 'completed'
		| 'failed'
		| undefined;
	$: extractionError = item?.file?.data?.error as string | undefined;
	$: escapedName = (item?.name || item?.file?.filename || 'file')
		.replace(/&/g, '&amp;')
		.replace(/"/g, '&quot;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;');
	$: previewEnvelope = extractedContent
		? `<document filename="${escapedName}">\n${extractedContent}\n</document>`
		: '';

	let previewExpanded = true;

	const handleModeChange = async (mode: 'text' | 'pdf') => {
		if (mode === currentMode) return;
		if (mode === 'pdf' && !pdfConversionAvailable) {
			toast.error(
				$i18n.t(
					'PDF conversion is unavailable on this server. Install LibreOffice to enable it.'
				)
			);
			return;
		}
		if (item) item.processing_mode = mode;
		if (item?.id) {
			try {
				await updateFileProcessingMode(localStorage.token, item.id, mode);
			} catch (e) {
				console.error('Failed to update processing mode:', e);
			}
		}
	};

	const loadContent = async () => {
		if (item?.type === 'file') {
			loading = true;

			const file = await getFileById(localStorage.token, item.id).catch((e) => {
				console.error('Error fetching file:', e);
				return null;
			});

			if (file) {
				item.file = file || {};
			}

			const existing = (item?.file?.data?.content ?? '').trim();
			const name = item?.name || item?.file?.filename || '';
			const ct = item?.meta?.content_type || item?.file?.meta?.content_type || '';
			if (!existing && !isPDF && !isAudio && isTextLikeFile(name, ct)) {
				try {
					const blob = await getFileContentById(item.id);
					const text = blob ? await blob.text() : '';
					if (!item.file) item.file = {};
					if (!item.file.data) item.file.data = {};
					item.file.data.content = text;
				} catch (e) {
					console.error('Error fetching file text content:', e);
				}
			}

			loading = false;
		}

		await tick();
	};

	$: if (show) {
		loadContent();
	}
</script>

<Modal bind:show size="lg">
	<div class="font-primary px-4.5 py-3.5 w-full flex flex-col justify-center dark:text-gray-400">
		<div class=" pb-2">
			<div class="flex items-start justify-between">
				<div>
					<div class=" font-medium text-lg dark:text-gray-100">
						<a
							href="#"
							class="hover:underline line-clamp-1"
							on:click|preventDefault={() => {
								if (!isPDF && item.url) {
									window.open(
										item.type === 'file' ? `${item.url}/content` : `${item.url}`,
										'_blank'
									);
								}
							}}
						>
							{item?.name ?? 'File'}
						</a>
					</div>
				</div>

				<div>
					<button
						on:click={() => {
							show = false;
						}}
					>
						<XMark />
					</button>
				</div>
			</div>

			<div>
				<div class="flex flex-col items-center md:flex-row gap-1 justify-between w-full">
					<div class=" flex flex-wrap text-xs gap-1 text-gray-500">
						{#if item.size}
							<div class="capitalize shrink-0">{formatFileSize(item.size)}</div>
						{/if}
					</div>
				</div>
			</div>
		</div>

		{#if showModeToggle}
			<div class="pb-3">
				<div class="text-xs text-gray-500 dark:text-gray-400 mb-2">
					{$i18n.t('How should the model read this file?')}
				</div>
				<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">
					<button
						type="button"
						class="text-left p-3 rounded-xl border transition
							{currentMode === 'text'
							? 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-850'
							: 'border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700'}"
						on:click={() => handleModeChange('text')}
					>
						<div class="flex items-center gap-2 mb-1">
							<span class="size-4 shrink-0 rounded-full border border-gray-300 dark:border-gray-600 flex items-center justify-center">
								{#if currentMode === 'text'}
									<span class="size-2 rounded-full bg-current"></span>
								{/if}
							</span>
							<span class="font-medium text-sm dark:text-gray-100">
								{$i18n.t('Extract text')}
							</span>
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 pl-6">
							{$i18n.t('Faster — but loses images, tables, and formatting.')}
						</div>
					</button>

					<button
						type="button"
						class="text-left p-3 rounded-xl border transition
							{currentMode === 'pdf'
							? 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-850'
							: 'border-gray-100 dark:border-gray-800 hover:border-gray-200 dark:hover:border-gray-700'}
							{pdfConversionAvailable ? '' : 'opacity-50 cursor-not-allowed'}"
						on:click={() => handleModeChange('pdf')}
						disabled={!pdfConversionAvailable}
					>
						<div class="flex items-center gap-2 mb-1">
							<span class="size-4 shrink-0 rounded-full border border-gray-300 dark:border-gray-600 flex items-center justify-center">
								{#if currentMode === 'pdf'}
									<span class="size-2 rounded-full bg-current"></span>
								{/if}
							</span>
							<span class="font-medium text-sm dark:text-gray-100">
								{$i18n.t('Convert to PDF')}
							</span>
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400 pl-6">
							{$i18n.t('Slower — but preserves images, tables, and layout.')}
						</div>
						{#if !pdfConversionAvailable}
							<div class="text-xs text-amber-600 dark:text-amber-400 pl-6 mt-1">
								{$i18n.t('Unavailable: LibreOffice is not installed on the server.')}
							</div>
						{/if}
					</button>
				</div>
			</div>
		{/if}

		<div class="max-h-[75vh] overflow-auto">
			{#if !loading}
				{#if isPDF}
					<iframe
						title={item?.name}
						src={`${WEBUI_API_BASE_URL}/files/${item.id}/content`}
						class="w-full h-[70vh] border-0 rounded-lg"
					/>
				{:else}
					{#if isAudio}
						<audio
							src={`${WEBUI_API_BASE_URL}/files/${item.id}/content`}
							class="w-full border-0 rounded-lg mb-2"
							controls
							playsinline
						/>
					{/if}

					{#if showModeToggle}
						<!-- Show what the model will actually see in Text mode: the
							 exact <document filename="..."> envelope. Useful for
							 debugging "why did the model miss this paragraph?" -->
						<details class="mb-2" bind:open={previewExpanded}>
							<summary class="cursor-pointer text-xs text-gray-500 dark:text-gray-400 py-1 select-none">
								{currentMode === 'pdf'
									? $i18n.t('View extracted text (Text mode preview)')
									: $i18n.t('View extracted text')}
							</summary>
							<div class="mt-2">
								{#if extractionStatus === 'processing' || extractionStatus === 'pending'}
									<div class="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 py-2">
										<Spinner className="size-3.5" />
										{$i18n.t('Extracting…')}
									</div>
								{:else if extractionStatus === 'failed'}
									<div class="text-xs text-red-600 dark:text-red-400 py-2">
										{$i18n.t('Extraction failed')}: {extractionError ?? $i18n.t('unknown error')}
									</div>
								{:else if previewEnvelope}
									<pre class="max-h-96 overflow-auto scrollbar-hidden text-xs whitespace-pre-wrap p-2 rounded-lg bg-gray-50 dark:bg-gray-850 font-mono">{previewEnvelope}</pre>
								{:else}
									<div class="text-xs text-gray-500 dark:text-gray-400 py-2">
										{$i18n.t('No content extracted yet.')}
									</div>
								{/if}
							</div>
						</details>
					{:else if item?.file?.data}
						<div class="max-h-96 overflow-scroll scrollbar-hidden text-xs whitespace-pre-wrap">
							{(item?.file?.data?.content ?? '').trim() || 'No content'}
						</div>
					{/if}
				{/if}
			{:else}
				<div class="flex items-center justify-center py-6">
					<Spinner className="size-5" />
				</div>
			{/if}
		</div>
	</div>
</Modal>
