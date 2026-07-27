<script lang="ts">
	import { getContext } from 'svelte';

	import { folders } from '$lib/stores';
	import { decodeString } from '$lib/utils';

	import Select from '$lib/components/common/Select.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Folder from '$lib/components/icons/Folder.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	const i18n = getContext('i18n');

	export let folder_id = '';
	export let side: 'top' | 'bottom' = 'top';
	export let align: 'start' | 'end' = 'start';
	export let onChange: () => void = () => {};

	let folderSearch = '';

	const folderName = (folder: any) => decodeString(folder?.name ?? $i18n.t('Folder'));

	const folderPath = (folder: any) => {
		const names: string[] = [];
		const seen = new Set<string>();
		let current = folder;

		while (current?.parent_id && !seen.has(current.parent_id)) {
			seen.add(current.parent_id);
			const parent = folderById.get(current.parent_id);
			if (!parent) break;
			names.unshift(folderName(parent));
			current = parent;
		}

		return names.join(' / ');
	};

	$: folderOptions = [...((($folders ?? []) as any[]) ?? [])]
		.filter((folder) => folder?.id && !folder?.shared)
		.sort((a, b) => folderName(a).localeCompare(folderName(b)));
	$: folderById = new Map(folderOptions.map((folder) => [folder.id, folder]));
	$: selectedFolder = folderOptions.find((folder) => folder.id === folder_id);
	$: folderLabel = selectedFolder ? folderName(selectedFolder) : $i18n.t('Choose folder');
	$: normalizedSearch = folderSearch.trim().toLowerCase();
	$: filteredFolderOptions = normalizedSearch
		? folderOptions.filter((folder) =>
				`${folderName(folder)} ${folderPath(folder)}`.toLowerCase().includes(normalizedSearch)
			)
		: folderOptions;
</script>

<Select
	bind:value={folder_id}
	items={folderOptions.map((folder) => ({ value: folder.id, label: folderName(folder) }))}
	placeholder={$i18n.t('Choose folder')}
	{align}
	{side}
	triggerClass="relative h-8 max-w-[11rem] flex items-center gap-1.5 px-2.5 py-1.5 bg-transparent rounded-2xl text-xs font-normal text-gray-600 transition hover:text-gray-900 dark:text-gray-400 dark:hover:text-gray-100"
	contentClass="w-72 shadow-lg"
	maxHeight="18rem"
	onChange={() => onChange()}
	onClose={() => {
		folderSearch = '';
	}}
>
	<svelte:fragment slot="trigger">
		<Folder className="size-3.5 shrink-0" />
		<div class="inline-flex h-input min-w-0 flex-1 truncate bg-transparent outline-hidden">
			{folderLabel}
		</div>

		{#if folder_id}
			<button
				class="outline-none"
				type="button"
				on:click|stopPropagation={() => {
					folder_id = '';
					folderSearch = '';
					onChange();
				}}
				aria-label={$i18n.t('Clear')}
			>
				<XMark className="size-3.5" />
			</button>
		{:else}
			<ChevronDown className="size-2.5 shrink-0" strokeWidth="2.5" />
		{/if}
	</svelte:fragment>

	<svelte:fragment let:selectItem>
		<div class="flex items-center gap-1.5 px-2 py-1">
			<Search className="size-3.5 shrink-0" strokeWidth="2.5" />
			<input
				bind:value={folderSearch}
				class="w-full bg-transparent text-[13px] outline-hidden"
				placeholder={$i18n.t('Search folders')}
				autocomplete="off"
				on:click|stopPropagation
			/>
		</div>

		{#if folderOptions.length > 0}
			<hr class="mx-1 my-0.5 border-gray-50/30 dark:border-gray-800/30" />
			<div class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400">
				{$i18n.t('Folders')}
			</div>
		{/if}

		{#each filteredFolderOptions as folder (folder.id)}
			{@const path = folderPath(folder)}
			<button
				type="button"
				class="flex h-[1.6875rem] w-full cursor-pointer items-center justify-between gap-2 rounded-xl bg-transparent px-2 text-[13px] hover:bg-gray-50/40 hover:text-gray-900 dark:hover:bg-gray-800/40 dark:hover:text-gray-100 {folder_id ===
				folder.id
					? 'text-gray-900 dark:text-gray-100'
					: 'text-gray-700 dark:text-gray-300'}"
				title={path ? `${path} / ${folderName(folder)}` : folderName(folder)}
				on:click={() => {
					selectItem({
						value: folder_id === folder.id ? '' : folder.id,
						label: folder_id === folder.id ? $i18n.t('Choose folder') : folderName(folder)
					});
					folderSearch = '';
				}}
			>
				<div class="flex min-w-0 items-center gap-1.5">
					<Folder className="size-3.5 shrink-0" />
					<span class="min-w-0 truncate">{folderName(folder)}</span>
					{#if path}
						<span class="min-w-0 truncate text-[11px] text-gray-400 dark:text-gray-500">
							{path}
						</span>
					{/if}
				</div>
				{#if folder_id === folder.id}
					<Check className="size-3.5 shrink-0" strokeWidth="2" />
				{/if}
			</button>
		{:else}
			<div class="px-2 py-1 text-[11px] text-gray-500 dark:text-gray-400">
				{folderOptions.length > 0 ? $i18n.t('No results found') : $i18n.t('No folders')}
			</div>
		{/each}
	</svelte:fragment>
</Select>
