<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	import RecursiveFolder from './RecursiveFolder.svelte';
	import { chatId, selectedFolder } from '$lib/stores';

	export let folderRegistry = {};

	export let folders = {};
	export let shiftKey = false;

	export let onDelete = (folderId) => {};

	let ownedList = [];
	let sharedList = [];

	$: {
		const rootKeys = Object.keys(folders)
			.filter((key) => {
				const f = folders[key];
				if (!f.name) return false;
				// Root folder: no parent, or shared folder whose parent isn't in our folders
				if (f.shared) {
					return !f.parent_id || !folders[f.parent_id];
				}
				return f.parent_id === null;
			})
			.sort((a, b) =>
				(folders[a].name ?? '').localeCompare(folders[b].name ?? '', undefined, {
					numeric: true,
					sensitivity: 'base'
				})
			);
		ownedList = rootKeys.filter((key) => !folders[key].shared);
		sharedList = rootKeys.filter((key) => folders[key].shared);
	}

	const onItemMove = (e) => {
		if (e.originFolderId) {
			folderRegistry[e.originFolderId]?.setFolderItems();
		}
	};

	const loadFolderItems = () => {
		for (const folderId of Object.keys(folders)) {
			folderRegistry[folderId]?.setFolderItems();
		}
	};

	$: if (folders || ($selectedFolder && $chatId)) {
		loadFolderItems();
	}
</script>

{#each ownedList as folderId (folderId)}
	<RecursiveFolder
		className=""
		bind:folderRegistry
		{folders}
		{folderId}
		{shiftKey}
		{onDelete}
		{onItemMove}
		on:import={(e) => {
			dispatch('import', e.detail);
		}}
		on:update={(e) => {
			dispatch('update', e.detail);
		}}
		on:change={(e) => {
			dispatch('change', e.detail);
		}}
	/>
{/each}

{#if sharedList.length > 0}
	<div class="w-full pl-2.5 text-[11px] text-gray-400 dark:text-gray-600 pt-2 pb-0.5">
		{$i18n.t('Shared')}
	</div>
	{#each sharedList as folderId (folderId)}
		<RecursiveFolder
			className=""
			bind:folderRegistry
			{folders}
			{folderId}
			{shiftKey}
			{onDelete}
			{onItemMove}
			on:import={(e) => {
				dispatch('import', e.detail);
			}}
			on:update={(e) => {
				dispatch('update', e.detail);
			}}
			on:change={(e) => {
				dispatch('change', e.detail);
			}}
		/>
	{/each}
{/if}
