<script lang="ts">
	import Fuse from 'fuse.js';
	import { getContext, onDestroy, onMount, tick } from 'svelte';

	import {
		chatId as activeChatId,
		folders,
		models,
		selectedTerminalId,
		settings,
		terminalServers
	} from '$lib/stores';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { getFolders } from '$lib/apis/folders';
	import { searchKnowledgeBases, searchKnowledgeFiles } from '$lib/apis/knowledge';
	import { searchFiles } from '$lib/apis/terminal';
	import { decodeString, isValidHttpUrl, isYoutubeUrl } from '$lib/utils';
	import { isTemporaryChatId } from '$lib/utils/chatId';

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
	let filesystemItems: any[] = [];
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
		...filesystemItems,
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
		const terminal = getSelectedTerminal();
		getFilesystemItems(terminal);
		getFolderItems();
		getKnowledgeItems();
		getKnowledgeFileItems();
	};

	const getFilesystemItems = async (terminal = getSelectedTerminal()) => {
		if (!terminal) {
			filesystemItems = [];
			return;
		}

		const res = await searchFiles(
			terminal.url,
			terminal.key,
			query,
			'.',
			20,
			'any',
			$activeChatId || undefined,
			localStorage.getItem('fileNav:showHidden') === 'true'
		).catch(() => null);

		filesystemItems = (res?.results ?? []).map((item: any) => ({
			...item,
			type: 'filesystem',
			filesystem_type: item.type,
			id: item.path,
			url: item.path,
			name: item.name,
			description: item.path,
			status: 'processed'
		}));
	};

	const chatContext = (terminal: any) => terminal?.contexts?.chat ?? {};

	const getSelectedTerminal = (): { url: string; key: string } | null => {
		if (!$selectedTerminalId) return null;

		const systemTerminal = ($terminalServers ?? []).find(
			(t) => t.id && t.id === $selectedTerminalId
		);
		const systemChatContext = chatContext(systemTerminal);
		if (systemTerminal) {
			if (
				systemChatContext === false ||
				(isTemporaryChatId($activeChatId) && systemChatContext?.context_id === 'chat_id')
			) {
				return null;
			}

			return { url: systemTerminal.url, key: localStorage.token };
		}

		const directTerminal = ($settings?.terminalServers ?? []).find(
			(t: any) => t.url === $selectedTerminalId && t.enabled
		);
		return directTerminal?.url ? { url: directTerminal.url, key: directTerminal.key ?? '' } : null;
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
		if (item.type === 'filesystem') {
			onSelect({ type: 'filesystem', data: item });
			return;
		}

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
			<div class="px-2 py-1 text-[0.6875rem] text-gray-500 dark:text-gray-400">
				{#if item?.type === 'folder'}
					{$i18n.t('Folders')}
				{:else if item?.type === 'collection'}
					{$i18n.t('Collections')}
				{:else if item?.type === 'file'}
					{$i18n.t('Files')}
				{:else if item?.type === 'filesystem'}
					{$i18n.t('Filesystem')}
				{/if}
			</div>
		{/if}

		<button
			class="flex h-[1.6875rem] w-full max-w-full items-center justify-between overflow-hidden rounded-xl px-2 text-left text-[0.8125rem] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {itemIdx ===
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
			<div
				class="flex w-full min-w-0 items-center gap-1.5 overflow-hidden text-black dark:text-gray-100"
			>
				<Tooltip
					className="shrink-0 flex"
					content={item?.legacy
						? $i18n.t('Legacy')
						: item?.type === 'filesystem'
							? item?.path
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
					{:else if item?.type === 'folder' || item?.filesystem_type === 'directory'}
						<Folder className="size-3.5" />
					{:else if item?.type === 'youtube'}
						<Youtube className="size-3.5" />
					{:else if item?.type === 'web'}
						<GlobeAlt className="size-3.5" />
					{:else}
						<DocumentPage className="size-3.5" />
					{/if}
				</Tooltip>

				<Tooltip
					className="min-w-0 flex-1"
					content={`${decodeString(item?.name)}`}
					placement="top-start"
				>
					<div class="line-clamp-1 min-w-0 overflow-hidden break-all">
						{decodeString(item?.name)}
					</div>
				</Tooltip>
			</div>
		</button>
	{/each}
{/if}

{#if filteredModels.length > 0}
	<div class="px-2 py-1 text-[0.6875rem] text-gray-500 dark:text-gray-400">
		{$i18n.t('Models')}
	</div>

	{#each filteredModels as model, modelIdx}
		{@const itemIdx = knowledgeResults.length + modelIdx}
		<Tooltip content={model.id} placement="top-start">
			<button
				class="flex h-[1.6875rem] w-full items-center rounded-xl px-2 text-left text-[0.8125rem] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {itemIdx ===
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
							// LICENSE covers this Open WebUI fallback logo.
							// Do not alter, remove, obscure, or replace it except as LICENSE permits:
							// https://docs.openwebui.com/license.
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
