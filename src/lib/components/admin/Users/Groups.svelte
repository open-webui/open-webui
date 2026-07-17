<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { adminGroupCount, user } from '$lib/stores';

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

	/** @type {any[]} */
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

	/** @type {any} */
	let defaultPermissions = {};

	let showAddGroupModal = false;
	let showDefaultPermissionsModal = false;

	const setGroups = async () => {
		groups = await getGroups(localStorage.token);
		adminGroupCount.set(groups.length);
	};

	/** @param {any} group */
	const addGroupHandler = async (group) => {
		const res = await createNewGroup(localStorage.token, group).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			toast.success($i18n.t('Group created successfully'));
			await setGroups();
		}
	};

	/** @param {any} group */
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

	<div class="space-y-1">
		<div class="flex h-8 flex-1 items-center w-full gap-2">
			<div class="flex min-w-0 flex-1 items-center">
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

			<button
				class="h-8 shrink-0 p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-850 transition font-normal text-sm flex items-center"
				aria-label={$i18n.t('New Group')}
				on:click={() => {
					showAddGroupModal = !showAddGroupModal;
				}}
			>
				<Plus className="size-3.5" strokeWidth="2.5" />
			</button>
		</div>

		{#if filteredGroups.length !== 0}
			<div class="mt-1 grid grid-cols-1">
				{#each filteredGroups as group, idx}
					<GroupItem {group} {setGroups} {defaultPermissions} />
					{#if idx < filteredGroups.length - 1}
						<hr class="border-gray-50 dark:border-gray-850/40" />
					{/if}
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

		<hr class="my-1 border-gray-50 dark:border-gray-850/40" />

		<button
			class="group flex cursor-pointer text-left w-full px-2.5 py-2"
			aria-haspopup="dialog"
			on:click={() => {
				showDefaultPermissionsModal = true;
			}}
		>
			<div class="w-full">
				<div class="flex items-center gap-3">
					<div class="flex min-w-0 flex-1 flex-col gap-0.5 pl-1">
						<div class="text-sm font-normal text-gray-900 group-hover:underline dark:text-gray-100">
							{$i18n.t('Default permissions')}
						</div>

						<div class="line-clamp-1 text-xs text-gray-500">
							{$i18n.t('applies to all users with the "user" role')}
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
