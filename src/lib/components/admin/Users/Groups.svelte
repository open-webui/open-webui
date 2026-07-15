<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { user } from '$lib/stores';

	import Plus from '$lib/components/icons/Plus.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import EditGroupModal from './Groups/EditGroupModal.svelte';
	import GroupItem from './Groups/GroupItem.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import Select from '$lib/components/common/Select.svelte';
	import { createNewGroup, getGroups } from '$lib/apis/groups';
	import { getUserDefaultPermissions, updateUserDefaultPermissions } from '$lib/apis/users';

	const i18n = getContext('i18n');

	let loaded = false;

	let groups = [];

	let query = '';
	let sortBy = 'members';

	const sortItems = [
		{ value: 'members', label: $i18n.t('Members') },
		{ value: 'name', label: $i18n.t('Name') }
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
			}

			return (b.member_count ?? 0) - (a.member_count ?? 0) || a.name.localeCompare(b.name);
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

	<div class="flex flex-col gap-1 mt-0.5 mb-3">
		<div class="flex justify-between items-center">
			<div class="flex items-center md:self-center text-xl font-normal px-0.5 gap-2 shrink-0">
				<div>
					{$i18n.t('Groups')}
				</div>

				<div class="text-lg font-normal text-gray-500 dark:text-gray-500">
					{filteredGroups.length}
				</div>
			</div>

			<div class="flex w-full justify-end gap-1.5">
				<button
					class="flex text-xs items-center space-x-1 px-3 py-1.5 rounded-xl bg-gray-50 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 dark:text-gray-200 transition"
					aria-haspopup="dialog"
					on:click={() => {
						showDefaultPermissionsModal = true;
					}}
				>
					<div class="self-center font-normal line-clamp-1">
						{$i18n.t('Default permissions')}
					</div>
				</button>

				<button
					class="px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-normal text-sm flex items-center"
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
		<div class="px-2.5 flex h-8 flex-1 items-center w-full gap-2">
			<div class="flex min-w-0 flex-1">
				<div class="self-center ml-1 mr-3">
					<Search className="size-3.5" />
				</div>
				<input
					class="w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
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

			<Select
				bind:value={sortBy}
				items={sortItems}
				placeholder={$i18n.t('Sort')}
				triggerClass="relative h-8 shrink-0 flex items-center gap-1 px-1.5 py-1.5 bg-transparent rounded-xl text-[13px] font-normal text-gray-700 transition hover:text-gray-900 dark:text-gray-200 dark:hover:text-gray-100"
				labelClass="inline-flex h-input outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
				align="end"
			>
				<svelte:fragment slot="trigger" let:selectedLabel>
					<span
						class="inline-flex h-input outline-hidden bg-transparent truncate placeholder-gray-400 focus:outline-hidden"
					>
						{selectedLabel}
					</span>
					<ChevronDown className="size-3.5" strokeWidth="2.5" />
				</svelte:fragment>

				<svelte:fragment slot="item" let:item let:selected>
					{item.label}
					<div class="ml-auto {selected ? '' : 'invisible'}">
						<Check />
					</div>
				</svelte:fragment>
			</Select>
		</div>

		{#if filteredGroups.length !== 0}
			<div class="mt-1 grid grid-cols-1 px-2">
				{#each filteredGroups as group}
					<GroupItem {group} {setGroups} {defaultPermissions} />
				{/each}
			</div>
		{:else}
			<div class="w-full h-full flex flex-col justify-center items-center my-16 mb-24">
				<div class="max-w-md text-center">
					<div class="text-3xl mb-3">👥</div>
					<div class="text-lg font-normal mb-1">{$i18n.t('No groups found')}</div>
					<div class="text-gray-500 text-center text-xs">
						{$i18n.t('Use groups to organize your users and assign permissions.')}
					</div>
				</div>
			</div>
		{/if}
	</div>

	{#if showDefaultPermissionsModal}
		<EditGroupModal
			bind:show={showDefaultPermissionsModal}
			tabs={['permissions']}
			permissions={defaultPermissions}
			custom={false}
			onSubmit={updateDefaultPermissionsHandler}
		/>
	{/if}
{/if}
