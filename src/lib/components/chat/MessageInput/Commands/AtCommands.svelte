<script lang="ts">
	import Fuse from 'fuse.js';
	import { getContext, onDestroy, onMount, tick } from 'svelte';

	import { folders, models } from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getFolders } from '$lib/apis/folders';
	import { searchKnowledgeBases, searchKnowledgeFiles } from '$lib/apis/knowledge';
	import { decodeString, isValidHttpUrl, isYoutubeUrl } from '$lib/utils';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Youtube from '$lib/components/icons/Youtube.svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext<any>('i18n');

	export let query = '';
	export let onSelect: (e: any) => void = () => {};

	let selectedIdx = 0;
	export let filteredItems: any[] = [];
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	let folderItems: any[] = [];
	let knowledgeItems: any[] = [];
	let fileItems: any[] = [];
	let modelItems: any[] = [];
	let filteredModels: any[] = [];
	let knowledgeResults: any[] = [];

	$: modelItems = (($models ?? []) as any[])
		.filter((model) => !model?.info?.meta?.hidden)
		.map((model) => ({
			...model,
			modelName: model?.name,
			tags: model?.info?.meta?.tags?.map((tag: any) => tag.name).join(' '),
			desc: model?.info?.meta?.description
		}));

	$: fuse = new Fuse(modelItems, {
		keys: ['value', 'tags', 'modelName'],
		threshold: 0.5
	});

	$: filteredModels = query ? fuse.search(query).map((e) => e.item) : modelItems;
	$: knowledgeResults = [
		...(query.startsWith('http')
			? isYoutubeUrl(query)
				? [{ type: 'youtube', name: query, description: query }]
				: [{ type: 'web', name: query, description: query }]
			: []),
		...folderItems,
		...knowledgeItems,
		...fileItems
	];

	$: filteredItems = [
		...knowledgeResults.map((data) => ({ type: data.type, data })),
		...filteredModels.map((data) => ({ type: 'model', data }))
	];

	$: if (query) {
		selectedIdx = 0;
	}

	$: selectedIdx = Math.min(selectedIdx, Math.max(filteredItems.length - 1, 0));

	$: if (query !== undefined) {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			getItems();
		}, 200);
	}

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});

	const getItems = () => {
		getFolderItems();
		getKnowledgeItems();
		getKnowledgeFileItems();
	};

	const getFolderItems = () => {
		folderItems = (($folders ?? []) as any[])
			.map((folder) => ({
				...folder,
				type: 'folder',
				description: $i18n.t('Folder'),
				title: folder.name
			}))
			.filter((folder: any) => folder.name.toLowerCase().includes(query.toLowerCase()));
	};

	const getKnowledgeItems = async () => {
		const res = await searchKnowledgeBases(localStorage.token, query).catch(() => null);

		if (res) {
			knowledgeItems = res.items.map((item: any) => ({
				...item,
				type: 'collection'
			}));
		}
	};

	const getKnowledgeFileItems = async () => {
		const res = await searchKnowledgeFiles(localStorage.token, query).catch(() => null);

		if (res) {
			fileItems = res.items.map((item: any) => ({
				...item,
				type: 'file',
				name: item.filename,
				description: item.collection ? item.collection.name : ''
			}));
		}
	};

	const selectKnowledgeItem = (item: any) => {
		if (['youtube', 'web'].includes(item.type)) {
			if (isValidHttpUrl(query)) {
				onSelect({ type: 'web', data: query });
			} else {
				toast.error(
					$i18n.t('Oops! Looks like the URL is invalid. Please double-check and try again.')
				);
			}
			return;
		}

		onSelect({ type: 'knowledge', data: item });
	};

	export const selectUp = () => {
		selectedIdx = Math.max(0, selectedIdx - 1);
	};

	export const selectDown = () => {
		selectedIdx = Math.min(selectedIdx + 1, filteredItems.length - 1);
	};

	export const select = async () => {
		const item = filteredItems[selectedIdx];
		if (!item) return;

		if (item.type === 'model') {
			onSelect({ type: 'model', data: item.data });
		} else {
			selectKnowledgeItem(item.data);
		}
	};

	onMount(async () => {
		if ($folders === null) {
			await folders.set(await getFolders(localStorage.token));
		}

		await tick();
	});
</script>

{#if knowledgeResults.length > 0 || query.startsWith('http')}
	{#each knowledgeResults as item, idx}
		{@const itemIdx = idx}
		{#if idx === 0 || item?.type !== knowledgeResults[idx - 1]?.type}
			<div class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400">
				{#if item?.type === 'folder'}
					{$i18n.t('Folders')}
				{:else if item?.type === 'collection'}
					{$i18n.t('Collections')}
				{:else if item?.type === 'file'}
					{$i18n.t('Files')}
				{/if}
			</div>
		{/if}

		<button
			class="flex h-[1.6875rem] w-full items-center justify-between rounded-xl px-2 text-left text-[13px] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {itemIdx ===
			selectedIdx
				? 'bg-gray-50/40 dark:bg-gray-800/40 dark:text-gray-100 selected-command-option-button'
				: ''}"
			type="button"
			on:click={() => {
				selectKnowledgeItem(item);
			}}
			on:mousemove={() => {
				selectedIdx = itemIdx;
			}}
			data-selected={itemIdx === selectedIdx}
		>
			<div class="flex min-w-0 items-center gap-1.5 text-black dark:text-gray-100">
				<Tooltip
					content={item?.legacy
						? $i18n.t('Legacy')
						: item?.type === 'file'
							? `${item?.collection?.name} > ${$i18n.t('File')}`
							: item?.type === 'collection'
								? $i18n.t('Collection')
								: item?.type === 'youtube'
									? $i18n.t('YouTube')
									: item?.type === 'web'
										? $i18n.t('Web')
										: ''}
					placement="top"
				>
					{#if item?.type === 'collection'}
						<Database className="size-3.5" />
					{:else if item?.type === 'folder'}
						<Folder className="size-3.5" />
					{:else if item?.type === 'youtube'}
						<Youtube className="size-3.5" />
					{:else if item?.type === 'web'}
						<GlobeAlt className="size-3.5" />
					{:else}
						<DocumentPage className="size-3.5" />
					{/if}
				</Tooltip>

				<Tooltip content={`${decodeString(item?.name)}`} placement="top-start">
					<div class="min-w-0 flex-1 truncate">
						{decodeString(item?.name)}
					</div>
				</Tooltip>
			</div>
		</button>
	{/each}
{/if}

{#if filteredModels.length > 0}
	<div class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400">
		{$i18n.t('Models')}
	</div>

	{#each filteredModels as model, modelIdx}
		{@const itemIdx = knowledgeResults.length + modelIdx}
		<Tooltip content={model.id} placement="top-start">
			<button
				class="flex h-[1.6875rem] w-full items-center rounded-xl px-2 text-left text-[13px] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {itemIdx ===
				selectedIdx
					? 'bg-gray-50/40 dark:bg-gray-800/40 selected-command-option-button'
					: ''}"
				type="button"
				on:click={() => {
					onSelect({ type: 'model', data: model });
				}}
				on:mousemove={() => {
					selectedIdx = itemIdx;
				}}
				on:focus={() => {}}
				data-selected={itemIdx === selectedIdx}
			>
				<div class="flex min-w-0 items-center text-black dark:text-gray-100">
					<img
						src={`${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}&lang=${$i18n.language}`}
						alt={model?.name ?? model.id}
						class="mr-2 size-4.5 rounded-full object-cover"
						on:error={(e) => {
							(e.currentTarget as HTMLImageElement).src = '/favicon.png';
						}}
					/>
					<div class="min-w-0 truncate">
						{model.name}
					</div>
				</div>
			</button>
		</Tooltip>
	{/each}
{/if}
