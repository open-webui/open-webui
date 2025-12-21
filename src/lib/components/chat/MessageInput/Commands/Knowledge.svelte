<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { tick, getContext, onMount, onDestroy } from 'svelte';

	import { folders } from '$lib/stores';
	import { getFolders } from '$lib/apis/folders';
	import { searchKnowledgeBases, searchKnowledgeFiles } from '$lib/apis/knowledge';
	import { removeLastWordFromString, isValidHttpUrl, isYoutubeUrl, decodeString } from '$lib/utils';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Youtube from '$lib/components/icons/Youtube.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';

	const i18n = getContext('i18n');

	export let query = '';
	export let onSelect = (e) => {};

	let selectedIdx = 0;
	let items = [];

	export let filteredItems = [];
	$: filteredItems = [
		...(query.startsWith('http')
			? isYoutubeUrl(query)
				? [{ type: 'youtube', name: query, description: query }]
				: [
						{
							type: 'web',
							name: query,
							description: query
						}
					]
			: []),
		...items
	];

	$: if (query) {
		selectedIdx = 0;
	}

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};

	export const select = async () => {
		// find item with data-selected=true
		const item = document.querySelector(`[data-selected="true"]`);
		if (item) {
			// click the item
			item.click();
		}
	};

	let folderItems = [];
	let knowledgeItems = [];
	let fileItems = [];

	$: items = [...folderItems, ...knowledgeItems, ...fileItems];

	$: if (query !== null) {
		getItems();
	}

	const getItems = () => {
		getFolderItems();
		getKnowledgeItems();
		getKnowledgeFileItems();
	};

	const getFolderItems = async () => {
		folderItems = $folders
			.map((folder) => ({
				...folder,
				type: 'folder',
				description: $i18n.t('Folder'),
				title: folder.name
			}))
			.filter((folder) => folder.name.toLowerCase().includes(query.toLowerCase()));
	};

	const getKnowledgeItems = async () => {
		const res = await searchKnowledgeBases(localStorage.token, query).catch(() => {
			return null;
		});

		if (res) {
			knowledgeItems = res.items.map((item) => {
				return {
					...item,
					type: 'collection'
				};
			});
		}
	};

	const getKnowledgeFileItems = async () => {
		const res = await searchKnowledgeFiles(localStorage.token, query).catch(() => {
			return null;
		});

		if (res) {
			fileItems = res.items.map((item) => {
				return {
					...item,
					type: 'file',
					name: item.filename,
					description: item.collection ? item.collection.name : ''
				};
			});
		}
	};

	onMount(async () => {
		if ($folders === null) {
			await folders.set(await getFolders(localStorage.token));
		}

		await tick();
	});

	const onKeyDown = (e) => {
		if (e.key === 'Enter') {
			e.preventDefault();
			select();
		}
	};
	onMount(() => {
		window.addEventListener('keydown', onKeyDown);
	});

	onDestroy(() => {
		window.removeEventListener('keydown', onKeyDown);
	});
</script>

{#if filteredItems.length > 0 || query.startsWith('http')}
	{#each filteredItems as item, idx}
		{#if idx === 0 || item?.type !== items[idx - 1]?.type}
			<div class="px-2 text-xs text-gray-500 py-1">
				{#if item?.type === 'folder'}
					{$i18n.t('Folders')}
				{:else if item?.type === 'collection'}
					{$i18n.t('Collections')}
				{:else if item?.type === 'file'}
					{$i18n.t('Files')}
				{/if}
			</div>
		{/if}

		{#if !['youtube', 'web'].includes(item.type)}
			<button
				class=" px-2 py-1 rounded-xl w-full text-left flex justify-between items-center {idx ===
				selectedIdx
					? ' bg-gray-50 dark:bg-gray-800 dark:text-gray-100 selected-command-option-button'
					: ''}"
				type="button"
				on:click={() => {
					console.log(item);
					onSelect({
						type: 'knowledge',
						data: item
					});
				}}
				on:mousemove={() => {
					selectedIdx = idx;
				}}
				data-selected={idx === selectedIdx}
			>
				<div class="  text-black dark:text-gray-100 flex items-center gap-1">
					<Tooltip
						content={item?.legacy
							? $i18n.t('Legacy')
							: item?.type === 'file'
								? `${item?.collection?.name} > ${$i18n.t('File')}`
								: item?.type === 'collection'
									? $i18n.t('Collection')
									: ''}
						placement="top"
					>
						{#if item?.type === 'collection'}
							<Database className="size-4" />
						{:else if item?.type === 'folder'}
							<Folder className="size-4" />
						{:else}
							<DocumentPage className="size-4" />
						{/if}
					</Tooltip>

					<Tooltip content={`${decodeString(item?.name)}`} placement="top-start">
						<div class="line-clamp-1 flex-1">
							{decodeString(item?.name)}
						</div>
					</Tooltip>
				</div>
			</button>
		{/if}
	{/each}

	{#if isYoutubeUrl(query)}
		<button
			class="px-2 py-1 rounded-xl w-full text-left bg-gray-50 dark:bg-gray-800 dark:text-gray-100 selected-command-option-button"
			type="button"
			data-selected={true}
			on:click={() => {
				if (isValidHttpUrl(query)) {
					onSelect({
						type: 'web',
						data: query
					});
				} else {
					toast.error(
						$i18n.t('Oops! Looks like the URL is invalid. Please double-check and try again.')
					);
				}
			}}
		>
			<div class="  text-black dark:text-gray-100 line-clamp-1 flex items-center gap-1">
				<Tooltip content={$i18n.t('YouTube')} placement="top">
					<Youtube className="size-4" />
				</Tooltip>

				<div class="truncate flex-1">
					{query}
				</div>
			</div>
		</button>
	{:else if query.startsWith('http')}
		<button
			class="px-2 py-1 rounded-xl w-full text-left bg-gray-50 dark:bg-gray-800 dark:text-gray-100 selected-command-option-button"
			type="button"
			data-selected={true}
			on:click={() => {
				if (isValidHttpUrl(query)) {
					onSelect({
						type: 'web',
						data: query
					});
				} else {
					toast.error(
						$i18n.t('Oops! Looks like the URL is invalid. Please double-check and try again.')
					);
				}
			}}
		>
			<div class="  text-black dark:text-gray-100 line-clamp-1 flex items-center gap-1">
				<Tooltip content={$i18n.t('Web')} placement="top">
					<GlobeAlt className="size-4" />
				</Tooltip>

				<div class="truncate flex-1">
					{query}
				</div>
			</div>
		</button>
	{/if}
{/if}
