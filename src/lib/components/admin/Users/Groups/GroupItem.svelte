<script>
	import { toast } from 'svelte-sonner';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');

	import { deleteGroupById, updateGroupById } from '$lib/apis/groups';

	import Pencil from '$lib/components/icons/Pencil.svelte';
	import User from '$lib/components/icons/User.svelte';
	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';
	import GroupModal from './EditGroupModal.svelte';

	export let users = [];
	export let group = {
		name: 'Admins',
		user_ids: [1, 2, 3]
	};

	export let setGroups = () => {};

	let showEdit = false;

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
</script>

<GroupModal
	bind:show={showEdit}
	edit
	{users}
	{group}
	onSubmit={updateHandler}
	onDelete={deleteHandler}
/>

<button
	class="w-full px-6 py-3.5 text-sm text-left transition-colors"
	on:click={() => {
		showEdit = true;
	}}
	aria-label={`Edit group ${group.name}`}
>
	<div class="flex items-center gap-3 text-gray-800 dark:text-gray-100">
		<div class="flex-1 min-w-0 flex items-center gap-3 font-medium">
			<div class="p-2 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 flex-shrink-0">
				<UserCircleSolid className="size-4" />
			</div>
			<span class="truncate">{group.name}</span>
		</div>

		<div class="flex-1 flex items-center gap-2 text-gray-600 dark:text-gray-300 font-medium">
			<span class="inline-flex min-w-8 justify-center rounded-md bg-gray-100 dark:bg-gray-800 px-2 py-0.5 text-xs font-semibold text-gray-700 dark:text-gray-200">
				{group.user_ids.length}
			</span>
			<span class="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Users</span>

			<div class="text-gray-500 dark:text-gray-400">
				<User className="size-3.5" />
			</div>
		</div>

		<div class="w-24 flex justify-end">
			<div class="rounded-lg px-2.5 py-1.5 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-900 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors inline-flex items-center gap-1.5">
				<Pencil className="size-3.5" />
				<span class="text-xs font-medium">Edit</span>
			</div>
		</div>
	</div>
</button>
