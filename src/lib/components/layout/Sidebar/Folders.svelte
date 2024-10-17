<script lang="ts">
	import RecursiveFolder from './RecursiveFolder.svelte';
	export let folders = {};

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
</script>

{#each folderList as folderId (folderId)}
	<RecursiveFolder className="px-2" {folders} {folderId} />
{/each}
