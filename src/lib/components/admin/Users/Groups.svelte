<script>
	import { toast } from 'svelte-sonner';
	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { WEBUI_NAME, config, user, showSidebar, knowledge } from '$lib/stores';
	import { WEBUI_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import UsersSolid from '$lib/components/icons/UsersSolid.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import User from '$lib/components/icons/User.svelte';
	import UserCircleSolid from '$lib/components/icons/UserCircleSolid.svelte';
	import GroupModal from './Groups/EditGroupModal.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import GroupItem from './Groups/GroupItem.svelte';
	import AddGroupModal from './Groups/AddGroupModal.svelte';
	import { createNewGroup, getGroups } from '$lib/apis/groups';
	import { getUserDefaultPermissions, updateUserDefaultPermissions } from '$lib/apis/users';

	const i18n = getContext('i18n');

	let loaded = false;

	export let users = [];

	let groups = [];
	let filteredGroups;

	$: filteredGroups = groups.filter((user) => {
		if (search === '') {
			return true;
		} else {
			let name = user.name.toLowerCase();
			const query = search.toLowerCase();
			return name.includes(query);
		}
	});

	let search = '';
	let defaultPermissions = {
		workspace: {
			models: false,
			knowledge: false,
			prompts: false,
			tools: false
		},
		sharing: {
			public_models: false,
			public_knowledge: false,
			public_prompts: false,
			public_tools: false
		},
		chat: {
			controls: true,
			file_upload: true,
			delete: true,
			edit: true,
			stt: true,
			tts: true,
			call: true,
			multiple_models: true,
			temporary: true,
			temporary_enforced: false
		},
		features: {
			direct_tool_servers: false,
			web_search: true,
			image_generation: true,
			code_interpreter: true
		}
	};

	let showCreateGroupModal = false;
	let showDefaultPermissionsModal = false;

	const setGroups = async () => {
		groups = await getGroups(localStorage.token);
	};

	const addGroupHandler = async (group) => {
		const res = await createNewGroup(localStorage.token, group).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group created successfully'));
			groups = await getGroups(localStorage.token);
		}
	};

	const updateDefaultPermissionsHandler = async (group) => {
		console.log(group.permissions);

		const res = await updateUserDefaultPermissions(localStorage.token, group.permissions).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		if (res) {
			toast.success($i18n.t('Default permissions updated successfully'));
			defaultPermissions = await getUserDefaultPermissions(localStorage.token);
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		} else {
			await setGroups();
			defaultPermissions = await getUserDefaultPermissions(localStorage.token);
		}
		loaded = true;
	});
</script>

{#if loaded}
	<AddGroupModal bind:show={showCreateGroupModal} onSubmit={addGroupHandler} />
	
	<div class="mb-6 flex flex-col gap-4">
		<!-- Header Section -->
		<div class="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
			<div class="flex items-center gap-3">
				<div>
					<h2 class="text-2xl font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Groups')}
					</h2>
					<p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
						{groups.length} {groups.length === 1 ? 'group' : 'groups'}
					</p>
				</div>
			</div>

			<!-- Search and Create Section -->
			<div class="flex gap-2">
				<div class="relative flex-1 md:w-72">
					<div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4 text-gray-400"
						>
							<path
								fill-rule="evenodd"
								d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<input
						class="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400 focus:border-transparent outline-none transition-all"
						bind:value={search}
						placeholder={$i18n.t('Search groups...')}
					/>
				</div>

				<Tooltip content={$i18n.t('Create Group')}>
					<button
						class="px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white transition-colors font-medium text-sm flex items-center gap-2 shadow-sm"
						on:click={() => {
							showCreateGroupModal = !showCreateGroupModal;
						}}
					>
						<Plus className="size-4" />
						<span class="hidden sm:inline">Create Group</span>
					</button>
				</Tooltip>
			</div>
		</div>
	</div>

	<div>
		{#if filteredGroups.length === 0}
			<div class="flex flex-col items-center justify-center py-16 px-4 bg-gray-50 dark:bg-gray-800/50 rounded-xl border-2 border-dashed border-gray-200 dark:border-gray-700">
				<div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-full mb-4">
					<UsersSolid className="size-8 text-blue-600 dark:text-blue-400" />
				</div>
				
				<h3 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">
					{$i18n.t('Organize your users')}
				</h3>

				<p class="text-sm text-gray-500 dark:text-gray-400 text-center max-w-md mb-6">
					{$i18n.t('Use groups to group your users and assign permissions.')}
				</p>

				<button
					class="px-6 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 text-white transition-colors font-medium text-sm flex items-center gap-2 shadow-sm"
					aria-label={$i18n.t('Create Group')}
					on:click={() => {
						showCreateGroupModal = true;
					}}
				>
					<Plus className="size-4" />
					{$i18n.t('Create Group')}
				</button>
			</div>
		{:else}
			<div class="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm bg-white dark:bg-gray-900 mb-4">
				<!-- Table Header -->
				<div class="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-3.5">
					<div class="flex items-center gap-3 text-xs font-semibold text-gray-600 dark:text-gray-300 uppercase tracking-wider">
						<div class="flex-1">Group</div>
						<div class="flex-1">Users</div>
						<div class="w-24 text-right">Actions</div>
					</div>
				</div>

				<!-- Groups List -->
				<div class="divide-y divide-gray-200 dark:divide-gray-700">
					{#each filteredGroups as group}
						<div class="hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
							<GroupItem {group} {users} {setGroups} />
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Default Permissions Card -->
		<GroupModal
			bind:show={showDefaultPermissionsModal}
			tabs={['permissions']}
			bind:permissions={defaultPermissions}
			custom={false}
			onSubmit={updateDefaultPermissionsHandler}
		/>

		<button
			class="flex items-center justify-between rounded-xl w-full p-4 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-all shadow-sm group"
			on:click={() => {
				showDefaultPermissionsModal = true;
			}}
		>
			<div class="flex items-center gap-3">
				<div class="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-xl group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30 transition-colors">
					<UsersSolid className="size-5 text-blue-600 dark:text-blue-400" />
				</div>

				<div class="text-left">
					<div class="text-sm font-semibold text-gray-900 dark:text-white">
						{$i18n.t('Default permissions')}
					</div>
					<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						{$i18n.t('applies to all users with the "user" role')}
					</div>
				</div>
			</div>

			<div class="text-gray-400 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors">
				<ChevronRight strokeWidth="2.5" className="size-5" />
			</div>
		</button>
	</div>
{/if}