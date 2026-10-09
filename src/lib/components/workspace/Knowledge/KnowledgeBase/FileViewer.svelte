<script lang="ts">
	import { getContext, onDestroy, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import DOMPurify from 'dompurify';
	import {
		FileContentError,
		getFileBlobById,
		getFileIndexedText,
		updateFileDataContentById
	} from '$lib/apis/files';
	import FilePreview from '$lib/components/chat/FileNav/FilePreview.svelte';
	import FileCodeEditor from '$lib/components/chat/FileNav/FileCodeEditor.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import DropdownMenu from '$lib/components/common/DropdownMenu.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import { fileName, type KnowledgeFile, type ViewerState, newViewerState } from './types';

	export let file: KnowledgeFile;
	export let writeAccess = false;
	export let mobile = false;
	export let state: ViewerState = newViewerState();
	export let onClose = () => {};
	export let onSaved = async () => {};
	export let saving = false;
	const i18n = getContext<any>('i18n');
	let previewData: Record<string, any> = {};
	let loading = false;
	let indexedLoading = false;
	let previewError = '';
	let indexedError = '';
	let sourceToggle = false;
	let showRaw = false;
	let previewName = fileName(file);
	let request = 0;
	let originalLoaded = false;
	let controller: AbortController;
	let indexedController: AbortController;
	let objectUrl = '';
	let workbook: any = null;
	let selectedExcelSheet = '';
	let excelSheetNames: string[] = [];
	let indexedEditor: FileCodeEditor;
	let mounted = false;
	$: name = fileName(file);
	$: noOriginal = file.has_original === false || !!state.originalUnavailable;
	$: if (
		mounted &&
		state.mode === 'indexed' &&
		state.indexed === null &&
		!indexedLoading &&
		!indexedError
	)
		loadIndexed();
	$: if (
		mounted &&
		state.mode === 'preview' &&
		!noOriginal &&
		!originalLoaded &&
		!loading &&
		!previewError
	)
		loadOriginal();
	$: if (noOriginal) state.mode = 'indexed';

	const message = (error: unknown) => (error instanceof Error ? error.message : String(error));
	const loadIndexed = async () => {
		indexedController?.abort();
		indexedController = new AbortController();
		const signal = indexedController.signal;
		indexedLoading = true;
		indexedError = '';
		try {
			const content = await getFileIndexedText(localStorage.token, file.id!, signal);
			if (!signal.aborted)
				state = {
					...state,
					indexed: content,
					draft: state.editing && state.indexed !== null ? state.draft : content
				};
		} catch (error) {
			if (!signal.aborted) indexedError = message(error);
		} finally {
			if (!signal.aborted) indexedLoading = false;
		}
	};
	const selectSheet = async (sheet: string) => {
		const key = request;
		const { excelToTable } = await import('$lib/utils/excelToTable');
		const result = await excelToTable(workbook.Sheets[sheet]);
		if (key !== request) return;
		selectedExcelSheet = sheet;
		previewData = { fileOfficeHtml: DOMPurify.sanitize(result.html) };
	};
	const loadOriginal = async () => {
		controller?.abort();
		controller = new AbortController();
		const signal = controller.signal;
		const key = ++request;
		loading = true;
		previewError = '';
		previewData = {};
		sourceToggle = false;
		if (objectUrl) URL.revokeObjectURL(objectUrl);
		objectUrl = '';
		try {
			const blob = await getFileBlobById(localStorage.token, file.id!, { signal });
			if (signal.aborted || key !== request) return;
			const mime = (file.meta?.content_type || blob.type).split(';')[0].toLowerCase();
			const ext = name.split('.').pop()?.toLowerCase() || '';
			let data: Record<string, any>;
			previewName = name;
			if (mime === 'application/pdf' || ext === 'pdf')
				data = { filePdfData: await blob.arrayBuffer() };
			else if (ext === 'svg' || mime === 'image/svg+xml') {
				previewName = `${name}.svg`;
				data = { fileContent: await blob.text() };
				sourceToggle = true;
			} else if (mime.startsWith('image/') || /^(png|jpe?g|gif|webp|avif|bmp|ico)$/.test(ext)) {
				objectUrl = URL.createObjectURL(blob);
				data = { fileImageUrl: objectUrl };
			} else if (mime.startsWith('audio/') || /^(mp3|wav|ogg|m4a|flac)$/.test(ext)) {
				objectUrl = URL.createObjectURL(blob);
				data = { fileAudioUrl: objectUrl };
			} else if (mime.startsWith('video/') || /^(mp4|webm|mov)$/.test(ext)) {
				objectUrl = URL.createObjectURL(blob);
				data = { fileVideoUrl: objectUrl };
			} else if (ext === 'docx' || mime.includes('wordprocessingml'))
				data = { fileDocxData: await blob.arrayBuffer() };
			else if (ext === 'xlsx' || mime.includes('spreadsheetml')) {
				const XLSX = await import('xlsx');
				const bytes = await blob.arrayBuffer();
				if (signal.aborted || key !== request) return;
				workbook = XLSX.read(bytes, { type: 'array' });
				excelSheetNames = workbook.SheetNames;
				if (!excelSheetNames.length) throw new Error('This workbook has no sheets.');
				await selectSheet(excelSheetNames[0]);
				data = previewData;
			} else if (ext === 'pptx' || mime.includes('presentationml')) {
				const { pptxToImages } = await import('$lib/utils/pptxToHtml');
				const result = await pptxToImages(await blob.arrayBuffer());
				data = { fileOfficeSlides: result.images };
			} else if (
				mime.startsWith('text/') ||
				/^(md|markdown|mdx|txt|csv|tsv|json|jsonc|jsonl|json5|html?|xml|ya?ml|toml|ini|log|py|js|ts|tsx|jsx|css|sh|sql|rs|go|java|c|cpp|h|ipynb)$/.test(
					ext
				) ||
				mime.includes('json')
			) {
				data = { fileContent: await blob.text() };
				if (mime === 'text/csv' && ext !== 'csv') previewName = `${name}.csv`;
				if (mime === 'text/html' && !/^html?$/.test(ext)) previewName = `${name}.html`;
				if (mime.includes('json') && !/^(json|jsonc|jsonl|json5|ipynb)$/.test(ext))
					previewName = `${name}.json`;
				sourceToggle = /\.(md|markdown|mdx|csv|tsv|json|jsonc|jsonl|json5|html?|svg|ipynb)$/i.test(
					previewName
				);
			} else throw new Error('Preview is not available for this file type.');
			if (signal.aborted || key !== request) return;
			previewData = data;
			originalLoaded = true;
		} catch (error) {
			if (!signal.aborted && key === request) {
				if (error instanceof FileContentError && error.status === 404)
					state = { ...state, originalUnavailable: true, mode: 'indexed' };
				else previewError = message(error);
			}
		} finally {
			if (!signal.aborted && key === request) loading = false;
		}
	};
	const download = async () => {
		try {
			const blob = await getFileBlobById(
				localStorage.token,
				file.id!,
				noOriginal ? { filename: name } : { attachment: true }
			);
			const url = URL.createObjectURL(blob);
			const link = document.createElement('a');
			link.href = url;
			link.download = noOriginal && !name.endsWith('.txt') ? `${name}.txt` : name;
			link.click();
			setTimeout(() => URL.revokeObjectURL(url), 1000);
		} catch (error) {
			toast.error(message(error));
		}
	};
	const save = async () => {
		if (!writeAccess || saving || !state.editing || state.indexed === null) return;
		state.draft = indexedEditor?.getValue() ?? state.draft;
		saving = true;
		try {
			const result = await updateFileDataContentById(localStorage.token, file.id!, state.draft);
			state = { ...state, indexed: result.content, draft: result.content, editing: false };
			toast.success($i18n.t('Indexed text saved.'));
			await onSaved();
		} catch (error) {
			toast.error(message(error));
		} finally {
			saving = false;
		}
	};
	onMount(() => {
		mounted = true;
	});
	onDestroy(() => {
		++request;
		controller?.abort();
		indexedController?.abort();
		if (objectUrl) URL.revokeObjectURL(objectUrl);
	});
</script>

<div class="flex h-full min-h-0 min-w-0 flex-1 flex-col bg-white dark:bg-gray-900">
	<div class="flex h-8 shrink-0 items-center gap-1 px-2.5 text-xs dark:bg-black">
		{#if mobile}<button
				type="button"
				aria-label={$i18n.t('Back to files')}
				class="flex shrink-0 items-center gap-1 whitespace-nowrap pr-1 text-gray-500"
				on:click={onClose}><ChevronLeft className="size-3.5" />{$i18n.t('Back')}</button
			>{/if}
		<span class="min-w-0 flex-1 truncate text-gray-500" title={name}>{name}</span>
		{#if !noOriginal}<button
				type="button"
				class="shrink-0 px-1 py-0.5 {state.mode === 'preview' ? '' : 'text-gray-400'}"
				aria-pressed={state.mode === 'preview'}
				on:click={() => (state.mode = 'preview')}>{$i18n.t('Preview')}</button
			>{/if}
		<button
			type="button"
			class="shrink-0 px-1 py-0.5 {state.mode === 'indexed' ? '' : 'text-gray-400'}"
			aria-pressed={state.mode === 'indexed'}
			on:click={() => (state.mode = 'indexed')}>{$i18n.t('Indexed text')}</button
		>
		{#if writeAccess}
			{#if state.editing}
				<button
					type="button"
					class="shrink-0 px-1 py-0.5 text-gray-500"
					disabled={saving}
					on:click={() => (state = { ...state, draft: state.indexed ?? '', editing: false })}
					>{$i18n.t('Cancel')}</button
				>
				<button
					type="button"
					class="flex shrink-0 items-center gap-1 px-1 py-0.5"
					disabled={saving || state.indexed === null}
					on:click={save}
				>
					{$i18n.t('Save')}{#if saving}<Spinner className="size-3" />{/if}
				</button>
			{:else}
				<button
					type="button"
					class="shrink-0 px-1 py-0.5 text-gray-500"
					on:click={() => {
						state = { ...state, mode: 'indexed', editing: true, draft: state.indexed ?? '' };
						toast.info(
							$i18n.t(
								'Edits change retrieval text in all linked collections; the original file stays unchanged.'
							),
							{ position: 'bottom-center', duration: 5000 }
						);
					}}>{$i18n.t('Edit')}</button
				>
			{/if}
		{/if}
		<Dropdown closeOnSelect align="end"
			><button type="button" aria-label={$i18n.t('File actions')} class="shrink-0 p-1 text-gray-500"
				><EllipsisHorizontal className="size-3.5" /></button
			>
			<div slot="content">
				<DropdownMenu
					><button type="button" on:click={download}>{$i18n.t('Download')}</button
					>{#if state.mode === 'preview' && !noOriginal}<button
							type="button"
							on:click={loadOriginal}>{$i18n.t('Reload preview')}</button
						>{/if}
					{#if state.mode === 'preview' && sourceToggle}<button
							type="button"
							on:click={() => (showRaw = !showRaw)}
							>{$i18n.t(showRaw ? 'Rendered preview' : 'View source')}</button
						>{/if}</DropdownMenu
				>
			</div></Dropdown
		>
	</div>
	{#if state.mode === 'preview'}
		{#if previewError}<div class="p-4 text-xs text-gray-500">
				<p role="alert">{previewError}</p>
				<button class="mt-2" type="button" on:click={loadOriginal}>{$i18n.t('Retry')}</button>
			</div>
		{:else}<FilePreview
				selectedFile={previewName}
				fileLoading={loading}
				{...previewData}
				readOnly
				allowScripts={false}
				bind:showRaw
				{excelSheetNames}
				{selectedExcelSheet}
				onSheetChange={selectSheet}
			/>{/if}
	{:else if indexedLoading}<div class="p-4"><Spinner className="size-4" /></div>
	{:else if indexedError}<div class="p-4 text-xs">
			<p role="alert">{indexedError}</p>
			<button type="button" on:click={loadIndexed}>{$i18n.t('Retry')}</button>
		</div>
	{:else if state.indexed !== null}
		<div class="min-h-0 flex-1">
			<FileCodeEditor
				bind:this={indexedEditor}
				bind:value={state.draft}
				filePath="indexed.txt"
				readOnly={!writeAccess || !state.editing || saving}
				onSave={save}
			/>
		</div>
	{/if}
</div>
