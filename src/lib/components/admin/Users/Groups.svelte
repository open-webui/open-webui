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
	import UsersSolid from '$lib/components/icons/UsersSolid.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import EditGroupModal from './Groups/EditGroupModal.svelte';
	import GroupItem from './Groups/GroupItem.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import { Select } from 'bits-ui';
	import { createNewGroup, getGroups } from '$lib/apis/groups';
	import {
		getUserDefaultPermissions,
		getAllUsers,
		updateUserDefaultPermissions
	} from '$lib/apis/users';

	const i18n = getContext('i18n');

	let loaded = false;

	let groups = [];

	let query = '';
	let sortBy = 'members';

	const sortItems = [
		{ value: 'name', label: $i18n.t('Name') },
		{ value: 'members', label: $i18n.t('Members') }
	];

	$: filteredGroups = groups
		.filter((group) => {
			if (query === '') {
				return true;
			} else {
				let name = group.name.toLowerCase();
				const q = query.toLowerCase();
				return name.includes(q);
			}
		})
		.sort((a, b) => {
			if (sortBy === 'name') {
				return a.name.localeCompare(b.name);
			} else if (sortBy === 'members') {
				return (b.member_count ?? 0) - (a.member_count ?? 0);
			}
			return 0;
		});

	let defaultPermissions = {};

	let showAddGroupModal = false;
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
		console.debug(group.permissions);

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
			return;
		}

		defaultPermissions = await getUserDefaultPermissions(localStorage.token);
		await setGroups();
		loaded = true;
	});
</script>

{#if loaded}
	<EditGroupModal
		bind:show={showAddGroupModal}
		edit={false}
		tabs={['general', 'permissions']}
		permissions={defaultPermissions}
		onSubmit={addGroupHandler}
	/>

	<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
				<div>
					{$i18n.t('Groups')}
				</div>

				<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
					{groups.length}
				</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				<button
					class="px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
					on:click={() => {
						showAddGroupModal = !showAddGroupModal;
					}}
				>
					<Plus className="size-3" strokeWidth="2.5" />

					<div class="hidden md:block md:ml-1 text-xs">{$i18n.t('New Group')}</div>
				</button>
			</div>
		</div>
	</div>

	<div
		class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
	>
		<div class="flex items-center w-full space-x-2 py-0.5 px-3.5">
			<div class="flex flex-1">
				<div class="self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class="w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
					bind:value={query}
					aria-label={$i18n.t('Search Groups')}
					placeholder={$i18n.t('Search Groups')}
				/>
				{#if query}
					<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
						<button
							class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
							aria-label={$i18n.t('Clear search')}
							on:click={() => {
								query = '';
							}}
						>
							<XMark className="size-3" strokeWidth="2" />
						</button>
					</div>
				{/if}
			</div>

			<Select.Root
				selected={sortItems.find((item) => item.value === sortBy)}
				items={sortItems}
				onSelectedChange={(selectedItem) => {
					sortBy = selectedItem.value;
				}}
			>
				<Select.Trigger
					class="relative flex items-center gap-0.5 px-2.5 py-1.5 text-sm bg-gray-50 dark:bg-gray-850 rounded-xl shrink-0"
					aria-label={$i18n.t('Sort by')}
				>
					<Select.Value
						class="inline-flex h-input px-0.5 outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
						placeholder={$i18n.t('Sort by')}
					/>
					<ChevronDown className="size-3.5" strokeWidth="2.5" />
				</Select.Trigger>

				<Select.Content
					class="rounded-2xl min-w-[170px] p-1 border border-gray-100 dark:border-gray-800 z-50 bg-white dark:bg-gray-850 dark:text-white shadow-lg"
					sameWidth={false}
					align="end"
				>
					{#each sortItems as item}
						<Select.Item
							class="flex gap-2 items-center px-3 py-1.5 text-sm cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800 rounded-xl"
							value={item.value}
							label={item.label}
						>
							{item.label}

							{#if sortBy === item.value}
								<div class="ml-auto">
									<Check />
								</div>
							{/if}
						</Select.Item>
					{/each}
				</Select.Content>
			</Select.Root>
		</div>

		{#if filteredGroups.length !== 0}
			<div class="my-2 px-3 grid grid-cols-1 gap-1">
				{#each filteredGroups as group}
					<GroupItem {group} {setGroups} {defaultPermissions} />
				{/each}
			</div>
		{:else}
			<div class="w-full h-full flex flex-col justify-center items-center my-16 mb-24">
				<div class="max-w-md text-center">
					<div class="text-3xl mb-3">👥</div>
					<div class="text-lg font-medium mb-1">{$i18n.t('No groups found')}</div>
					<div class="text-gray-500 text-center text-xs">
						{$i18n.t('Use groups to organize your users and assign permissions.')}
					</div>
				</div>
			</div>
		{/if}
	</div>

	<EditGroupModal
		bind:show={showDefaultPermissionsModal}
		tabs={['permissions']}
		bind:permissions={defaultPermissions}
		custom={false}
		onSubmit={updateDefaultPermissionsHandler}
	/>

	<button
		class="flex items-center justify-between rounded-lg w-full transition mt-4"
		aria-haspopup="dialog"
		on:click={() => {
			showDefaultPermissionsModal = true;
		}}
	>
		<div class="flex items-center gap-2.5">
			<div class="p-1.5 bg-black/5 dark:bg-white/10 rounded-full">
				<UsersSolid className="size-4" />
			</div>

			<div class="text-left">
				<div class=" text-sm font-medium">{$i18n.t('Default permissions')}</div>

				<div class="flex text-xs mt-0.5">
					{$i18n.t('applies to all users with the "user" role')}
				</div>
			</div>
		</div>

		<div>
			<ChevronRight strokeWidth="2.5" />
		</div>
	</button>
{/if}
