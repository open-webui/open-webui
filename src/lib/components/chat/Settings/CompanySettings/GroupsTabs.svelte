<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { createNewGroup, getGroups } from '$lib/apis/groups';
	import { user } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Accordeon from './Accordeon.svelte';
	import { toast } from 'svelte-sonner';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import ManageUsersMenu from './ManageUsersMenu.svelte';
	import { updateGroupById, deleteGroupById } from '$lib/apis/groups';
	import GroupPermissions from './GroupPermissions.svelte';
	import RenameGroupDialog from '$lib/components/common/ConfirmDialog.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
    import RemoveFromGroup from './RemoveFromGroup.svelte';

	const i18n = getContext('i18n');
	export let users = [];
	let groupName = '';
	let groups = [];

	let permissions = {
		workspace: {
			models: true,
			knowledge: true,
			prompts: true,
			tools: false
		},
		chat: {
			controls: true,
			file_upload: true,
			delete: true,
			edit: true,
			temporary: true
		},
		features: {
			web_search: false,
			image_generation: false,
			code_interpreter: false
		}
	};

	const setGroups = async () => {
		groups = await getGroups(localStorage.token);
	};

	const updateGroupHandler = async (groupId, _group) => {
		const res = await updateGroupById(localStorage.token, groupId, _group).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group updated successfully'));
			setGroups();
		}
	};

	const deleteHandler = async (id) => {
		const res = await deleteGroupById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group deleted successfully'));
			setGroups();
		}
	};

	$: console.log(groups);

	const addGroupHandler = async () => {
		const res = await createNewGroup(localStorage.token, {
			name: groupName,
			description: ''
		}).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group created successfully'));
			groups = await getGroups(localStorage.token);
			groupName = '';
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		} else {
			await setGroups();
		}
	});

	let showRenameGroup = false;
	let renameName = '';
	let renameGroupId = null;

	let showDeleteConfirm = false;
	let groupToDelete = null;
</script>

<RenameGroupDialog
	bind:show={showRenameGroup}
	title="Create New Folder"
	bind:inputValue={renameName}
	input={true}
	inputPlaceholder={$i18n.t('Title')}
	confirmLabel={$i18n.t('Done')}
	noMessage={true}
	inputType="input"
	on:confirm={(e) => {
		const group = groups.find((group) => group.id === renameGroupId);
		updateGroupHandler(renameGroupId, { ...group, name: renameName });
		renameName = '';
		renameGroupId = null;
	}}
	on:cancel={() => {
		renameName = '';
		renameGroupId = null;
	}}
/>

<DeleteConfirmDialog
	bind:show={showDeleteConfirm}
	title={$i18n.t('Delete group?')}
	on:confirm={() => {
		deleteHandler(groupToDelete?.id);
		groupToDelete = null;
	}}
	on:cancel={() => {
		groupToDelete = null;
	}}
>
	<div class=" text-sm text-gray-500 flex-1 line-clamp-3">
		{$i18n.t('This will delete')} <span class="  font-semibold">{groupToDelete?.name}</span>.
	</div>
</DeleteConfirmDialog>

<div class="pb-56">
	<div
		class="flex w-full justify-between items-center py-2.5 border-b border-lightGray-400 dark:border-customGray-700 mb-2.5"
	>
		<div class="flex w-full justify-between items-center">
			<div class="text-xs text-lightGray-100 dark:text-customGray-300 font-medium">{$i18n.t('Group Management')}</div>
		</div>
	</div>
	<div class="flex flex-col md:flex-row justify-between items-center mb-5">
		<div class="w-full flex-1 md:mr-2">
			<div class="relative w-full bg-lightGray-300 dark:bg-customGray-900 rounded-md">
				{#if groupName}
					<div class="text-xs absolute left-2.5 top-1 text-lightGray-100/50 dark:text-customGray-100/50">
						{$i18n.t('Group name')}
					</div>
				{/if}
				<input
					class={`px-2.5 text-sm ${groupName ? 'pt-2' : 'pt-0'} w-full h-12 bg-transparent text-lightGray-100 placeholder:text-lightGray-100 dark:text-white dark:placeholder:text-customGray-100 outline-none`}
					placeholder={$i18n.t('Create a group')}
					bind:value={groupName}
				/>
				{#if !groupName}
					<span
						class="absolute top-1/2 right-2.5 -translate-y-1/2 text-xs text-lightGray-100/50 dark:text-customGray-100/50 pointer-events-none select-none"
					>
						{$i18n.t('e.g., Marketing')}
					</span>
				{/if}
			</div>
		</div>
		<button
			class="w-full md:w-[25%] mt-2 md:mt-0 bg-lightGray-300 border-lightGray-400 text-lightGray-100 font-medium hover:bg-lightGray-700 text-xs dark:bg-customGray-900 border dark:border-customGray-700 dark:hover:bg-customGray-950 dark:text-customGray-200 px-4 h-12 rounded-lg transition"
			on:click={addGroupHandler}
			type="button"
		>
			{$i18n.t('Done')}
		</button>
	</div>
	<div>
		{#each groups as group (group.id)}
			<Accordeon id={group.id}>
				<span slot="title"
					>{group.name}
                    {#if users?.filter((user) => group.user_ids?.includes(user.id))?.length > 0}
					{users?.filter((user) => group.user_ids?.includes(user.id))?.length} ({$i18n.t(
						'Users'
					)})
                    {/if}
                    </span>
				<div slot="right" class="flex items-center">
					<ManageUsersMenu {users} {group} {updateGroupHandler}>
						<button type="button" class="flex items-center mr-1 font-medium hover:dark:text-white">
							<Plus className="size-2" />
							<span class="mr-1 ml-1">{$i18n.t('Add User')}</span>
							<ChevronDown className="size-2" />
						</button>
					</ManageUsersMenu>
					<GroupPermissions
						{group}
						on:editName={() => {
							renameName = group.name;
							renameGroupId = group.id;
							showRenameGroup = true;
						}}
						on:deleteGroup={() => {
							showDeleteConfirm = true;
							groupToDelete = group;
						}}
						on:changePermissions={(e) => {
							updateGroupHandler(group.id, {
								...group,
								permissions: { ...permissions, features: {
                                    web_search: e.detail.web_search,
			                        image_generation: e.detail.image_generation,
			                        code_interpreter: e.detail.code_interpreter
                                }}
							});
							console.log(e.detail);
						}}
					>
						<button type="button" class="hover:dark:text-white h-4">
							<EllipsisHorizontal />
						</button>
					</GroupPermissions>
				</div>
				<div class="py-2">
					{#each users?.filter((user) => group.user_ids?.includes(user.id)) as user (user.id)}
						<div class="flex items-center justify-between w-full group cursor-pointer mt-2.5">
							<div class="flex items-center">
								<img
									class=" rounded-full w-3 h-3 object-cover mr-1"
									src={user.profile_image_url.startsWith(WEBUI_BASE_URL) ||
									user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
									user.profile_image_url.startsWith('data:')
										? user.profile_image_url
										: `/user.png`}
									alt="user"
								/>
								{#if user?.first_name !== 'INVITED'}
									<div class="text-xs dark:text-customGray-100 mr-1 whitespace-nowrap">
										{user.first_name}
										{user.last_name}
									</div>
								{/if}
								<div class="text-xs dark:text-customGray-590 mr-1 whitespace-nowrap">{user.email}</div>
							</div>
							<RemoveFromGroup on:removeFromGroup={() => {
								console.log('test')
								updateGroupHandler(group.id, {
									...group,
									user_ids: [...group.user_ids?.filter(id => id !== user.id)]
								});
							}}>
								<button type="button" class="md:invisible group-hover:visible">
									<EllipsisHorizontal/>
								</button>
							</RemoveFromGroup>
						</div>
					{/each}
				</div>
			</Accordeon>
		{/each}
	</div>
</div>
