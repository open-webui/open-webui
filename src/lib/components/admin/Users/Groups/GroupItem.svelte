<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');

	import { deleteGroupById, updateGroupById } from '$lib/apis/groups';

	import EditGroupModal from './EditGroupModal.svelte';

	export let group = {
		id: '',
		name: 'Admins',
		description: '',
		permissions: {},
		user_ids: [1, 2, 3],
		member_count: 0
	};
	export let defaultPermissions = {};

	export let setGroups = () => {};

	let showEdit = false;
	$: hasCustomPermissions = Object.keys(group?.permissions ?? {}).length > 0;

	const updateHandler = async (_group) => {
		const res = await updateGroupById(localStorage.token, group.id, _group).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group updated successfully'));
			setGroups();
		}
	};

	const deleteHandler = async () => {
		const res = await deleteGroupById(localStorage.token, group.id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group deleted successfully'));
			setGroups();
		}
	};

	onMount(() => {
		const groupId = $page.url.searchParams.get('id');
		if (groupId && groupId === group.id) {
			showEdit = true;
		}
	});
</script>

<EditGroupModal
	bind:show={showEdit}
	edit
	{group}
	{defaultPermissions}
	tabs={['general', 'permissions', 'users', 'preview']}
	onSubmit={updateHandler}
	onDelete={deleteHandler}
/>

<button
	class="group flex cursor-pointer text-left w-full px-2.5 py-2 rounded-xl border-b border-gray-100/60 last:border-b-0 hover:bg-gray-50/70 dark:border-gray-850/60 dark:hover:bg-gray-850/50 transition"
	on:click={() => {
		showEdit = true;
	}}
>
	<div class="w-full">
		<div class="flex items-center gap-3">
			<div class="flex min-w-0 flex-1 flex-col gap-0.5 pl-1">
				<div class="flex min-w-0 items-center gap-2">
					<div class="text-sm font-normal line-clamp-1 text-gray-900 dark:text-gray-100">
						{group.name}
					</div>

					<div
						class="shrink-0 rounded-md bg-gray-500/10 px-1.5 py-0.5 text-[11px] font-normal leading-none text-gray-600 dark:text-gray-300"
					>
						{$i18n.t('{{COUNT}} members', { COUNT: group?.member_count ?? 0 })}
					</div>
				</div>

				<div class="flex min-w-0 items-center gap-1.5 text-xs text-gray-500">
					<div class="line-clamp-1 min-w-0">
						{#if group?.description}
							{group.description}
						{:else}
							{$i18n.t('No description')}
						{/if}
					</div>

					<div class="shrink-0 text-gray-300 dark:text-gray-700">/</div>

					<div class="shrink-0">
						{#if hasCustomPermissions}
							{$i18n.t('Custom permissions')}
						{:else}
							{$i18n.t('Uses defaults')}
						{/if}
					</div>
				</div>
			</div>

			<div
				class="shrink-0 px-1.5 text-xs text-gray-500 transition group-hover:text-gray-800 dark:text-gray-400 dark:group-hover:text-gray-200"
			>
				{$i18n.t('Edit')}
			</div>
		</div>
	</div>
</button>
