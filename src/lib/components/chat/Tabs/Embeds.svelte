<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	import { embed } from '$lib/stores';
	import { getFileContentById } from '$lib/apis/files';
	import { quoteLines, quoteMarks } from '$lib/utils/comments/highlights';

	import FullHeightIframe from '$lib/components/common/FullHeightIframe.svelte';
	import PdfPagesPreview from '$lib/components/common/PdfPagesPreview.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import FilePreview from '$lib/components/chat/FileNav/FilePreview.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';

	// A cited upload, shown at its cited page. PDFs also mark the cited text.
	let fileId = '';
	let fileLoading = false;
	let fileData: ArrayBuffer | null = null;
	let fileDocxData: ArrayBuffer | null = null;
	let fileOfficeSlides: string[] | null = null;
	let excelWorkbook: import('xlsx').WorkBook | null = null;
	let selectedExcelSheet = '';
	$: fileName = String($embed?.title ?? '');
	$: fileExt = fileName.split('.').pop()?.toLowerCase() ?? '';

	const loadFile = async (id: string, ext: string) => {
		fileId = id;
		fileData = fileDocxData = fileOfficeSlides = excelWorkbook = null;
		selectedExcelSheet = '';
		fileLoading = !!id;
		if (!id) return;
		try {
			const data = await getFileContentById(id);
			if (fileId !== id || !data) return;
			if (ext === 'pdf') fileData = data;
			else if (ext === 'docx') fileDocxData = data;
			else if (ext === 'pptx') {
				const { pptxToImages } = await import('$lib/utils/pptxToHtml');
				const slides = (await pptxToImages(data)).images;
				if (fileId === id) fileOfficeSlides = slides;
			} else {
				const { readExcelWorkbook } = await import('$lib/utils/excelToTable');
				const workbook = await readExcelWorkbook(data);
				if (fileId === id && workbook.SheetNames.length > 0) {
					selectedExcelSheet = workbook.SheetNames[0];
					excelWorkbook = workbook;
				}
			}
		} catch (e) {
			console.error(e);
		} finally {
			if (fileId === id) fileLoading = false;
		}
	};
	$: if (($embed?.file?.id ?? '') !== fileId) loadFile($embed?.file?.id ?? '', fileExt);
	let filePage: number | null = null;
	let fileQuotes: string[] = [];
	// Hovering a mark shows the retrieved passage it came from.
	let fileQuoteTexts: { text: string; page: number | null }[] = [];
	let hoveredText: {
		text: string;
		page: number | null;
		left: number;
		top: number;
		above: boolean;
	} | null = null;
	const CARD_WIDTH = 352;
	// The card stays while the pointer travels from the mark onto it, so it can be scrolled and selected.
	let closeTimer: ReturnType<typeof setTimeout> | null = null;
	const keepQuoteText = () => {
		if (closeTimer) clearTimeout(closeTimer);
		closeTimer = null;
	};
	const closeQuoteText = (delay = 300) => {
		keepQuoteText();
		closeTimer = setTimeout(() => (hoveredText = null), delay);
	};
	const showQuoteText = (index: number | null, rect: DOMRect | null) => {
		const passage = index === null ? null : fileQuoteTexts[index];
		if (!passage || !rect) return closeQuoteText();
		keepQuoteText();
		// Below the mark, or above it when there is more room there
		const above = rect.bottom > window.innerHeight / 2;
		hoveredText = {
			...passage,
			left: Math.max(12, Math.min(rect.left, window.innerWidth - CARD_WIDTH - 12)),
			top: above ? rect.top - 6 : rect.bottom + 6,
			above
		};
	};
	onDestroy(keepQuoteText);
	let fileSource: any = null;
	$: if ($embed?.file !== fileSource) {
		fileSource = $embed?.file ?? null;
		filePage = fileSource?.page ?? null;
		// The cited passages are marked on the pages they appear on
		const quotes = (fileSource?.passages ?? []).flatMap((passage) =>
			quoteLines(passage.text ?? '').map((quote) => ({ quote, passage }))
		);
		fileQuotes = quotes.map(({ quote }) => quote);
		fileQuoteTexts = quotes.map(({ passage }) => passage);
		hoveredText = null;
	}

	const i18n = getContext<any>('i18n');

	export let overlay = false;
	// Preserve the former embed close label for i18n extraction.
	// t('Close embed')

	const getSrcUrl = (url: string, chatId?: string, messageId?: string, sourceId: string) => {
		try {
			const parsed = new URL(url);

			if (chatId) {
				parsed.searchParams.set('chat_id', chatId);
			}

			if (messageId) {
				parsed.searchParams.set('message_id', messageId);
			}

			if (sourceId) {
				parsed.searchParams.set('source_id', sourceId);
			}

			return parsed.toString();
		} catch {
			// Fallback for relative URLs or invalid input
			const hasQuery = url.includes('?');
			const parts = [];

			if (chatId) parts.push(`chat_id=${encodeURIComponent(chatId)}`);
			if (messageId) parts.push(`message_id=${encodeURIComponent(messageId)}`);
			if (sourceId) parts.push(`source_id=${encodeURIComponent(sourceId)}`);

			if (parts.length === 0) return url;

			return url + (hasQuery ? '&' : '?') + parts.join('&');
		}
	};
</script>

{#if $embed}
	<div class="h-full w-full flex flex-col">
		<!-- A cited file is named by its tab, like other file tabs -->
		{#if !$embed?.file}
			<div
				class="pointer-events-auto z-20 flex justify-between items-center pb-3 px-2 font-primar text-base-900 dark:text-base-0 flex-shrink-0"
			>
				<div class="flex-1 flex items-center justify-between pl-2">
					<a
						class="flex items-center space-x-2 hover:underline"
						href={$embed?.url}
						target="_blank"
						rel="noopener noreferrer"
					>
						{$embed?.title ?? 'Embedded Content'}
					</a>
				</div>
			</div>
		{/if}

		<div class="w-full flex-1 min-h-0 relative">
			{#if overlay}
				<div class=" absolute top-0 left-0 right-0 bottom-0 z-10"></div>
			{/if}

			{#if $embed?.file}
				{#if fileData}
					{#key `${fileId}:${filePage}`}
						<PdfPagesPreview
							data={fileData}
							targetPage={filePage}
							highlightQuotes={fileQuotes}
							onQuoteHover={showQuoteText}
							className="w-full h-full"
						/>
					{/key}
				{:else if fileDocxData || fileOfficeSlides || excelWorkbook}
					<!-- Previews drawn as real text get the cited passages marked too -->
					<div
						class="flex h-full min-h-0 flex-col"
						use:quoteMarks={{ quotes: fileQuotes, onHover: showQuoteText }}
					>
						<FilePreview
							selectedFile={fileName}
							fileLoading={false}
							{fileDocxData}
							{fileOfficeSlides}
							{excelWorkbook}
							bind:selectedExcelSheet
							currentSlide={Math.max(0, (filePage ?? 1) - 1)}
							targetPage={filePage}
							target={null}
							readOnly={true}
						/>
					</div>
				{:else}
					<div
						class="flex h-full items-center justify-center text-xs text-base-500 dark:text-base-400"
					>
						{#if fileLoading}
							<Spinner className="size-3.5 text-base-400 dark:text-base-500" />
						{:else}
							{$i18n.t('Preview failed')}
						{/if}
					</div>
				{/if}
				{#if hoveredText}
					<!-- Styled as the file and chat hover previews are -->
					<div
						role="tooltip"
						class="fixed z-[9999] flex max-h-[min(17.5rem,calc(100vh-1.5rem))] w-[22rem] max-w-[calc(100vw-1.5rem)] flex-col overflow-hidden rounded-2xl bg-base-0 font-normal text-base-900 shadow-[0_16px_40px_-28px_rgba(0,0,0,0.55)] ring-1 ring-base-1000/5 dark:bg-base-850 dark:text-base-100 dark:ring-base-0/10"
						style:left={`${hoveredText.left}px`}
						style:top={`${hoveredText.top}px`}
						style:transform={hoveredText.above ? 'translateY(-100%)' : ''}
						on:mouseenter={keepQuoteText}
						on:mouseleave={() => closeQuoteText(150)}
					>
						<!-- Labelled as the comment popover on a file is: one quiet line above the text -->
						{#if hoveredText.page}
							<div
								class="shrink-0 px-3 pt-2 text-[0.6875rem] leading-4 text-base-500 dark:text-base-400"
							>
								{$i18n.t('Page')}
								{hoveredText.page}
							</div>
						{/if}
						<!-- Everything at the small preview size, headings and tables included -->
						<div
							class="markdown-prose-xs min-h-0 min-w-full max-w-full flex-1 overflow-auto scrollbar-thin px-3 pb-2 {hoveredText.page
								? 'pt-1'
								: 'pt-2'} !leading-snug text-base-800 dark:text-base-200 [&_*]:!text-xs [&_*]:!leading-snug [&_:is(h1,h2,h3,h4,h5,h6)]:!my-1 [&_:is(h1,h2,h3,h4,h5,h6)]:!font-medium [&_:is(td,th)]:!px-1.5 [&_:is(td,th)]:!py-0.5 [&_:is(td,th)]:!text-[0.6875rem] [&_strong]:!font-medium"
						>
							<Markdown
								content={hoveredText.text.trim().replace(/\n\n+/g, '\n\n')}
								id="cited-passage"
							/>
						</div>
					</div>
				{/if}
			{:else}
				<FullHeightIframe
					src={getSrcUrl($embed?.url ?? '', $embed?.chatId, $embed?.messageId, $embed?.sourceId)}
					payload={$embed?.source ?? null}
					iframeClassName="w-full h-full"
				/>
			{/if}
		</div>
	</div>
{/if}
