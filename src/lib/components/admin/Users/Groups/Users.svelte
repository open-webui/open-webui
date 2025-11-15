<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import { WEBUI_BASE_URL } from '$lib/constants';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Search from '$lib/components/icons/Search.svelte';

	export let users = [];
	export let userIds = [];

	let filteredUsers = [];
	let query = '';
	let sortBy: 'members' | 'name' | 'role' | 'last_active' | 'created' = 'members';
	let selectAllState: 'checked' | 'unchecked' | 'indeterminate' = 'unchecked';

	const getSelectAllState = (filteredUsers, userIds) => {
		const filteredUserIds = filteredUsers.map((u) => u.id);
		const selectedCount = filteredUserIds.filter((id) => userIds.includes(id)).length;

		if (selectedCount === 0) return 'unchecked';
		if (selectedCount === filteredUserIds.length) return 'checked';
		return 'indeterminate';
	};

	$: selectAllState = getSelectAllState(filteredUsers, userIds);

	$: filteredUsers = users
		.filter((user) => {
			if (query === '') {
				return true;
			}

			return (
				user.name.toLowerCase().includes(query.toLowerCase()) ||
				user.email.toLowerCase().includes(query.toLowerCase())
			);
		})
		.sort((a, b) => {
			switch (sortBy) {
				case 'members':
					const aUserIndex = userIds.indexOf(a.id);
					const bUserIndex = userIds.indexOf(b.id);
					if (aUserIndex !== -1 && bUserIndex === -1) return -1;
					if (bUserIndex !== -1 && aUserIndex === -1) return 1;
					if (aUserIndex !== -1 && bUserIndex !== -1) return aUserIndex - bUserIndex;
					return a.name.localeCompare(b.name);
				case 'name':
					return a.name.localeCompare(b.name);
				case 'role':
					if (a.role === b.role) {
						return a.name.localeCompare(b.name);
					}
					return a.role.localeCompare(b.role);
				case 'last_active':
					if (a.last_active_at === b.last_active_at) {
						return a.name.localeCompare(b.name);
					}
					return (b.last_active_at || 0) - (a.last_active_at || 0);
				case 'created':
					if (a.created_at === b.created_at) {
						return a.name.localeCompare(b.name);
					}
					return (b.created_at || 0) - (a.created_at || 0);
				default:
					return a.name.localeCompare(b.name);
			}
		});

	const handleSelectAll = (e) => {
		const newState = e.detail;
		const filteredUserIds = filteredUsers.map((u) => u.id);

		if (newState === 'checked') {
			const combinedIds = [...new Set([...userIds, ...filteredUserIds])];
			userIds = combinedIds;
		} else {
			userIds = userIds.filter((id) => !filteredUserIds.includes(id));
		}
	};

	const addAllToGroup = () => {
		const filteredUserIds = filteredUsers.map((u) => u.id);
		const combinedIds = [...new Set([...userIds, ...filteredUserIds])];
		userIds = combinedIds;
	};

	const removeAllFromGroup = () => {
		const filteredUserIds = filteredUsers.map((u) => u.id);
		userIds = userIds.filter((id) => !filteredUserIds.includes(id));
	};
</script>

<div>
	<div class="flex w-full gap-2 mb-3">
		<div class="flex flex-1">
			<div class=" self-center mr-3">
				<Search />
			</div>
			<input
				class=" w-full text-sm pr-4 rounded-r-xl outline-hidden bg-transparent"
				bind:value={query}
				placeholder={$i18n.t('Search')}
			/>
		</div>
		<div class="flex items-center gap-2">
			<select
				bind:value={sortBy}
				class="w-full text-xs bg-transparent dark:text-gray-100 outline-none rounded-lg px-2 py-1.5 border border-gray-200 dark:border-gray-700"
			>
				<option value="members">{$i18n.t('Members First')}</option>
				<option value="name">{$i18n.t('Sort by Name')}</option>
				<option value="role">{$i18n.t('Sort by Role')}</option>
				<option value="last_active">{$i18n.t('Sort by Last Active')}</option>
				<option value="created">{$i18n.t('Sort by Created Date')}</option>
			</select>
		</div>
	</div>

	{#if filteredUsers.length > 0}
		<div class="flex items-center justify-between mb-3 pb-2 border-b border-gray-200 dark:border-gray-700">
			<div class="flex items-center gap-2">
				<Checkbox state={selectAllState} on:change={handleSelectAll} />
				<span class="text-xs text-gray-600 dark:text-gray-400">
					{$i18n.t('Select All')} ({filteredUsers.length})
				</span>
			</div>
			<div class="flex gap-1.5">
				<button
					on:click={addAllToGroup}
					class="px-2.5 py-1 text-xs font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg transition"
					title={$i18n.t('Add all filtered users to group')}
				>
					{$i18n.t('Add All')}
				</button>
				<button
					on:click={removeAllFromGroup}
					class="px-2.5 py-1 text-xs font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 rounded-lg transition"
					title={$i18n.t('Remove all filtered users from group')}
				>
					{$i18n.t('Remove All')}
				</button>
			</div>
		</div>
	{/if}

	<div class="mt-3 scrollbar-hidden">
		<div class="flex flex-col gap-2.5">
			{#if filteredUsers.length > 0}
				{#each filteredUsers as user, userIdx (user.id)}
					<div class="flex flex-row items-center gap-3 w-full text-sm">
						<div class="flex items-center">
							<Checkbox
								state={userIds.includes(user.id) ? 'checked' : 'unchecked'}
								on:change={(e) => {
									if (e.detail === 'checked') {
										userIds = [...userIds, user.id];
									} else {
										userIds = userIds.filter((id) => id !== user.id);
									}
								}}
							/>
						</div>

						<div class="flex w-full items-center justify-between overflow-hidden">
							<Tooltip content={user.email} placement="top-start">
								<div class="flex flex-col">
									<div class=" font-medium self-center truncate">{user.name}</div>
									<div class="text-xs text-gray-500 dark:text-gray-400 truncate">
										{user.role}
									</div>
								</div>
							</Tooltip>

							{#if userIds.includes(user.id)}
								<Badge type="success" content="member" />
							{/if}
						</div>
					</div>
				{/each}
			{:else}
				<div class="text-gray-500 text-xs text-center py-2 px-10">
					{$i18n.t('No users were found.')}
				</div>
			{/if}
		</div>
	</div>
</div>
