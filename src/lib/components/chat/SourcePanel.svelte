<script lang="ts">
	import { getContext } from 'svelte';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import PDFViewer from '$lib/components/common/PDFViewer.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n: Writable<i18nType> = getContext('i18n');

	export let target: {
		messageId?: string;
		sourceTargetKey?: string;
		scrollRequestId?: number;
		citationGroupIndex?: number;
		selectedReferenceIndex?: number;
		title?: string;
		file_id?: string;
		url?: string;
		page?: number;
		page_label?: string | number;
		total_pages?: number;
		metadata?: Record<string, any>;
		openInNewTabUrl?: string;
	} | null = null;

	export let onClose: () => void = () => {};

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch {
			return str;
		}
	};

	const withPageFragment = (sourceUrl: string | null | undefined, page: number | null) => {
		if (!sourceUrl || !page) return sourceUrl ?? null;

		const [baseUrl] = sourceUrl.split('#');
		return `${baseUrl}#page=${page}`;
	};

	$: title = target?.title ?? $i18n.t('Source');
	$: fileId = target?.file_id;
	$: url = target?.url;
	$: page = target?.page;
	$: hasPage = Number.isInteger(page);
	$: initialPage = hasPage ? (page as number) + 1 : null;
	$: pdfUrl = fileId ? `${WEBUI_API_BASE_URL}/files/${fileId}/content` : null;
	$: iframeUrl = !fileId ? withPageFragment(url, initialPage) : null;
	$: openInNewTabUrl = target?.openInNewTabUrl;
	$: scrollRequestId = target?.scrollRequestId ?? 0;
</script>

<div
	class="flex h-full min-h-full w-full min-w-0 flex-col bg-white text-gray-800 dark:bg-gray-850 dark:text-gray-100"
>
	<div class="flex shrink-0 items-center justify-between gap-3 px-3 py-2">
		<div class="min-w-0">
			<div class="truncate text-sm font-medium">
				{#if openInNewTabUrl}
					<Tooltip
						className="w-fit"
						content={url?.includes('http') ? $i18n.t('Open link') : $i18n.t('Open file')}
						placement="top-start"
						tippyOptions={{ duration: [500, 0] }}
					>
						<a
							class="underline hover:text-gray-500 dark:hover:text-gray-100"
							href={openInNewTabUrl}
							target="_blank"
							rel="noopener noreferrer"
						>
							{decodeString(title)}
						</a>
					</Tooltip>
				{:else}
					{decodeString(title)}
				{/if}
			</div>
		</div>

		<div class="flex shrink-0 items-center gap-1">
			<button
				class="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition text-gray-500 dark:text-gray-400"
				aria-label={$i18n.t('Close')}
				on:click={onClose}
			>
				<XMark className="size-4" />
			</button>
		</div>
	</div>

	<div class="min-h-0 flex-1">
		{#if pdfUrl}
			{#key pdfUrl}
				<PDFViewer url={pdfUrl} {initialPage} {scrollRequestId} className="h-full w-full" />
			{/key}
		{:else if iframeUrl}
			{#key `${iframeUrl}:${scrollRequestId}`}
				<iframe class="h-full w-full border-0" title={decodeString(title)} src={iframeUrl}></iframe>
			{/key}
		{:else}
			<div class="flex h-full items-center justify-center text-sm text-gray-500 dark:text-gray-400">
				{$i18n.t('No source available')}
			</div>
		{/if}
	</div>
</div>
