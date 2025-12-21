<script lang="ts">
	import * as XLSX from 'xlsx';

	import { getContext, onMount, tick } from 'svelte';

	import { formatFileSize, getLineCount } from '$lib/utils';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getKnowledgeById } from '$lib/apis/knowledge';
	import { getFileById } from '$lib/apis/files';

	import CodeBlock from '$lib/components/chat/Messages/CodeBlock.svelte';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';

	const i18n = getContext('i18n');

	import Modal from './Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import Info from '../icons/Info.svelte';
	import Switch from './Switch.svelte';
	import Tooltip from './Tooltip.svelte';
	import dayjs from 'dayjs';
	import Spinner from './Spinner.svelte';

	export let item;
	export let show = false;
	export let edit = false;

	let enableFullContent = false;
	let loading = false;

	let isPDF = false;
	let isAudio = false;
	let isExcel = false;

	let selectedTab = '';
	let excelWorkbook: XLSX.WorkBook | null = null;
	let excelSheetNames: string[] = [];
	let selectedSheet = '';
	let excelHtml = '';
	let excelError = '';
	let rowCount = 0;

	$: isPDF =
		item?.meta?.content_type === 'application/pdf' ||
		(item?.name && item?.name.toLowerCase().endsWith('.pdf'));

	$: isMarkdown =
		item?.meta?.content_type === 'text/markdown' ||
		(item?.name && item?.name.toLowerCase().endsWith('.md'));

	$: isCode =
		item?.name &&
		(item.name.toLowerCase().endsWith('.py') ||
			item.name.toLowerCase().endsWith('.js') ||
			item.name.toLowerCase().endsWith('.ts') ||
			item.name.toLowerCase().endsWith('.java') ||
			item.name.toLowerCase().endsWith('.html') ||
			item.name.toLowerCase().endsWith('.css') ||
			item.name.toLowerCase().endsWith('.json') ||
			item.name.toLowerCase().endsWith('.cpp') ||
			item.name.toLowerCase().endsWith('.c') ||
			item.name.toLowerCase().endsWith('.h') ||
			item.name.toLowerCase().endsWith('.sh') ||
			item.name.toLowerCase().endsWith('.bash') ||
			item.name.toLowerCase().endsWith('.yaml') ||
			item.name.toLowerCase().endsWith('.yml') ||
			item.name.toLowerCase().endsWith('.xml') ||
			item.name.toLowerCase().endsWith('.sql') ||
			item.name.toLowerCase().endsWith('.go') ||
			item.name.toLowerCase().endsWith('.rs') ||
			item.name.toLowerCase().endsWith('.php') ||
			item.name.toLowerCase().endsWith('.rb'));

	$: isAudio =
		(item?.meta?.content_type ?? '').startsWith('audio/') ||
		(item?.name && item?.name.toLowerCase().endsWith('.mp3')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.wav')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.ogg')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.m4a')) ||
		(item?.name && item?.name.toLowerCase().endsWith('.webm'));

	$: isExcel =
		item?.meta?.content_type === 'application/vnd.ms-excel' ||
		item?.meta?.content_type ===
			'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' ||
		item?.meta?.content_type === 'text/csv' ||
		item?.meta?.content_type === 'application/csv' ||
		(item?.name &&
			(item.name.toLowerCase().endsWith('.xls') ||
				item.name.toLowerCase().endsWith('.xlsx') ||
				item.name.toLowerCase().endsWith('.csv')));

	const loadExcelContent = async () => {
		try {
			excelError = '';
			const response = await fetch(`${WEBUI_API_BASE_URL}/files/${item.id}/content`, {
				headers: {
					Authorization: `Bearer ${localStorage.token}`
				}
			});

			if (!response.ok) {
				throw new Error('Failed to fetch Excel file');
			}

			const arrayBuffer = await response.arrayBuffer();
			excelWorkbook = XLSX.read(arrayBuffer, { type: 'array' });
			excelSheetNames = excelWorkbook.SheetNames;

			if (excelSheetNames.length > 0) {
				selectedSheet = excelSheetNames[0];
				renderExcelSheet();
			}
		} catch (error) {
			console.error('Error loading Excel/CSV file:', error);
			excelError = 'Failed to load Excel/CSV file. Please try downloading it instead.';
		}
	};

	const renderExcelSheet = () => {
		if (!excelWorkbook || !selectedSheet) return;

		const worksheet = excelWorkbook.Sheets[selectedSheet];
		// Calculate row count
		const range = XLSX.utils.decode_range(worksheet['!ref'] || 'A1:A1');
		rowCount = range.e.r - range.s.r + 1;

		excelHtml = XLSX.utils.sheet_to_html(worksheet, {
			id: 'excel-table',
			editable: false,
			header: ''
		});
	};

	$: if (selectedSheet && excelWorkbook) {
		renderExcelSheet();
	}

	const loadContent = async () => {
		selectedTab = '';
		if (item?.type === 'collection') {
			loading = true;

			const knowledge = await getKnowledgeById(localStorage.token, item.id).catch((e) => {
				console.error('Error fetching knowledge base:', e);
				return null;
			});

			if (knowledge) {
				item.files = knowledge.files || [];
			}
			loading = false;
		} else if (item?.type === 'file') {
			loading = true;

			const file = await getFileById(localStorage.token, item.id).catch((e) => {
				console.error('Error fetching file:', e);
				return null;
			});

			if (file) {
				item.file = file || {};
			}

			// Load Excel content if it's an Excel file
			if (isExcel) {
				await loadExcelContent();
			}

			loading = false;
		}

		await tick();
	};

	$: if (show) {
		loadContent();
	}

	onMount(() => {
		console.log(item);
		if (item?.context === 'full') {
			enableFullContent = true;
		}
	});
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
										item.type === 'file'
											? item?.url?.startsWith('http')
												? item.url
												: `${WEBUI_API_BASE_URL}/files/${item.url}/content`
											: item.url,
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
						{#if item?.type === 'collection'}
							{#if item?.type}
								<div class="capitalize shrink-0">{item.type}</div>
								•
							{/if}

							{#if item?.description}
								<div class="line-clamp-1">{item.description}</div>
								•
							{/if}

							{#if item?.created_at}
								<div class="capitalize shrink-0">
									{dayjs(item.created_at * 1000).format('LL')}
								</div>
							{/if}
						{/if}

						{#if item.size}
							<div class="capitalize shrink-0">{formatFileSize(item.size)}</div>
							•
						{/if}

						{#if item?.file?.data?.content}
							<div class="capitalize shrink-0">
								{#if isExcel && rowCount > 0 && selectedTab === 'preview'}
									{$i18n.t('{{COUNT}} Rows', {
										COUNT: rowCount
									})}
								{:else}
									{$i18n.t('{{COUNT}} extracted lines', {
										COUNT: getLineCount(item?.file?.data?.content ?? '')
									})}
								{/if}
							</div>

							<div class="flex items-center gap-1 shrink-0">
								• {$i18n.t('Formatting may be inconsistent from source.')}
							</div>
						{/if}

						{#if item?.knowledge}
							<div class="capitalize shrink-0">
								{$i18n.t('Knowledge Base')}
							</div>
						{/if}
					</div>

					{#if edit}
						<div class=" self-end">
							<Tooltip
								content={enableFullContent
									? $i18n.t(
											'Inject the entire content as context for comprehensive processing, this is recommended for complex queries.'
										)
									: $i18n.t(
											'Default to segmented retrieval for focused and relevant content extraction, this is recommended for most cases.'
										)}
							>
								<div class="flex items-center gap-1.5 text-xs">
									{#if enableFullContent}
										{$i18n.t('Using Entire Document')}
									{:else}
										{$i18n.t('Using Focused Retrieval')}
									{/if}
									<Switch
										bind:state={enableFullContent}
										on:change={(e) => {
											item.context = e.detail ? 'full' : undefined;
										}}
									/>
								</div>
							</Tooltip>
						</div>
					{/if}
				</div>
			</div>
		</div>

		<div class="max-h-[75vh] overflow-auto">
			{#if !loading}
				{#if item?.type === 'collection'}
					<div>
						{#each item?.files as file}
							<div class="flex items-center gap-2 mb-2">
								<div class="flex-shrink-0 text-xs">
									{file?.meta?.name}
								</div>
							</div>
						{/each}
					</div>
				{/if}

				{#if isAudio || isPDF || isExcel || isCode || isMarkdown}
					<div
						class="flex mb-2.5 scrollbar-none overflow-x-auto w-full border-b border-gray-50 dark:border-gray-850/30 text-center text-sm font-medium bg-transparent dark:text-gray-200"
					>
						<button
							class="min-w-fit py-1.5 px-4 border-b {selectedTab === ''
								? ' '
								: ' border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							type="button"
							on:click={() => {
								selectedTab = '';
							}}>{$i18n.t('Content')}</button
						>

						<button
							class="min-w-fit py-1.5 px-4 border-b {selectedTab === 'preview'
								? ' '
								: ' border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
							type="button"
							on:click={() => {
								selectedTab = 'preview';
							}}>{$i18n.t('Preview')}</button
						>
					</div>
				{/if}

				{#if selectedTab === ''}
					{#if item?.file?.data}
						<div class="max-h-96 overflow-scroll scrollbar-hidden text-xs whitespace-pre-wrap">
							{(item?.file?.data?.content ?? '').trim() || 'No content'}
						</div>
					{:else if item?.content}
						<div class="max-h-96 overflow-scroll scrollbar-hidden text-xs whitespace-pre-wrap">
							{(item?.content ?? '').trim() || 'No content'}
						</div>
					{/if}
				{:else if selectedTab === 'preview'}
					{#if isAudio}
						<audio
							src={`${WEBUI_API_BASE_URL}/files/${item.id}/content`}
							class="w-full border-0 rounded-lg mb-2"
							controls
							playsinline
						/>
					{:else if isPDF}
						<iframe
							title={item?.name}
							src={`${WEBUI_API_BASE_URL}/files/${item.id}/content`}
							class="w-full h-[70vh] border-0 rounded-lg"
						/>
					{:else if isExcel}
						{#if excelError}
							<div class="text-red-500 text-sm p-4">
								{excelError}
							</div>
						{:else}
							{#if excelSheetNames.length > 1}
								<div
									class="flex mb-2.5 scrollbar-none overflow-x-auto w-full border-b border-gray-50 dark:border-gray-850/30 text-center text-sm font-medium bg-transparent dark:text-gray-200"
								>
									{#each excelSheetNames as sheetName}
										<button
											class="min-w-fit py-1.5 px-4 border-b {selectedSheet === sheetName
												? ' '
												: ' border-transparent text-gray-300 dark:text-gray-600 hover:text-gray-700 dark:hover:text-white'} transition"
											type="button"
											on:click={() => {
												selectedSheet = sheetName;
											}}>{sheetName}</button
										>
									{/each}
								</div>
							{/if}

							{#if excelHtml}
								<div class="excel-table-container overflow-auto max-h-[60vh]">
									{@html excelHtml}
								</div>
							{:else}
								<div class="text-gray-500 text-sm p-4">No content available</div>
							{/if}
						{/if}
					{:else if isCode}
						<div class="max-h-[60vh] overflow-scroll scrollbar-hidden text-sm relative">
							<CodeBlock
								code={item.file.data.content}
								lang={item.name.split('.').pop()}
								token={null}
								edit={false}
								run={false}
								save={false}
							/>
						</div>
					{:else if isMarkdown}
						<div
							class="max-h-[60vh] overflow-scroll scrollbar-hidden text-sm prose dark:prose-invert max-w-full"
						>
							<Markdown content={item.file.data.content} id="markdown-viewer" />
						</div>
					{:else}
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

<style>
	:global(.excel-table-container table) {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.875rem;
		line-height: 1.25rem;
	}

	:global(.excel-table-container table td),
	:global(.excel-table-container table th) {
		border-width: 1px;
		border-style: solid;
		border-color: var(--color-gray-300, #cdcdcd);
		padding: 0.5rem 0.75rem;
		text-align: left;
	}

	:global(.dark .excel-table-container table td),
	:global(.dark .excel-table-container table th) {
		border-color: var(--color-gray-600, #676767);
	}

	:global(.excel-table-container table th) {
		background-color: var(--color-gray-100, #ececec);
		font-weight: 600;
	}

	:global(.dark .excel-table-container table th) {
		background-color: var(--color-gray-800, #333);
		color: var(--color-gray-100, #ececec);
	}

	:global(.excel-table-container table tr:nth-child(even)) {
		background-color: var(--color-gray-50, #f9f9f9);
	}

	:global(.dark .excel-table-container table tr:nth-child(even)) {
		background-color: rgba(38, 38, 38, 0.5);
	}

	:global(.excel-table-container table tr:hover) {
		background-color: var(--color-gray-100, #ececec);
	}

	:global(.dark .excel-table-container table tr:hover) {
		background-color: rgba(51, 51, 51, 0.5);
	}
</style>
