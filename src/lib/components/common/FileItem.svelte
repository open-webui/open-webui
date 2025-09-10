<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { formatFileSize } from '$lib/utils';
	import type { i18n as i18nType } from 'i18next';
	import type { Writable } from 'svelte/store';

	import FileItemModal from './FileItemModal.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Spinner from './Spinner.svelte';
	import Tooltip from './Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Mask from '$lib/components/icons/Mask.svelte';
	import { settings } from '$lib/stores';

	const i18n = getContext<Writable<i18nType>>('i18n');
	const dispatch = createEventDispatcher();

	export let className = 'w-60';
	export let colorClassName = 'bg-white dark:bg-gray-850 border border-gray-50 dark:border-white/5';
	export let url: string | null = null;

	export let dismissible = false;
	export let modal = false;
	export let loading = false;

	export let item: any = null;
	export let edit = false;
	export let small = false;

	export let name: string;
	export let type: string;
	export let size: number;
	export let enablePiiDetection: boolean = false;

	import { deleteFileById } from '$lib/apis/files';
	import { PiiSessionManager } from '$lib/utils/pii';

	let showModal = false;
	export let disableModal = false;
	export let conversationId: string | undefined = undefined;

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};

	// Stage label for processing
	$: processingStage = item?.file?.meta?.processing?.stage || null;
	$: stageText =
		processingStage === 'extracting'
			? 'Extracting text'
			: processingStage === 'pii_detection'
				? 'Masking PII'
				: item?.status === 'uploading'
					? 'Uploading'
					: null;

	// Get the display name and masking status
	$: ({ displayName, isFilenameMasked } = (() => {
		if (!enablePiiDetection || !name) {
			return { displayName: name, isFilenameMasked: false };
		}

		// Special handling for collections from PII-enabled knowledge bases
		if (type === 'collection') {
			// Check if this collection has PII detection enabled
			// Collections from the knowledge store retain their enable_pii_detection property
			const collectionHasPiiEnabled = item?.enable_pii_detection === true;

			if (collectionHasPiiEnabled) {
				// For collections, check if the name has been altered or if there's metadata indicating masking
				const hasOriginalNameInMeta = item?.meta?.name && item.meta.name !== name;

				// Also check PII session manager for any collection-related mappings
				const piiSessionManager = PiiSessionManager.getInstance();
				let mapping = null;

				if (conversationId) {
					const mappings = piiSessionManager.getFilenameMappingsForDisplay(conversationId);
					mapping = mappings.find((m) => m.fileId === name || m.maskedFilename === name);
				}

				if (!mapping) {
					const tempMappings = piiSessionManager.getTemporaryFilenameMappings();
					mapping = tempMappings.find((m) => m.fileId === name || m.maskedFilename === name);
				}

				if (hasOriginalNameInMeta) {
					return { displayName: item.meta.name, isFilenameMasked: true };
				}

				if (mapping && mapping.originalFilename) {
					return { displayName: mapping.originalFilename, isFilenameMasked: true };
				}

				// For PII-enabled collections, show PII badge to indicate they come from a PII-enabled source
				return { displayName: name, isFilenameMasked: true };
			}
		}

		// Original logic for files
		// Check if name looks like a UUID or file ID (indicating it's masked)
		const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
		const shortIdPattern = /^[a-zA-Z0-9_-]{8,32}$/;

		const looksLikeMaskedId =
			uuidPattern.test(name) || (shortIdPattern.test(name) && !name.includes('.'));

		if (looksLikeMaskedId) {
			const piiSessionManager = PiiSessionManager.getInstance();
			let mapping = null;

			// Try conversation-specific mappings first
			if (conversationId) {
				const mappings = piiSessionManager.getFilenameMappingsForDisplay(conversationId);
				mapping = mappings.find((m) => m.fileId === name || m.maskedFilename === name);
			}

			// For new chats without conversation ID, check temporary state
			if (!mapping) {
				const tempMappings = piiSessionManager.getTemporaryFilenameMappings();
				mapping = tempMappings.find((m) => m.fileId === name || m.maskedFilename === name);
			}

			// Also check if the item itself has the original name stored
			if (!mapping && item?.meta?.name && item.meta.name !== name) {
				return { displayName: item.meta.name, isFilenameMasked: true };
			}

			if (mapping && mapping.originalFilename) {
				return { displayName: mapping.originalFilename, isFilenameMasked: true };
			}
		}

		return { displayName: name, isFilenameMasked: looksLikeMaskedId };
	})());
</script>

{#if item && !disableModal}
	<FileItemModal bind:show={showModal} bind:item {edit} {conversationId} />
{/if}

<button
	class="relative group p-1.5 {className} flex items-center gap-1 {colorClassName} {small
		? 'rounded-xl'
		: 'rounded-2xl'} text-left"
	type="button"
	on:click={async () => {
		const isPdf =
			item?.meta?.content_type === 'application/pdf' ||
			(item?.name && item?.name.toLowerCase().endsWith('.pdf'));
		const isDocx =
			item?.meta?.content_type ===
				'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
			(item?.name && item?.name.toLowerCase().endsWith('.docx'));

		// Open modal unless disabled (used in KnowledgeBase)
		if (!disableModal && (item?.file?.data?.content || modal || isPdf || isDocx)) {
			showModal = !showModal;
		} else {
			if (url) {
				if (type === 'file') {
					window.open(`${url}/content`, '_blank')?.focus();
				} else {
					window.open(`${url}`, '_blank')?.focus();
				}
			}
		}

		dispatch('click');
	}}
>
	{#if item?.status === 'processing' || item?.status === 'uploading'}
		<!-- Stage-aware top progress bar -->
		{#key item?.file?.meta?.processing?.updated_at || item?.progress}
			<div
				class="absolute left-0 right-0 top-0 h-1.5 bg-gray-200 dark:bg-gray-800 overflow-hidden rounded-t-2xl"
			>
				<div
					class="h-full bg-sky-500 transition-all duration-300"
					style={`width: ${Math.min(100, Math.max(0, item?.file?.meta?.processing?.progress ?? item?.progress ?? 0))}%`}
				/>
			</div>
		{/key}
	{/if}
	{#if !small}
		<div class="p-3 bg-black/20 dark:bg-white/10 text-white rounded-xl">
			{#if !loading}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="currentColor"
					aria-hidden="true"
					class=" size-5"
				>
					<path
						fill-rule="evenodd"
						d="M5.625 1.5c-1.036 0-1.875.84-1.875 1.875v17.25c0 1.035.84 1.875 1.875 1.875h12.75c1.035 0 1.875-.84 1.875-1.875V12.75A3.75 3.75 0 0 0 16.5 9h-1.875a1.875 1.875 0 0 1-1.875-1.875V5.25A3.75 3.75 0 0 0 9 1.5H5.625ZM7.5 15a.75.75 0 0 1 .75-.75h7.5a.75.75 0 0 1 0 1.5h-7.5A.75.75 0 0 1 7.5 15Zm.75 2.25a.75.75 0 0 0 0 1.5H12a.75.75 0 0 0 0-1.5H8.25Z"
						clip-rule="evenodd"
					/>
					<path
						d="M12.971 1.816A5.23 5.23 0 0 1 14.25 5.25v1.875c0 .207.168.375.375.375H16.5a5.23 5.23 0 0 1 3.434 1.279 9.768 9.768 0 0 0-6.963-6.963Z"
					/>
				</svg>
			{:else}
				<Spinner />
			{/if}
		</div>
	{/if}

	{#if !small}
		<div class="flex flex-col justify-center -space-y-0.5 px-2.5 w-full">
			<div class="flex items-center gap-1.5 mb-1">
				<div class="dark:text-gray-100 text-sm font-medium line-clamp-1 flex-1">
					{decodeString(displayName)}
				</div>
				{#if isFilenameMasked}
					<Tooltip content={$i18n.t('Nenna Privacy active')} placement="top">
						<div
							class="flex items-center justify-center size-4 bg-sky-50 dark:bg-sky-200/10 text-sky-600 dark:text-sky-400 rounded-full"
						>
							<Mask className="size-2.5" />
						</div>
					</Tooltip>
				{/if}
			</div>

			<div
				class=" flex justify-between text-xs line-clamp-1 {($settings?.highContrastMode ?? false)
					? 'text-gray-800 dark:text-gray-100'
					: 'text-gray-500'}"
			>
				{#if type === 'file'}
					{$i18n.t('File')}
				{:else if type === 'doc'}
					{$i18n.t('Document')}
				{:else if type === 'collection'}
					{$i18n.t('Collection')}
				{:else}
					<span class=" capitalize line-clamp-1">{type}</span>
				{/if}
				<div class="flex items-center gap-1">
					{#if stageText}
						<span class="text-[11px] text-sky-600 dark:text-sky-400">{stageText}</span>
					{/if}
					{#if size}
						<span class="capitalize">{formatFileSize(size)}</span>
					{/if}
				</div>
			</div>
		</div>
	{:else}
		<Tooltip
			content={decodeString(displayName)}
			className="flex flex-col w-full"
			placement="top-start"
		>
			<div class="flex flex-col justify-center -space-y-0.5 px-2.5 w-full">
				<div class=" dark:text-gray-100 text-sm flex justify-between items-center">
					{#if loading}
						<div class=" shrink-0 mr-2">
							<Spinner className="size-4" />
						</div>
					{/if}
					<div class="font-medium line-clamp-1 flex-1">{decodeString(displayName)}</div>
					{#if isFilenameMasked}
						<Tooltip
							content={type === 'collection'
								? $i18n.t('From PII-enabled knowledge base')
								: $i18n.t('Filename masked for privacy')}
							placement="top"
						>
							<div
								class="flex items-center justify-center size-4 bg-sky-50 dark:bg-sky-200/10 text-sky-600 dark:text-sky-400 rounded-full mx-1 flex-shrink-0"
							>
								<Mask className="size-2.5" />
							</div>
						</Tooltip>
					{/if}
					<div class="text-gray-500 text-xs capitalize shrink-0">{formatFileSize(size)}</div>
				</div>
			</div>
		</Tooltip>
	{/if}

	{#if dismissible}
		<div class=" absolute -top-1 -right-1">
			<button
				aria-label={$i18n.t('Remove File')}
				class=" bg-white text-black border border-gray-50 rounded-full {($settings?.highContrastMode ??
				false)
					? ''
					: 'outline-hidden focus:outline-hidden group-hover:visible invisible transition'}"
				type="button"
				on:click|stopPropagation={() => {
					dispatch('dismiss');
				}}
			>
				<XMark className={'size-4'} />
			</button>

			<!-- <button
				class=" p-1 dark:text-gray-300 dark:hover:text-white hover:bg-black/5 dark:hover:bg-white/5 rounded-full group-hover:visible invisible transition"
				type="button"
				on:click={() => {
				}}
			>
				<GarbageBin />
			</button> -->
		</div>
	{/if}
</button>
