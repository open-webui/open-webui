<script lang="ts">
	import { getContext, createEventDispatcher } from 'svelte';
	const i18n = getContext('i18n');
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

	let ownedList: string[] = [];
	let sharedList: string[] = [];

	$: {
		const rootFolders = Object.values(folders).filter((f) => {
			if (!f.name) return false;
			// Root folder: no parent, or shared folder whose parent isn't in our folders
			if (f.shared) {
				return !f.parent_id || !folders[f.parent_id];
			}
			return f.parent_id === null;
		});
		ownedList = sortFolders(
			rootFolders.filter((f) => !f.shared),
			$settings?.folderOrder?.root
		).map((f) => f.id);
		sharedList = sortFolders(rootFolders.filter((f) => f.shared)).map((f) => f.id);
	}

	const onReorder = async (id: string, targetId: string, position: 'before' | 'after') => {
		const parentId = folders[targetId].parent_id;

		if (folders[id].parent_id !== parentId) {
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
		const order = sortFolders(
			Object.values(folders).filter((f) => f.parent_id === parentId && !f.shared && f.id !== id),
			$settings?.folderOrder?.[key]
		).map((f) => f.id);
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

{#if ownedList.length > 0}
	<div role="list">
		{#each ownedList as folderId (folderId)}
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

{#if sharedList.length > 0}
	<div class="w-full pl-2.5 text-[0.6875rem] text-base-400 dark:text-base-600 pt-2 pb-0.5">
		{$i18n.t('Shared')}
	</div>
	<div role="list">
		{#each sharedList as folderId (folderId)}
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
