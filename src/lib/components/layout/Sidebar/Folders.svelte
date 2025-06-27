<script lang="ts">
	import { createEventDispatcher, getContext } from 'svelte';
	import { toast } from 'svelte-sonner';
	import RecursiveFolder from './RecursiveFolder.svelte';
	import EditFolderModal from './Folders/EditFolderModal.svelte';
	import { updateFolderById } from '$lib/apis/folders';

	const dispatch = createEventDispatcher();
	const i18n = getContext('i18n');

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

	let showEditFolderModal = false;
	let currentEditingFolder = null;

	const handleEditFolderEvent = (event) => {
		const folderToEdit = event.detail;
		if (folderToEdit && folderToEdit.id) {
			currentEditingFolder = { ...folderToEdit };
			showEditFolderModal = true;
		} else {
			console.error('EditFolder event did not provide valid folder data:', event.detail);
			toast.error($i18n.t('Failed to open edit dialog: Invalid folder data.'));
		}
	};

	const handleSaveFolderEdit = async (event) => {
		const { id, name, system_prompt } = event.detail;

		try {
			const updatedFolder = await updateFolderById(localStorage.token, id, {
				name,
				system_prompt
			});

			if (updatedFolder && updatedFolder.id) {
				toast.success($i18n.t('Folder updated successfully'));
				showEditFolderModal = false;
				currentEditingFolder = null;
				dispatch('update', updatedFolder);
			} else {
				const errorDetail = updatedFolder?.detail || $i18n.t('Unknown error');
				toast.error(`${$i18n.t('Failed to update folder')}: ${errorDetail}`);
			}
		} catch (error) {
			console.error('Failed to update folder:', error);
			const errorDetail = error?.detail || error?.message || $i18n.t('Unknown error');
			toast.error(`${$i18n.t('Failed to update folder')}: ${errorDetail}`);
		}
	};

	const handleCreateChatInFolder = (event) => {
	    dispatch('createChatInFolder', event.detail);
	};
</script>

{#if showEditFolderModal && currentEditingFolder}
	<EditFolderModal
		bind:show={showEditFolderModal}
		folder={currentEditingFolder}
		on:saveFolder={handleSaveFolderEdit}
		on:close={() => {
			showEditFolderModal = false;
			currentEditingFolder = null;
		}}
	/>
{/if}

{#each folderList as folderId (folderId)}
	<RecursiveFolder
		className=""
		{folders}
		{folderId}
		on:import={(e) => {
			dispatch('import', e.detail);
		}}
		on:update={(e) => {
			dispatch('update', e.detail);
		}}
		on:change={(e) => {
			dispatch('change', e.detail);
		}}
		on:editFolder={handleEditFolderEvent}
		on:createChatInFolder={handleCreateChatInFolder}
	/>
{/each}
