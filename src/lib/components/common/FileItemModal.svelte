<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { formatFileSize, getLineCount } from '$lib/utils';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');
	import Modal from './Modal.svelte';
	import XMark from '../icons/XMark.svelte';
	import Info from '../icons/Info.svelte';
	import Switch from './Switch.svelte';
	import Tooltip from './Tooltip.svelte';

	export let item;
	export let show = false;
	export let edit = false;

	let enableFullContent = false;
	let pdfObjectUrl = '';
	let pdfLoading = false;
	let errorMessage = '';
	$: isPDF =
		item?.meta?.content_type === 'application/pdf' ||
		(item?.name && item?.name.toLowerCase().endsWith('.pdf'));

	onMount(() => {
		console.log(item);
		if (item?.context === 'full') {
			enableFullContent = true;
		}

		if (isPDF && item?.id) {
			loadFileContent();
		}

		return () => {
			if (pdfObjectUrl) {
				URL.revokeObjectURL(pdfObjectUrl);
			}
		};
	});

	const loadFileContent = async () => {
		if (!isPDF || !item?.id) return;

		try {
			pdfLoading = true;
			errorMessage = '';

			const token = localStorage.getItem('token');

			if (!token) {
				errorMessage = 'No authentication token found. Please log in again.';
				console.error('No token found in localStorage');
				return;
			}

			const response = await fetch(`${WEBUI_API_BASE_URL}/files/${item.id}/content`, {
				method: 'GET',
				headers: {
					Accept: 'application/pdf',
					Authorization: `Bearer ${token}`
				}
			});

			if (!response.ok) {
				const errorData = await response.json();
				errorMessage = errorData.detail || 'Failed to load PDF';
				console.error('Error loading PDF:', errorData);
				return;
			}

			const blob = await response.blob();

			if (pdfObjectUrl) {
				URL.revokeObjectURL(pdfObjectUrl); // Nettoyer l'ancien URL
			}
			pdfObjectUrl = URL.createObjectURL(blob);
		} catch (error) {
			console.error('Error loading file content:', error);
			errorMessage =
				error instanceof Error ? error.message : 'An error occurred while loading the PDF';
		} finally {
			pdfLoading = false;
		}
	};

	$: if (item?.id && isPDF) {
		loadFileContent();
	}
</script>

<Modal bind:show size="lg">
	<div class="font-primary px-6 py-5 w-full flex flex-col justify-center dark:text-gray-400">
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
					<div class=" flex flex-wrap text-sm gap-1 text-gray-500">
						{#if item.size}
							<div class="capitalize shrink-0">{formatFileSize(item.size)}</div>
							•
						{/if}

						{#if item?.file?.data?.content}
							<div class="capitalize shrink-0">
								{getLineCount(item?.file?.data?.content ?? '')} extracted lines
							</div>

							<div class="flex items-center gap-1 shrink-0">
								<Info />

								Formatting may be inconsistent from source.
							</div>
						{/if}
					</div>

					{#if edit}
						<div>
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
										Using Entire Document
									{:else}
										Using Focused Retrieval
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
			{#if isPDF}
				{#if pdfLoading}
					<div class="flex justify-center items-center h-[70vh]">
						<div class="text-center">
							<div
								class="inline-block animate-spin h-8 w-8 border-4 border-gray-300 border-t-blue-600 rounded-full"
							></div>
							<p class="mt-2">Loading PDF...</p>
						</div>
					</div>
				{:else if errorMessage}
					<div class="flex justify-center items-center h-[70vh]">
						<div class="text-center text-red-500">
							<p>Error: {errorMessage}</p>
							<button
								class="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
								on:click={loadFileContent}
							>
								Retry
							</button>
						</div>
					</div>
				{:else if pdfObjectUrl}
					<iframe
						title={item?.name}
						src={pdfObjectUrl}
						class="w-full h-[70vh] border-0 rounded-lg mt-4"
					/>
				{/if}
			{:else}
				<div class="max-h-96 overflow-scroll scrollbar-hidden text-xs whitespace-pre-wrap">
					{item?.file?.data?.content ?? 'No content'}
				</div>
			{/if}
		</div>
	</div>
</Modal>
