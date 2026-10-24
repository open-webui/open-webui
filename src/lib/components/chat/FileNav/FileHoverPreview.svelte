<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { LinkPreview } from 'bits-ui';
	import { readFile, downloadFileBlob, type FileEntry } from '$lib/apis/terminal';
	import { formatFileSize } from '$lib/utils';
	import { supportsComments } from '$lib/utils/comments/types';
	import FilePreview from './FilePreview.svelte';
	import CommentFilePreview from './CommentFilePreview.svelte';
	import FileTypeIcon from './FileTypeIcon.svelte';

	const i18n: any = getContext('i18n');
	export let entry: FileEntry;
	export let path: string;
	export let terminalUrl: string;
	export let terminalKey: string;
	export let sessionId: string | undefined = undefined;

	let loading = true;
	let fileContent: string | null = null;
	let fileImageUrl: string | null = null;
	let fileVideoUrl: string | null = null;
	let fileAudioUrl: string | null = null;
	let fileSqliteData: ArrayBuffer | null = null;
	let disposed = false;
	const controller = new AbortController();
	const documentPreview = supportsComments(path);
	// shortcut: Avoid large automatic downloads until bounded preview reads are available.
	const withinPreviewLimit = entry.size !== undefined && entry.size <= 20 * 1024 * 1024;

	onMount(async () => {
		if (documentPreview || !withinPreviewLimit) {
			loading = false;
			return;
		}
		const extension = path.split('.').pop()?.toLowerCase() ?? '';
		const isImage = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'ico', 'avif', 'webp'].includes(extension);
		const isVideo = ['mp4', 'webm', 'mov', 'ogv', 'avi', 'mkv'].includes(extension);
		const isAudio = ['mp3', 'wav', 'ogg', 'oga', 'flac', 'm4a', 'aac', 'wma', 'opus'].includes(
			extension
		);
		const isSqlite = ['db', 'sqlite', 'sqlite3', 'db3'].includes(extension);
		try {
			if (isImage || isVideo || isAudio || isSqlite) {
				const result = await downloadFileBlob(
					terminalUrl,
					terminalKey,
					path,
					sessionId,
					controller.signal
				);
				if (!result || disposed) return;
				if (isSqlite) {
					const bytes = await result.blob.arrayBuffer();
					if (!disposed) fileSqliteData = bytes;
				} else {
					const url = URL.createObjectURL(result.blob);
					if (isImage) fileImageUrl = url;
					else if (isVideo) fileVideoUrl = url;
					else fileAudioUrl = url;
				}
			} else if (entry.size! <= 1024 * 1024) {
				const text = await readFile(terminalUrl, terminalKey, path, sessionId);
				if (!disposed && text !== null && !text.startsWith('[Binary file:')) fileContent = text;
			}
		} catch {
			// A failed preview must not prevent opening the file normally.
		} finally {
			if (!disposed) loading = false;
		}
	});

	onDestroy(() => {
		disposed = true;
		controller.abort();
		for (const url of [fileImageUrl, fileVideoUrl, fileAudioUrl]) {
			if (url) URL.revokeObjectURL(url);
		}
	});
</script>

<LinkPreview.Portal>
	<LinkPreview.Content
		class="z-[9999] hidden w-[20rem] max-w-[calc(100vw-1.5rem)] overflow-hidden rounded-2xl bg-white shadow-[0_16px_40px_-28px_rgba(0,0,0,0.55)] ring-1 ring-black/5 md:block dark:bg-gray-850 dark:text-white dark:ring-white/10"
		side="top"
		align="center"
		sideOffset={12}
		aria-label={$i18n.t('File preview')}
	>
		<div
			class="flex items-center gap-1.5 border-b border-gray-50/60 px-2 py-1.5 dark:border-gray-800/25"
		>
			<FileTypeIcon name={entry.name} size={12} />
			<div class="min-w-0 flex-1 truncate text-xs font-normal leading-4" title={path}>
				{entry.name}
			</div>
			{#if entry.size !== undefined}
				<span class="shrink-0 text-[0.625rem] text-gray-500 dark:text-gray-400"
					>{formatFileSize(entry.size)}</span
				>
			{/if}
		</div>
		<div
			class="h-60 max-h-[calc(100dvh-6rem)] overflow-hidden text-xs [&_.document-markdown]:!p-2 [&_.document-markdown_h1]:!text-sm [&_.document-markdown_h2]:!text-xs [&_.document-markdown_h3]:!text-xs [&_.document-markdown]:!text-xs [&_.cm-editor]:!text-[0.6875rem] [&_pre]:!text-[0.6875rem]"
		>
			{#if documentPreview && withinPreviewLimit}
				<CommentFilePreview
					{path}
					baseUrl={terminalUrl}
					apiKey={terminalKey}
					chatId={sessionId ?? null}
				/>
			{:else if loading || fileContent !== null || fileImageUrl || fileVideoUrl || fileAudioUrl || fileSqliteData}
				<FilePreview
					selectedFile={path}
					fileLoading={loading}
					{fileContent}
					{fileImageUrl}
					{fileVideoUrl}
					{fileAudioUrl}
					{fileSqliteData}
					baseUrl={terminalUrl}
					apiKey={terminalKey}
					chatId={sessionId ?? null}
					readOnly={true}
					allowScripts={false}
				/>
			{:else}
				<div class="px-3 py-4 text-xs text-gray-500 dark:text-gray-400">
					{$i18n.t('Preview not available')}
				</div>
			{/if}
		</div>
	</LinkPreview.Content>
</LinkPreview.Portal>
