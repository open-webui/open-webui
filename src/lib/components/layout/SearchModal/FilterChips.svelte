<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { folders as foldersStore, tags as tagsStore } from '$lib/stores';
	import ArchiveBox from '$lib/components/icons/ArchiveBox.svelte';
	import Tag from '$lib/components/icons/Tag.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Calendar from '$lib/components/icons/Calendar.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import type { ChatSearchFacets } from '$lib/apis/chats';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

	export let archived: boolean | null = null;
	export let pinned: boolean | null = null;
	export let folderIds: string[] = [];
	export let tagIds: string[] = [];
	export let modelIds: string[] = [];
	export let datePreset: 'all' | 'today' | '7d' | '30d' | 'year' = 'all';
	export let sort: 'relevance' | 'recent' = 'relevance';
	export let facets: ChatSearchFacets | null = null;

	let openMenu: 'folder' | 'tag' | 'model' | 'date' | 'sort' | null = null;

	const closeMenu = () => (openMenu = null);

	const change = () => {
		dispatch('change');
	};

	const toggleArchived = () => {
		// Tri-state: null (include both) -> false (hide archived) -> true (only archived) -> null
		if (archived === null) archived = false;
		else if (archived === false) archived = true;
		else archived = null;
		change();
	};

	const togglePinned = () => {
		if (pinned === null) pinned = true;
		else if (pinned === true) pinned = false;
		else pinned = null;
		change();
	};

	const togglePick = (list: string[], id: string): string[] => {
		const idx = list.indexOf(id);
		if (idx >= 0) return list.filter((x) => x !== id);
		return [...list, id];
	};

	const datePresets: { id: typeof datePreset; label: string }[] = [
		{ id: 'all', label: 'All time' },
		{ id: 'today', label: 'Today' },
		{ id: '7d', label: 'Last 7 days' },
		{ id: '30d', label: 'Last 30 days' },
		{ id: 'year', label: 'Last year' }
	];

	$: dateLabel = datePresets.find((d) => d.id === datePreset)?.label ?? 'All time';
	$: archivedLabel =
		archived === null ? 'Archived: any' : archived ? 'Only archived' : 'Hide archived';
	$: pinnedLabel = pinned === null ? 'Pinned: any' : pinned ? 'Only pinned' : 'Hide pinned';

	$: folderFacets = (facets?.folders ?? []).reduce(
		(acc, f) => {
			acc[f.id] = f.count;
			return acc;
		},
		{} as Record<string, number>
	);
	$: tagFacets = (facets?.tags ?? []).reduce(
		(acc, t) => {
			acc[t.id] = t.count;
			return acc;
		},
		{} as Record<string, number>
	);
	$: modelFacets = facets?.models ?? [];

	type FolderLike = { id: string; name: string };
	type TagLike = { id: string; name: string };
	$: folderList = ($foldersStore ?? []) as unknown as FolderLike[];
	$: tagList = ($tagsStore ?? []) as unknown as TagLike[];

	const clickOutside = (node: HTMLElement) => {
		const handler = (e: MouseEvent) => {
			if (!node.contains(e.target as Node)) {
				openMenu = null;
			}
		};
		document.addEventListener('mousedown', handler);
		return {
			destroy() {
				document.removeEventListener('mousedown', handler);
			}
		};
	};
</script>

<div class="flex flex-wrap items-center gap-1.5 px-4 pb-2 text-xs">
	<!-- Archived -->
	<button
		class="flex items-center gap-1 px-2 py-1 rounded-full border transition {archived === null
			? 'border-gray-200 dark:border-gray-700 text-gray-500'
			: 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-850 text-gray-900 dark:text-gray-100'}"
		on:click={toggleArchived}
		type="button"
	>
		<ArchiveBox className="size-3" strokeWidth="2" />
		<span>{$i18n.t(archivedLabel)}</span>
	</button>

	<!-- Pinned -->
	<button
		class="flex items-center gap-1 px-2 py-1 rounded-full border transition {pinned === null
			? 'border-gray-200 dark:border-gray-700 text-gray-500'
			: 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-850 text-gray-900 dark:text-gray-100'}"
		on:click={togglePinned}
		type="button"
	>
		<span class="text-xs">📌</span>
		<span>{$i18n.t(pinnedLabel)}</span>
	</button>

	<!-- Folder -->
	<div class="relative" use:clickOutside>
		<button
			class="flex items-center gap-1 px-2 py-1 rounded-full border transition {folderIds.length
				? 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-850 text-gray-900 dark:text-gray-100'
				: 'border-gray-200 dark:border-gray-700 text-gray-500'}"
			on:click={() => (openMenu = openMenu === 'folder' ? null : 'folder')}
			type="button"
		>
			<Folder className="size-3" />
			<span
				>{$i18n.t('Folder')}{folderIds.length ? ` (${folderIds.length})` : ''}</span
			>
			<ChevronDown className="size-3" />
		</button>
		{#if openMenu === 'folder'}
			<div
				class="absolute z-30 mt-1 min-w-[200px] max-h-72 overflow-y-auto rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg p-1 text-sm"
			>
				{#if folderList.length === 0}
					<div class="px-3 py-2 text-gray-500">{$i18n.t('No folders')}</div>
				{:else}
					{#each folderList as folder (folder.id)}
						<button
							class="w-full text-left px-3 py-1.5 rounded-lg flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-850"
							on:click={() => {
								folderIds = togglePick(folderIds, folder.id);
								change();
							}}
							type="button"
						>
							<span class="flex items-center gap-2">
								<span
									class="inline-block w-3 h-3 rounded-sm border {folderIds.includes(
										folder.id
									)
										? 'bg-gray-900 dark:bg-white border-gray-900 dark:border-white'
										: 'border-gray-400'}"
								></span>
								<span class="line-clamp-1">{folder.name}</span>
							</span>
							{#if folderFacets[folder.id] != null}
								<span class="text-xs text-gray-500">{folderFacets[folder.id]}</span>
							{/if}
						</button>
					{/each}
				{/if}
			</div>
		{/if}
	</div>

	<!-- Tag -->
	<div class="relative" use:clickOutside>
		<button
			class="flex items-center gap-1 px-2 py-1 rounded-full border transition {tagIds.length
				? 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-850 text-gray-900 dark:text-gray-100'
				: 'border-gray-200 dark:border-gray-700 text-gray-500'}"
			on:click={() => (openMenu = openMenu === 'tag' ? null : 'tag')}
			type="button"
		>
			<Tag className="size-3" />
			<span>{$i18n.t('Tag')}{tagIds.length ? ` (${tagIds.length})` : ''}</span>
			<ChevronDown className="size-3" />
		</button>
		{#if openMenu === 'tag'}
			<div
				class="absolute z-30 mt-1 min-w-[200px] max-h-72 overflow-y-auto rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg p-1 text-sm"
			>
				{#if tagList.length === 0}
					<div class="px-3 py-2 text-gray-500">{$i18n.t('No tags')}</div>
				{:else}
					{#each tagList as tag (tag.id)}
						<button
							class="w-full text-left px-3 py-1.5 rounded-lg flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-850"
							on:click={() => {
								tagIds = togglePick(tagIds, tag.id);
								change();
							}}
							type="button"
						>
							<span class="flex items-center gap-2">
								<span
									class="inline-block w-3 h-3 rounded-sm border {tagIds.includes(tag.id)
										? 'bg-gray-900 dark:bg-white border-gray-900 dark:border-white'
										: 'border-gray-400'}"
								></span>
								<span class="line-clamp-1">{tag.name}</span>
							</span>
							{#if tagFacets[tag.id] != null}
								<span class="text-xs text-gray-500">{tagFacets[tag.id]}</span>
							{/if}
						</button>
					{/each}
				{/if}
			</div>
		{/if}
	</div>

	<!-- Date -->
	<div class="relative" use:clickOutside>
		<button
			class="flex items-center gap-1 px-2 py-1 rounded-full border transition {datePreset !== 'all'
				? 'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-850 text-gray-900 dark:text-gray-100'
				: 'border-gray-200 dark:border-gray-700 text-gray-500'}"
			on:click={() => (openMenu = openMenu === 'date' ? null : 'date')}
			type="button"
		>
			<Calendar className="size-3" />
			<span>{$i18n.t(dateLabel)}</span>
			<ChevronDown className="size-3" />
		</button>
		{#if openMenu === 'date'}
			<div
				class="absolute z-30 mt-1 min-w-[160px] rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg p-1 text-sm"
			>
				{#each datePresets as preset}
					<button
						class="w-full text-left px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-850 {datePreset ===
						preset.id
							? 'font-medium'
							: ''}"
						on:click={() => {
							datePreset = preset.id;
							openMenu = null;
							change();
						}}
						type="button"
					>
						{$i18n.t(preset.label)}
					</button>
				{/each}
			</div>
		{/if}
	</div>

	<!-- Sort -->
	<div class="relative ml-auto" use:clickOutside>
		<button
			class="flex items-center gap-1 px-2 py-1 rounded-full border border-gray-200 dark:border-gray-700 text-gray-500 transition"
			on:click={() => (openMenu = openMenu === 'sort' ? null : 'sort')}
			type="button"
		>
			<span>{$i18n.t('Sort')}: {$i18n.t(sort === 'relevance' ? 'Relevance' : 'Recent')}</span>
			<ChevronDown className="size-3" />
		</button>
		{#if openMenu === 'sort'}
			<div
				class="absolute right-0 z-30 mt-1 min-w-[140px] rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-lg p-1 text-sm"
			>
				<button
					class="w-full text-left px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-850 {sort ===
					'relevance'
						? 'font-medium'
						: ''}"
					on:click={() => {
						sort = 'relevance';
						openMenu = null;
						change();
					}}
					type="button">{$i18n.t('Relevance')}</button
				>
				<button
					class="w-full text-left px-3 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-850 {sort ===
					'recent'
						? 'font-medium'
						: ''}"
					on:click={() => {
						sort = 'recent';
						openMenu = null;
						change();
					}}
					type="button">{$i18n.t('Recent')}</button
				>
			</div>
		{/if}
	</div>

	{#if archived !== null || pinned !== null || folderIds.length || tagIds.length || datePreset !== 'all' || sort !== 'relevance'}
		<button
			class="flex items-center gap-1 px-2 py-1 rounded-full border border-gray-200 dark:border-gray-700 text-gray-500 hover:text-gray-900 dark:hover:text-white transition"
			on:click={() => {
				archived = null;
				pinned = null;
				folderIds = [];
				tagIds = [];
				datePreset = 'all';
				sort = 'relevance';
				change();
			}}
			type="button"
		>
			<XMark className="size-3" strokeWidth="2" />
			<span>{$i18n.t('Clear')}</span>
		</button>
	{/if}
</div>
