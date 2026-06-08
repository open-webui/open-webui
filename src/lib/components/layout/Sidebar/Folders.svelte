<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import RecursiveFolder from './RecursiveFolder.svelte';
	import { chatId, selectedFolder } from '$lib/stores';

	type FolderItem = {
		id: string;
		name: string;
		parent_id?: string | null;
		workspace_id?: string | null;
		childrenIds?: string[];
	};

	export let folderRegistry: Record<string, { setFolderItems?: () => void }> = {};

	export let folders: Record<string, FolderItem> = {};
	export let shiftKey = false;
	export let folderApis: Record<string, unknown> = {};
	export let selectFolderPath = '/';
	export let workspaceId: string | null = null;
	export let folderReadOnly = false;

	export let onDelete = (folderId: string) => {};

	let folderList: string[] = [];
	// Get the list of folders that have no parent, sorted by name alphabetically
	$: folderList = Object.keys(folders)
		.filter((key) => folders[key].parent_id === null)
		.sort((a, b) =>
			folders[a].name.localeCompare(folders[b].name, undefined, {
				numeric: true,
				sensitivity: 'base'
			})
		);

	const onItemMove = (e: { originFolderId?: string }) => {
		if (e.originFolderId) {
			folderRegistry[e.originFolderId]?.setFolderItems?.();
		}
	};

	const loadFolderItems = () => {
		for (const folderId of Object.keys(folders)) {
			folderRegistry[folderId]?.setFolderItems?.();
		}
	};

	$: if (folders || ($selectedFolder && $chatId)) {
		loadFolderItems();
	}
</script>

{#each folderList as folderId (folderId)}
	<RecursiveFolder
		className=""
		bind:folderRegistry
		{folders}
		{folderId}
		{shiftKey}
		{folderApis}
		{selectFolderPath}
		{workspaceId}
		{folderReadOnly}
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
