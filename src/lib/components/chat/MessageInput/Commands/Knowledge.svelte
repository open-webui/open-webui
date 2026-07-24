<script lang="ts">
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { tick, getContext, onMount, onDestroy } from 'svelte';

	import { folders } from '$lib/stores';
	import { getFolders } from '$lib/apis/folders';
	import {
		searchKnowledgeBases,
		searchKnowledgeFiles,
		searchKnowledgeFilesById
	} from '$lib/apis/knowledge';
	import { removeLastWordFromString, isValidHttpUrl, isYoutubeUrl, decodeString } from '$lib/utils';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Database from '$lib/components/icons/Database.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Youtube from '$lib/components/icons/Youtube.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import ArrowLeft from '$lib/components/icons/ArrowLeft.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext('i18n');

	export let query = '';
	export let onSelect = (e) => {};

	let selectedIdx = 0;
	let items = [];
	let searchDebounceTimer: ReturnType<typeof setTimeout>;

	// --- Browsing state ---
	let browsingCollection = null;
	let currentDirectoryId = null; // null = root level of the KB
	let browsingFiles = [];
	let browsingDirectories = [];
	let browsingBreadcrumbs = [];
	let browsingLoading = false;

	export let filteredItems = [];
	$: {
		if (browsingCollection) {
			const dirItems = browsingDirectories.map((d) => ({
				...d,
				type: 'directory'
			}));
			const fItems = browsingFiles.map((f) => ({
				...f,
				type: 'file',
				name: f?.meta?.name || f.filename
			}));
			const combined = [...dirItems, ...fItems];
			// Always keep at least one placeholder so the dropdown stays visible
			filteredItems =
				combined.length > 0
					? combined
					: browsingLoading
						? [{ type: 'browsing-loading', name: '' }]
						: [{ type: 'browsing-empty', name: '' }];
		} else {
			filteredItems = [
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
		}
	}

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

	$: if (query !== undefined) {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (browsingCollection) {
				loadBrowsingItems();
			} else {
				getItems();
			}
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

	// --- Browsing functions ---

	const browseIntoCollection = async (collection) => {
		browsingCollection = collection;
		currentDirectoryId = null;
		selectedIdx = 0;
		await loadBrowsingItems();
	};

	const browseIntoDirectory = async (dir) => {
		currentDirectoryId = dir.id;
		selectedIdx = 0;
		await loadBrowsingItems();
	};

	const navigateBack = async () => {
		if (browsingBreadcrumbs.length > 0) {
			// Go up one level — parent is the second-to-last breadcrumb
			const parentCrumb =
				browsingBreadcrumbs.length >= 2
					? browsingBreadcrumbs[browsingBreadcrumbs.length - 2]
					: null;
			currentDirectoryId = parentCrumb ? parentCrumb.id : null;
			selectedIdx = 0;
			await loadBrowsingItems();
		} else {
			// Back to top-level view
			browsingCollection = null;
			currentDirectoryId = null;
			browsingFiles = [];
			browsingDirectories = [];
			browsingBreadcrumbs = [];
			selectedIdx = 0;
		}
	};

	const loadBrowsingItems = async () => {
		if (!browsingCollection) return;
		browsingLoading = true;

		const res = await searchKnowledgeFilesById(
			localStorage.token,
			browsingCollection.id,
			query || null,
			null,
			null,
			null,
			1,
			currentDirectoryId
		).catch(() => null);

		if (res) {
			browsingFiles = res.items || [];
			browsingDirectories = res.directories || [];
			browsingBreadcrumbs = res.breadcrumbs || [];
		}

		browsingLoading = false;
	};

	const selectDirectory = async (dir) => {
		// Fetch all files directly in this directory
		const allFiles = [];
		let page = 1;
		while (true) {
			const res = await searchKnowledgeFilesById(
				localStorage.token,
				browsingCollection.id,
				null,
				null,
				null,
				null,
				page,
				dir.id
			).catch(() => null);

			if (!res || !res.items || res.items.length === 0) break;
			allFiles.push(...res.items);
			if (allFiles.length >= res.total) break;
			page++;
		}

		if (allFiles.length === 0) {
			toast.info($i18n.t('No files in this directory.'));
			return;
		}

		onSelect({
			type: 'knowledge-directory',
			data: {
				files: allFiles.map((file) => ({
					...file,
					type: 'file',
					name: file?.meta?.name || file.filename,
					collection: { name: browsingCollection.name }
				}))
			}
		});
	};

	const selectBrowsingFile = (file) => {
		onSelect({
			type: 'knowledge',
			data: {
				...file,
				type: 'file',
				name: file?.meta?.name || file.filename,
				collection: { name: browsingCollection.name }
			}
		});
	};

	const selectEntireCollection = () => {
		onSelect({
			type: 'knowledge',
			data: { ...browsingCollection, type: 'collection' }
		});
	};

	// Derived: current location name for the header
	$: currentLocationName =
		browsingBreadcrumbs.length > 0
			? browsingBreadcrumbs[browsingBreadcrumbs.length - 1]?.name
			: (browsingCollection?.name ?? '');

	onMount(async () => {
		if ($folders === null) {
			await folders.set(await getFolders(localStorage.token));
		}

		await tick();
	});
</script>

{#if browsingCollection}
	<!-- Browsing view: inside a knowledge base -->
	<div class="px-2 py-1.5 flex items-center gap-1.5 border-b border-gray-100 dark:border-gray-800">
		<button
			type="button"
			class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition"
			on:click={navigateBack}
		>
			<ArrowLeft className="size-3.5" strokeWidth="2" />
		</button>

		<div class="flex-1 min-w-0">
			<div class="text-xs text-gray-500 dark:text-gray-400 truncate flex items-center gap-0.5">
				<button
					type="button"
					class="hover:text-gray-700 dark:hover:text-gray-200 transition truncate"
					on:click={() => {
						if (browsingBreadcrumbs.length > 0) {
							currentDirectoryId = null;
							selectedIdx = 0;
							loadBrowsingItems();
						}
					}}
				>
					{decodeString(browsingCollection?.name)}
				</button>
				{#each browsingBreadcrumbs as crumb, i}
					<span class="flex-shrink-0">/</span>
					<button
						type="button"
						class="hover:text-gray-700 dark:hover:text-gray-200 transition truncate"
						on:click={() => {
							currentDirectoryId = crumb.id;
							selectedIdx = 0;
							loadBrowsingItems();
						}}
					>
						{crumb.name}
					</button>
				{/each}
			</div>
		</div>

		<Tooltip
			content={browsingBreadcrumbs.length > 0
				? $i18n.t('Select directory')
				: $i18n.t('Select collection')}
			placement="top"
		>
			<button
				type="button"
				class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition opacity-60 hover:opacity-100"
				on:click={() => {
					if (browsingBreadcrumbs.length > 0) {
						selectDirectory({
							id: currentDirectoryId,
							name: currentLocationName
						});
					} else {
						selectEntireCollection();
					}
				}}
			>
				<Plus className="size-3.5" />
			</button>
		</Tooltip>
	</div>

	{#if browsingLoading}
		<div class="flex justify-center py-3">
			<Spinner className="size-3.5" />
		</div>
	{:else if browsingDirectories.length === 0 && browsingFiles.length === 0}
		<div class="px-2 py-3 text-center text-xs text-gray-400 dark:text-gray-500 italic">
			{$i18n.t('This directory is empty.')}
		</div>
	{:else}
		{@const allBrowsingItems = [
			...browsingDirectories.map((d) => ({ ...d, _itemType: 'directory' })),
			...browsingFiles.map((f) => ({
				...f,
				_itemType: 'file',
				name: f?.meta?.name || f.filename
			}))
		]}

		{#each allBrowsingItems as item, idx}
			{#if idx === 0 || item._itemType !== allBrowsingItems[idx - 1]?._itemType}
				<div class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400">
					{#if item._itemType === 'directory'}
						{$i18n.t('Directories')}
					{:else}
						{$i18n.t('Files')}
					{/if}
				</div>
			{/if}

			{#if item._itemType === 'directory'}
				<div
					class="flex h-[1.6875rem] w-full items-center justify-between rounded-xl px-2 text-left text-[13px] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {idx ===
					selectedIdx
						? 'bg-gray-50/40 dark:bg-gray-800/40 dark:text-gray-100 selected-command-option-button'
						: ''}"
				>
					<button
						type="button"
						class="flex min-w-0 flex-1 items-center gap-1.5 text-left text-black dark:text-gray-100"
						data-selected={idx === selectedIdx}
						on:click={() => browseIntoDirectory(item)}
						on:mousemove={() => {
							selectedIdx = idx;
						}}
					>
						<Folder className="size-3.5" />
						<Tooltip content={item.name} placement="top-start">
							<div class="min-w-0 flex-1 truncate">{item.name}</div>
						</Tooltip>
					</button>

					<div class="ml-1 flex items-center gap-0.5">
						<Tooltip content={$i18n.t('Select directory')} placement="top">
							<button
								type="button"
								class="rounded p-0.5 opacity-40 transition hover:bg-gray-200 hover:opacity-100 dark:hover:bg-gray-700"
								on:click|stopPropagation={() => selectDirectory(item)}
							>
								<Plus className="size-3" />
							</button>
						</Tooltip>
						<ChevronRight className="size-3 opacity-30" />
					</div>
				</div>
			{:else}
				<button
					class="flex h-[1.6875rem] w-full items-center gap-1.5 rounded-xl px-2 text-left text-[13px] text-black hover:bg-gray-50/40 dark:text-gray-100 dark:hover:bg-gray-800/40 {idx ===
					selectedIdx
						? 'bg-gray-50/40 dark:bg-gray-800/40 dark:text-gray-100 selected-command-option-button'
						: ''}"
					type="button"
					data-selected={idx === selectedIdx}
					on:click={() => selectBrowsingFile(item)}
					on:mousemove={() => {
						selectedIdx = idx;
					}}
				>
					<DocumentPage className="size-3.5" />
					<Tooltip content={decodeString(item.name)} placement="top-start">
						<div class="min-w-0 flex-1 truncate">{decodeString(item.name)}</div>
					</Tooltip>
				</button>
			{/if}
		{/each}
	{/if}
{:else if filteredItems.length > 0 || query.startsWith('http')}
	<!-- Top-level view -->
	{#each filteredItems as item, idx}
		{#if idx === 0 || item?.type !== items[idx - 1]?.type}
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

		{#if !['youtube', 'web'].includes(item.type)}
			{#if item.type === 'collection'}
				<div
					class="flex h-[1.6875rem] w-full items-center justify-between rounded-xl px-2 text-left text-[13px] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {idx ===
					selectedIdx
						? 'bg-gray-50/40 dark:bg-gray-800/40 dark:text-gray-100 selected-command-option-button'
						: ''}"
				>
					<button
						type="button"
						class="flex min-w-0 flex-1 items-center gap-1.5 text-left text-black dark:text-gray-100"
						data-selected={idx === selectedIdx}
						on:click={() => browseIntoCollection(item)}
						on:mousemove={() => {
							selectedIdx = idx;
						}}
					>
						<Tooltip
							content={item?.legacy ? $i18n.t('Legacy') : $i18n.t('Collection')}
							placement="top"
						>
							<Database className="size-3.5" />
						</Tooltip>

						<Tooltip content={`${decodeString(item?.name)}`} placement="top-start">
							<div class="min-w-0 flex-1 truncate">
								{decodeString(item?.name)}
							</div>
						</Tooltip>
					</button>

					<div class="ml-1 flex items-center gap-0.5">
						<Tooltip content={$i18n.t('Select collection')} placement="top">
							<button
								type="button"
								class="rounded p-0.5 opacity-40 transition hover:bg-gray-200 hover:opacity-100 dark:hover:bg-gray-700"
								on:click|stopPropagation={() => {
									onSelect({
										type: 'knowledge',
										data: { ...item, type: 'collection' }
									});
								}}
							>
								<Plus className="size-3" />
							</button>
						</Tooltip>
						<ChevronRight className="size-3 opacity-30" />
					</div>
				</div>
			{:else}
				<button
					class="flex h-[1.6875rem] w-full items-center justify-between rounded-xl px-2 text-left text-[13px] hover:bg-gray-50/40 dark:hover:bg-gray-800/40 {idx ===
					selectedIdx
						? 'bg-gray-50/40 dark:bg-gray-800/40 dark:text-gray-100 selected-command-option-button'
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
					<div class="flex min-w-0 items-center gap-1.5 text-black dark:text-gray-100">
						<Tooltip
							content={item?.legacy
								? $i18n.t('Legacy')
								: item?.type === 'file'
									? `${item?.collection?.name} > ${$i18n.t('File')}`
									: ''}
							placement="top"
						>
							{#if item?.type === 'folder'}
								<Folder className="size-3.5" />
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
			{/if}
		{/if}
	{/each}

	{#if isYoutubeUrl(query)}
		<button
			class="flex h-[1.6875rem] w-full items-center rounded-xl bg-gray-50/40 px-2 text-left text-[13px] dark:bg-gray-800/40 dark:text-gray-100 selected-command-option-button"
			type="button"
			data-selected={selectedIdx === filteredItems.findIndex((i) => i.type === 'youtube')}
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
			<div class="flex min-w-0 items-center gap-1.5 text-black dark:text-gray-100">
				<Tooltip content={$i18n.t('YouTube')} placement="top">
					<Youtube className="size-3.5" />
				</Tooltip>

				<div class="min-w-0 flex-1 truncate">
					{query}
				</div>
			</div>
		</button>
	{:else if query.startsWith('http')}
		<button
			class="flex h-[1.6875rem] w-full items-center rounded-xl bg-gray-50/40 px-2 text-left text-[13px] dark:bg-gray-800/40 dark:text-gray-100 selected-command-option-button"
			type="button"
			data-selected={selectedIdx === filteredItems.findIndex((i) => i.type === 'web')}
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
			<div class="flex min-w-0 items-center gap-1.5 text-black dark:text-gray-100">
				<Tooltip content={$i18n.t('Web')} placement="top">
					<GlobeAlt className="size-3.5" />
				</Tooltip>

				<div class="min-w-0 flex-1 truncate">
					{query}
				</div>
			</div>
		</button>
	{/if}
{/if}
