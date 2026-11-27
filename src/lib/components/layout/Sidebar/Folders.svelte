<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import { toast } from 'svelte-sonner';

	import { settings } from '$lib/stores';
	import { updateFolderDetails } from '$lib/stores/folderStates';
	import { updateFolderParentIdById } from '$lib/apis/folders';
	import { updateUserSettings } from '$lib/apis/users';
	import { sortFolders } from '$lib/utils/folders';

	import RecursiveFolder from './RecursiveFolder.svelte';

	export let folderRegistry = {};

	export let folders: Record<string, any> = {};
	export let shiftKey = false;

	export let onDelete = () => {};
	export let onFolderUnreadCounts = () => {};

	let rootOrder: string[] = [];

	$: roots = Object.values(folders).filter((f) => {
		if (!f.name) return false;
		// Root folder: no parent, or shared folder whose parent isn't in our folders
		if (f.shared) {
			return !f.parent_id || !folders[f.parent_id];
		}
		return f.parent_id === null;
	});
	$: rootOrder = sortFolders(roots, $settings?.folderOrder?.root).map((f) => f.id);

	// Filters only hide folders; the saved order keeps them all
	$: owner = $settings?.folderOwner ?? 'all';
	// A machine that no longer has folders here filters nothing
	$: machine =
		$settings?.folderMachine === 'none' ||
		roots.some((f) => f.machine_id && f.machine_id === $settings?.folderMachine)
			? $settings?.folderMachine
			: 'all';
	$: rootList = sortFolders(roots, $settings?.folderOrder?.root, $settings?.folderSort)
		.filter(
			(f) =>
				(owner === 'all' || (owner === 'shared') === !!f.shared) &&
				(machine === 'all' || (machine === 'none' ? !f.machine_id : f.machine_id === machine))
		)
		.map((f) => f.id);

	const onReorder = async (id: string, targetId: string, position: 'before' | 'after') => {
		// A shared folder only moves among top-level folders; the owner's tree stays as it is
		const parentId = folders[targetId].shared ? null : folders[targetId].parent_id;

		if (!folders[id].shared && folders[id].parent_id !== parentId) {
			const res = await updateFolderParentIdById(localStorage.token, id, parentId).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);
			if (!res) return;

			updateFolderDetails(id, res);
			dispatch('update');
		}

		const key = parentId ?? 'root';
		const order = (
			parentId === null
				? rootOrder
				: sortFolders(
						Object.values(folders).filter((f) => f.parent_id === parentId && !f.shared),
						$settings?.folderOrder?.[key]
					).map((f) => f.id)
		).filter((f) => f !== id);
		order.splice(order.indexOf(targetId) + (position === 'after' ? 1 : 0), 0, id);

		const folderOrder = { ...$settings?.folderOrder, [key]: order };
		settings.set({ ...$settings, folderOrder });
		await updateUserSettings(localStorage.token, { ui: { folderOrder } }).catch((error) => {
			toast.error(`${error}`);
		});
	};

	const onItemMove = (e) => {
		if (e.originFolderId) {
			folderRegistry[e.originFolderId]?.setFolderItems();
		}
	};
</script>

{#if rootList.length > 0}
	<div role="list">
		{#each rootList as folderId (folderId)}
			<RecursiveFolder
				className=""
				bind:folderRegistry
				{folders}
				{folderId}
				{shiftKey}
				{onDelete}
				{onItemMove}
				{onReorder}
				{onFolderUnreadCounts}
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
	</div>
{/if}
