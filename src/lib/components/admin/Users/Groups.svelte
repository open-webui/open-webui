<script context="module">
	/** @typedef {{ id: string, name: string, parent_group_id?: string | null, path: string, ancestor_ids: string[] }} GroupListItem */
</script>

<script>
	import { toast } from 'svelte-sonner';
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { adminGroupCount, user } from '$lib/stores';

	import Search from '$lib/components/icons/Search.svelte';
	import EditGroupModal from './Groups/EditGroupModal.svelte';
	import GroupItem from './Groups/GroupItem.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import Select from '$lib/components/common/Select.svelte';
	import { createNewGroup, getGroups, updateGroupById } from '$lib/apis/groups';
	import { getUserDefaultPermissions, updateUserDefaultPermissions } from '$lib/apis/users';

	const i18n = getContext('i18n');

	let loaded = false;

	/** @type {any[]} */
	let groups = [];

	let query = '';
	let sortBy = 'name';
	let collapsed = new Set();
	/** @type {any} */
	let draggedGroup = null;
	let dropTarget = '';
	let moving = false;

	const sortItems = [
		{ value: 'members', label: $i18n.t('Members') },
		{ value: 'name', label: $i18n.t('Name') }
	];

	/** @type {any[]} */
	let filteredGroups = [];
	/** @type {Map<string | null, any[]>} */
	let children = new Map();
	$: {
		children = new Map();
		for (const group of groups) {
			const parent = group.parent_group_id ?? null;
			children.set(parent, [...(children.get(parent) ?? []), group]);
		}
		for (const siblings of children.values()) {
			siblings.sort((a, b) =>
				sortBy === 'members'
					? (b.member_count ?? 0) - (a.member_count ?? 0) || a.name.localeCompare(b.name)
					: a.name.localeCompare(b.name)
			);
		}
		const matching = new Set();
		for (const group of groups) {
			if (group.path.toLowerCase().includes(query.toLowerCase())) {
				matching.add(group.id);
				for (const id of group.ancestor_ids) matching.add(id);
			}
		}
		const visible = [];
		const pending = [...(children.get(null) ?? [])].reverse();
		while (pending.length) {
			const group = pending.pop();
			if (!matching.has(group.id)) continue;
			visible.push(group);
			if (query || !collapsed.has(group.id)) {
				pending.push(...[...(children.get(group.id) ?? [])].reverse());
			}
		}
		filteredGroups = visible;
	}

	/** @param {string | null} parentId */
	const canDrop = (parentId) => {
		const parent = groups.find((group) => group.id === parentId);
		return (
			draggedGroup &&
			!moving &&
			(draggedGroup.parent_group_id ?? null) !== parentId &&
			draggedGroup.id !== parentId &&
			!parent?.ancestor_ids.includes(draggedGroup.id)
		);
	};

	/** @param {string | null} parentId */
	const moveGroup = async (parentId) => {
		if (!canDrop(parentId)) return;
		const group = draggedGroup;
		draggedGroup = null;
		dropTarget = '';
		moving = true;
		try {
			await updateGroupById(localStorage.token, group.id, {
				name: group.name,
				description: group.description,
				parent_group_id: parentId
			});
			collapsed.delete(parentId);
			collapsed = new Set(collapsed);
			await setGroups();
			toast.success($i18n.t('Group moved successfully'));
		} catch (error) {
			toast.error(String(error));
		} finally {
			moving = false;
		}
	};

	$: if (loaded) {
		adminGroupCount.set(
			groups.filter((group) => group.path.toLowerCase().includes(query.toLowerCase())).length
		);
	}

	/** @type {any} */
	let defaultPermissions = {};

	let showAddGroupModal = false;
	let showDefaultPermissionsModal = false;

	const setGroups = async () => {
		/** @type {any[]} */
		const result = await getGroups(localStorage.token);
		const byId = new Map(result.map((group) => [group.id, group]));
		groups = result.map((group) => {
			const ancestors = [];
			const seen = new Set([group.id]);
			let parent = byId.get(group.parent_group_id);
			while (parent && !seen.has(parent.id)) {
				seen.add(parent.id);
				ancestors.unshift(parent);
				parent = byId.get(parent.parent_group_id);
			}
			return {
				...group,
				path: [...ancestors, group].map((item) => item.name).join(' / '),
				ancestor_ids: ancestors.map((item) => item.id)
			};
		});
	};

	/** @param {any} updatedGroup */
	const updateGroup = (updatedGroup) => {
		groups = groups.map((group) =>
			group.id === updatedGroup.id ? { ...group, ...updatedGroup } : group
		);
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
		return !!res;
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
		return !!res;
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
	{#if showAddGroupModal}
		<EditGroupModal
			bind:show={showAddGroupModal}
			edit={false}
			tabs={['general', 'permissions']}
			permissions={defaultPermissions}
			{groups}
			onSubmit={addGroupHandler}
		/>
	{/if}

	<div>
		<div class="sticky top-0 z-10 bg-white dark:bg-gray-900">
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
					triggerClass="relative h-8 shrink-0 flex items-center gap-1 px-1.5 py-1.5 bg-transparent rounded-xl text-[0.8125rem] font-normal text-gray-700 transition hover:text-gray-900 dark:text-gray-200 dark:hover:text-gray-100"
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
					class="ml-1 shrink-0 rounded-lg bg-gray-50 px-2.5 py-1 text-xs text-gray-900 transition ring-1 ring-gray-200 hover:bg-gray-100 dark:bg-gray-850 dark:text-gray-100 dark:ring-gray-800 dark:hover:bg-gray-800"
					on:click={() => {
						showAddGroupModal = !showAddGroupModal;
					}}
				>
					{$i18n.t('New Group')}
				</button>
			</div>
		</div>

		{#if filteredGroups.length !== 0}
			<div class="mt-2" aria-label={$i18n.t('Group hierarchy')}>
				{#each filteredGroups as group (group.id)}
					<div
						role="group"
						aria-label={group.name}
						class="relative flex items-center rounded-xl transition {dropTarget === group.id
							? 'bg-gray-100/40 dark:bg-gray-800/30'
							: 'hover:bg-gray-50/60 dark:hover:bg-gray-900'} {draggedGroup?.id === group.id
							? 'opacity-40'
							: ''}"
						style:padding-left={`${Math.min(group.ancestor_ids.length, 8) * 20}px`}
						on:dragover={(event) => {
							if (canDrop(group.id)) {
								event.preventDefault();
								if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
								dropTarget = group.id;
							}
						}}
						on:dragleave={(event) => {
							if (
								!(event.relatedTarget instanceof Node) ||
								!event.currentTarget.contains(event.relatedTarget)
							)
								dropTarget = '';
						}}
						on:drop|preventDefault={() => moveGroup(group.id)}
					>
						{#each group.ancestor_ids.slice(0, 8) as ancestorId, depth}
							<span
								aria-hidden="true"
								class="pointer-events-none absolute top-0 bottom-0 border-l border-gray-100 dark:border-gray-900"
								style:left={`${depth * 20 + 11}px`}
							></span>
						{/each}
						{#if children.has(group.id)}
							<button
								type="button"
								class="z-10 flex size-6 shrink-0 items-center justify-center rounded-md text-gray-500 hover:text-gray-900 dark:hover:text-gray-100"
								aria-label={$i18n.t(
									collapsed.has(group.id) ? 'Expand {{name}}' : 'Collapse {{name}}',
									{ name: group.name }
								)}
								aria-expanded={!!query || !collapsed.has(group.id)}
								on:click={() => {
									collapsed.has(group.id) ? collapsed.delete(group.id) : collapsed.add(group.id);
									collapsed = new Set(collapsed);
								}}
							>
								<div
									class="transition-transform"
									class:rotate-90={!!query || !collapsed.has(group.id)}
								>
									<ChevronRight className="size-3.5" />
								</div>
							</button>
						{:else}<span class="w-6 shrink-0"></span>{/if}
						<div class="min-w-0 flex-1">
							<GroupItem
								{group}
								{groups}
								{setGroups}
								{updateGroup}
								{defaultPermissions}
								draggable={!moving}
								onDragStart={(event) => {
									if (!event.dataTransfer) return;
									draggedGroup = group;
									event.dataTransfer.effectAllowed = 'move';
									event.dataTransfer.setData('text/plain', group.id);
								}}
								onDragEnd={() => {
									draggedGroup = null;
									dropTarget = '';
								}}
							/>
						</div>
					</div>
				{/each}
				{#if draggedGroup}
					<div
						role="region"
						aria-label={$i18n.t('Move to top level')}
						class="mt-1 rounded-lg px-3 py-2 text-xs transition {dropTarget === 'root'
							? 'bg-gray-100/40 text-gray-500 dark:bg-gray-800/30 dark:text-gray-400'
							: 'text-gray-400 dark:text-gray-500'}"
						on:dragover={(event) => {
							if (canDrop(null)) {
								event.preventDefault();
								dropTarget = 'root';
							}
						}}
						on:dragleave={() => {
							dropTarget = '';
						}}
						on:drop|preventDefault={() => moveGroup(null)}
					>
						{$i18n.t('Move to top level')}
					</div>
				{/if}
			</div>
		{:else}
			<div class="flex w-full flex-col items-center justify-center py-16 pb-24">
				<div class="max-w-sm text-center text-gray-900 dark:text-gray-100">
					<div class="mb-1.5 text-sm">{$i18n.t('No groups found')}</div>
					<div class="text-center text-xs leading-5 text-gray-500">
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
