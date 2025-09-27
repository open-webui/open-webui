<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import RecursiveFolder from './RecursiveFolder.svelte';

	export let folderRegistry = {};

	export let folders = {};
	export let shiftKey = false;

	export let onDelete = (folderId) => {};

	let folderList = [];
	// Get the list of folders that have no parent, sorted by name alphabetically
	$: folderList = Object.keys(folders)
		.filter((key) => folders[key].parent_id === null)
		.sort((a, b) =>
			folders[a].name.localeCompare(folders[b].name, undefined, {
				numeric: true,
				sensitivity: 'base'
			})
		);

	const onItemMove = (e) => {
		if (e.originFolderId) {
			folderRegistry[e.originFolderId]?.setFolderItems();
		}
	};
</script>

{#each folderList as folderId (folderId)}
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
