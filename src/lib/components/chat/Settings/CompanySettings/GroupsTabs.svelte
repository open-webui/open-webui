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
    import { updateGroupById } from '$lib/apis/groups';

	const i18n = getContext('i18n');
	export let users = [];
	let groupName = '';
	let groups = [];

    let permissions = {
		workspace: {
			models: false,
			knowledge: false,
			prompts: false,
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
			web_search: true,
			image_generation: true,
			code_interpreter: true
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
</script>

<div class="pb-56">
	<div
		class="flex w-full justify-between items-center py-2.5 border-b border-customGray-700 mb-2.5"
	>
		<div class="flex w-full justify-between items-center">
			<div class="text-xs dark:text-customGray-300">{$i18n.t('Group Management')}</div>
		</div>
	</div>
	<div class="flex justify-between items-center mb-5">
		<div class="flex-1 mr-2">
			<div class="relative w-full dark:bg-customGray-900 rounded-md">
				{#if groupName}
					<div class="text-xs absolute left-2.5 top-1 dark:text-customGray-100/50">
						{$i18n.t('Group name')}
					</div>
				{/if}
				<input
					class={`px-2.5 text-sm ${groupName ? 'mt-2' : 'mt-0'} w-full h-10 bg-transparent dark:text-white dark:placeholder:text-customGray-100 outline-none`}
					placeholder={$i18n.t('Create a group')}
					bind:value={groupName}
				/>
				{#if !groupName}
					<span
						class="absolute top-1/2 right-2.5 -translate-y-1/2 text-xs dark:text-customGray-100/50 pointer-events-none select-none"
					>
						{$i18n.t('e.g., Marketing')}
					</span>
				{/if}
			</div>
		</div>
		<button
			class="bg-gray-900 text-xs dark:bg-customGray-900 border dark:border-customGray-700 dark:hover:bg-customGray-950 text-gray-100 dark:text-customGray-200 px-4 h-10 rounded-lg transition"
			on:click={addGroupHandler}
			type="button"
		>
			{$i18n.t('Done')}
		</button>
	</div>
	<div>
		{#each groups as group (group.id)}
			<Accordeon>
				<span slot="title"
					>{group.name}
					{users?.filter((user) => group.user_ids?.includes(user.id))?.length} ({$i18n.t(
						'Users'
					)})</span
				>
				<div slot="right" class="flex items-center">
					<ManageUsersMenu {users} {group} {updateGroupHandler}>
						<button type="button" class="flex items-center mr-1 font-medium hover:dark:text-white">
							<Plus className="size-2" />
							<span class="mr-1 ml-1">{$i18n.t('Add User')}</span>
							<ChevronDown className="size-2" />
						</button>
					</ManageUsersMenu>
					<button
						type="button"
						on:click={(e) => {
							e.stopPropagation();
						}}
					>
						<EllipsisHorizontal />
					</button>
				</div>
				{#each users?.filter((user) => group.user_ids?.includes(user.id)) as user (user.id)}
					<div class="flex items-center my-2.5">
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
				{/each}
			</Accordeon>
		{/each}
	</div>
</div>
