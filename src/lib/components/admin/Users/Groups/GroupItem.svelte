<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');

	import { deleteGroupById, updateGroupById, cloneGroupById } from '$lib/apis/groups';

	import Pencil from '$lib/components/icons/Pencil.svelte';
	import User from '$lib/components/icons/User.svelte';
	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';
	import GroupModal from './EditGroupModal.svelte';
	import CloneGroupModal from './CloneGroupModal.svelte';
	import Dropdown from '$lib/components/common/Dropdown.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import Duplicate from '$lib/components/icons/Duplicate.svelte';

	export let users = [];
	export let group = {
		name: 'Admins',
		user_ids: [1, 2, 3]
	};

	export let setGroups = () => {};

	let showEdit = false;
	let showClone = false;
	let showActionMenu = false;

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

	const cloneHandler = async (clone_data) => {
		const res = await cloneGroupById(localStorage.token, group.id, clone_data).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group cloned successfully'));
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

<CloneGroupModal bind:show={showClone} {group} onSubmit={cloneHandler} />

<div class="flex items-center gap-3 justify-between px-1 text-xs w-full transition">
	<button
		class="flex items-center gap-1.5 w-full font-medium flex-1"
		on:click={() => {
			showEdit = true;
		}}
	>
		<div>
			<UserCircleSolid className="size-4" />
		</div>
		<div class="line-clamp-1">
			{group.name}
		</div>
	</button>

	<div class="flex items-center gap-1.5 w-fit font-medium text-right justify-end">
		{group.user_ids.length}

		<div>
			<User className="size-3.5" />
		</div>

		<div on:click={(e) => e.stopPropagation()}>
			<Dropdown bind:show={showActionMenu} side="left" align="start">
				<button
					class=" rounded-lg p-1 hover:bg-gray-100 dark:hover:bg-gray-850 transition"
					on:click={() => (showActionMenu = !showActionMenu)}
				>
					<EllipsisHorizontal className="size-3.5" />
				</button>
				<div slot="content">
					<div
						class="w-full max-w-[130px] rounded-lg p-1 border border-gray-200 dark:border-gray-800 z-50 bg-white dark:bg-gray-900 text-black dark:text-white"
					>
						<button
							class="flex items-center w-full px-3 py-2 text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
							on:click={() => {
								showEdit = true;
								showActionMenu = false;
							}}
						>
							<Pencil className="size-3.5 mr-2" />
							{$i18n.t('Edit')}
						</button>
						<button
							class="flex items-center w-full px-3 py-2 text-sm font-medium hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg"
							on:click={() => {
								showClone = true;
								showActionMenu = false;
							}}
						>
							<Duplicate className="size-3.5 mr-2" />
							{$i18n.t('Clone')}
						</button>
					</div>
				</div>
			</Dropdown>
		</div>
	</div>
</div>
