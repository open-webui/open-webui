<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';

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

	onMount(() => {
		const groupId = $page.url.searchParams.get('id');
		if (groupId && groupId === group.id) {
			showEdit = true;
		}
	});
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
	class="flex items-center gap-3 justify-between px-1 text-xs w-full transition"
	on:click={() => {
		showEdit = true;
	}}
>
	<div class="flex items-center gap-1.5 w-full font-medium flex-1">
		<div>
			<UserCircleSolid className="size-4" />
		</div>
		<div class="line-clamp-1">
			{group.name}
		</div>
	</div>

	<div class="flex items-center gap-1.5 w-fit font-medium text-right justify-end">
		{group.user_ids.length}

		<div>
			<User className="size-3.5" />
		</div>

		<div class=" rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition">
			<Pencil className="size-3.5" />
		</div>
	</div>
</button>
