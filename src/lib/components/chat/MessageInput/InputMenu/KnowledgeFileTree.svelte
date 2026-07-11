<script lang="ts">
	import { tick, getContext } from 'svelte';

	import { decodeString } from '$lib/utils';
	import { searchKnowledgeFilesById } from '$lib/apis/knowledge';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import DocumentPage from '$lib/components/icons/DocumentPage.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Loader from '$lib/components/common/Loader.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	const i18n = getContext('i18n');

	export let knowledgeId: string;
	// null = root level of the knowledge base. A directory id scopes to that folder.
	export let directoryId: string | null = null;
	export let depth = 0;
	export let onSelect = (e) => {};

	let page = 1;
	let files = null;
	let total = null;
	let directories = [];

	let itemsLoading = false;
	let allItemsLoaded = false;

	// Which child folders are expanded (inline, accordion-style like the KB rows).
	let expandedDirectoryIds = new Set();

	const toggleDirectory = (id: string) => {
		if (expandedDirectoryIds.has(id)) {
			expandedDirectoryIds.delete(id);
		} else {
			expandedDirectoryIds.add(id);
		}
		// Reassign so Svelte picks up the change.
		expandedDirectoryIds = new Set(expandedDirectoryIds);
	};

	const getItemsPage = async () => {
		itemsLoading = true;

		const res = await searchKnowledgeFilesById(
			localStorage.token,
			knowledgeId,
			null,
			null,
			null,
			null,
			page,
			// null (root) -> '' so the backend scopes to the root level; otherwise the folder id.
			directoryId ?? ''
		).catch(() => {
			return null;
		});

		if (res) {
			total = res.total;
			// Directories are not paginated; the API returns the full set for this level each call.
			directories = res.directories ?? [];

			const pageItems = res.items ?? [];
			allItemsLoaded = pageItems.length === 0;

			if (files) {
				const existingIds = new Set(files.map((item) => item.id));
				const newItems = pageItems.filter((item) => !existingIds.has(item.id));
				files = [...files, ...newItems];
			} else {
				files = pageItems;
			}
		}

		itemsLoading = false;
		return res;
	};

	const loadMoreItems = async () => {
		if (allItemsLoaded) return;
		page += 1;
		await getItemsPage();
	};

	const init = async () => {
		page = 1;
		files = null;
		total = null;
		directories = [];
		allItemsLoaded = false;
		itemsLoading = false;
		expandedDirectoryIds = new Set();
		await tick();
		await getItemsPage();
	};

	// Load (and reload) whenever the target level changes.
	$: knowledgeId, directoryId, init();
</script>

{#if files === null && total === null}
	<div class="py-1 flex justify-center">
		<Spinner className="size-3" />
	</div>
{:else if directories.length === 0 && (files?.length ?? 0) === 0}
	<div class="text-xs text-gray-500 dark:text-gray-400 italic py-0.5 px-2">
		{depth === 0
			? $i18n.t('No files in this knowledge base.')
			: $i18n.t('No files in this folder.')}
	</div>
{:else}
	<!-- Folders first, each expandable inline to reveal its own files/sub-folders. -->
	{#each directories as directory (directory.id)}
		<button
			class="px-2.5 py-1 rounded-xl w-full text-left flex justify-between items-center text-sm hover:bg-gray-50 hover:dark:bg-gray-800 hover:dark:text-gray-100"
			type="button"
			on:click={() => {
				toggleDirectory(directory.id);
			}}
		>
			<div class="flex items-center gap-1.5 min-w-0">
				<Tooltip content={$i18n.t('Folder')} placement="top">
					<Folder className="size-4" />
				</Tooltip>

				<Tooltip content={decodeString(directory?.name)} placement="top-start">
					<div class="line-clamp-1 flex-1 text-sm">
						{decodeString(directory?.name)}
					</div>
				</Tooltip>
			</div>

			<Tooltip content={$i18n.t('Show Files')} placement="top">
				<span class="ml-2 opacity-50">
					{#if expandedDirectoryIds.has(directory.id)}
						<ChevronDown className="size-3" />
					{:else}
						<ChevronRight className="size-3" />
					{/if}
				</span>
			</Tooltip>
		</button>

		{#if expandedDirectoryIds.has(directory.id)}
			<div class="pl-3 flex flex-col gap-0.5">
				<svelte:self
					{knowledgeId}
					directoryId={directory.id}
					depth={depth + 1}
					{onSelect}
				/>
			</div>
		{/if}
	{/each}

	<!-- Files that live directly at this level. -->
	{#each files as file (file.id)}
		<button
			class="px-2.5 py-1 rounded-xl w-full text-left flex justify-between items-center text-sm hover:bg-gray-50 hover:dark:bg-gray-800 hover:dark:text-gray-100"
			type="button"
			on:click={() => {
				onSelect({
					type: 'file',
					name: file?.meta?.name,
					...file
				});
			}}
		>
			<div class="flex items-center gap-1.5 min-w-0">
				<Tooltip content={$i18n.t('File')} placement="top">
					<DocumentPage className="size-4" />
				</Tooltip>

				<Tooltip content={decodeString(file?.meta?.name)} placement="top-start">
					<div class="line-clamp-1 flex-1 text-sm">
						{decodeString(file?.meta?.name)}
					</div>
				</Tooltip>
			</div>
		</button>
	{/each}

	{#if !allItemsLoaded && !itemsLoading}
		<Loader
			on:visible={async (e) => {
				if (!itemsLoading) {
					await loadMoreItems();
				}
			}}
		>
			<div class="w-full flex justify-center py-4 text-xs animate-pulse items-center gap-2">
				<Spinner className="size-3" />
				<div>{$i18n.t('Loading...')}</div>
			</div>
		</Loader>
	{/if}
{/if}
