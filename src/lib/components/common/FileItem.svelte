<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { formatFileSize } from '$lib/utils';

	import FileItemModal from './FileItemModal.svelte';
	import GarbageBin from '../icons/GarbageBin.svelte';
	import Spinner from './Spinner.svelte';
	import Tooltip from './Tooltip.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import { settings } from '$lib/stores';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let className = 'w-60';
	export let colorClassName =
		'bg-white dark:bg-gray-850 border border-gray-50/30 dark:border-gray-800/30';
	export let url: string | null = null;

	export let dismissible = false;
	export let modal = false;
	export let loading = false;

	export let item = null;
	export let edit = false;
	export let small = false;

	export let name: string;
	export let type: string;
	export let size: number;

	import DocumentPage from '../icons/DocumentPage.svelte';
	import Database from '../icons/Database.svelte';
	import PageEdit from '../icons/PageEdit.svelte';
	import ChatBubble from '../icons/ChatBubble.svelte';
	import Folder from '../icons/Folder.svelte';
	let showModal = false;

	const decodeString = (str: string) => {
		try {
			return decodeURIComponent(str);
		} catch (e) {
			return str;
		}
	};
</script>

{#if item}
	<FileItemModal bind:show={showModal} bind:item {edit} />
{/if}

<button
	class="relative group p-1.5 {className} flex items-center gap-1 {colorClassName} {small
		? 'rounded-xl p-2'
		: 'rounded-2xl'} text-left"
	type="button"
	on:click={async () => {
		if (item?.file?.data?.content || item?.type === 'file' || modal) {
			showModal = !showModal;
		} else {
			if (url) {
				if (type === 'file') {
					window.open(`${url}/content`, '_blank').focus();
				} else {
					window.open(`${url}`, '_blank').focus();
				}
			}
		}

		dispatch('click');
	}}
>
	{#if !small}
		<div
			class="size-10 shrink-0 flex justify-center items-center bg-black/20 dark:bg-white/10 text-white rounded-xl"
		>
			{#if !loading}
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 24 24"
					fill="currentColor"
					aria-hidden="true"
					class=" size-4.5"
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
	{:else}
		<div class="pl-1.5">
			{#if !loading}
				<Tooltip
					content={type === 'collection'
						? $i18n.t('Collection')
						: type === 'note'
							? $i18n.t('Note')
							: type === 'chat'
								? $i18n.t('Chat')
								: type === 'file'
									? $i18n.t('File')
									: $i18n.t('Document')}
					placement="top"
				>
					{#if type === 'collection'}
						<Database />
					{:else if type === 'note'}
						<PageEdit />
					{:else if type === 'chat'}
						<ChatBubble />
					{:else if type === 'folder'}
						<Folder />
					{:else}
						<DocumentPage />
					{/if}
				</Tooltip>
			{:else}
				<Spinner />
			{/if}
		</div>
	{/if}

	{#if !small}
		<div class="flex flex-col justify-center -space-y-0.5 px-2.5 w-full">
			<div class=" dark:text-gray-100 text-sm font-medium line-clamp-1 mb-1">
				{decodeString(name)}
			</div>

			<div
				class=" flex justify-between text-xs line-clamp-1 {($settings?.highContrastMode ?? false)
					? 'text-gray-800 dark:text-gray-100'
					: 'text-gray-500'}"
			>
				{#if type === 'file'}
					{$i18n.t('File')}
				{:else if type === 'note'}
					{$i18n.t('Note')}
				{:else if type === 'doc'}
					{$i18n.t('Document')}
				{:else if type === 'collection'}
					{$i18n.t('Collection')}
				{:else}
					<span class=" capitalize line-clamp-1">{type}</span>
				{/if}
				{#if size}
					<span class="capitalize">{formatFileSize(size)}</span>
				{/if}
			</div>
		</div>
	{:else}
		<Tooltip content={decodeString(name)} className="flex flex-col w-full" placement="top-start">
			<div class="flex flex-col justify-center -space-y-0.5 px-1 w-full">
				<div class=" dark:text-gray-100 text-sm flex justify-between items-center">
					<div class="font-medium line-clamp-1 flex-1 pr-1">{decodeString(name)}</div>
					{#if size}
						<div class="text-gray-500 text-xs capitalize shrink-0">{formatFileSize(size)}</div>
					{:else}
						<div class="text-gray-500 text-xs capitalize shrink-0">{type}</div>
					{/if}
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
