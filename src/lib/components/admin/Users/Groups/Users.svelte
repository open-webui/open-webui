<script lang="ts">
	import { getContext } from 'svelte';
	const i18n = getContext('i18n');

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { WEBUI_BASE_URL } from '$lib/constants';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';

	export let users = [];
	export let userIds = [];

	const COLUMN_COUNT = 6;

	let filteredUsers = [];
	let query = '';
	let orderBy = 'name';
	let direction: 'asc' | 'desc' = 'asc';
	let selectAllState: 'checked' | 'unchecked' | 'indeterminate' = 'unchecked';

	const getSelectAllState = (filteredUsers, userIds) => {
		const filteredUserIds = filteredUsers.map((u) => u.id);
		const selectedCount = filteredUserIds.filter((id) => userIds.includes(id)).length;

		if (selectedCount === 0) return 'unchecked';
		if (selectedCount === filteredUserIds.length) return 'checked';
		return 'indeterminate';
	};

	const setSortKey = (key) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
	};

	const handleSelectAll = () => {
		const filteredUserIds = filteredUsers.map((u) => u.id);
		const allFilteredSelected = filteredUserIds.every((id) => userIds.includes(id));

		userIds = allFilteredSelected
			? userIds.filter((id) => !filteredUserIds.includes(id))
			: [...new Set([...userIds, ...filteredUserIds])];
	};

	const getProfileImageUrl = (profileUrl) => {
		if (!profileUrl) return `${WEBUI_BASE_URL}/user.png`;
		if (profileUrl.startsWith(WEBUI_BASE_URL)) return profileUrl;
		if (profileUrl.startsWith('https://www.gravatar.com/avatar/')) return profileUrl;
		if (profileUrl.startsWith('data:')) return profileUrl;
		return `${WEBUI_BASE_URL}/user.png`;
	};

	const getBadgeType = (role) => {
		switch (role) {
			case 'admin':
				return 'info';
			case 'user':
				return 'success';
			default:
				return 'muted';
		}
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
			let compareResult = 0;

			switch (orderBy) {
				case 'email':
					compareResult = a.email.localeCompare(b.email);
					break;
				case 'role':
					compareResult = a.role.localeCompare(b.role);
					break;
				case 'last_active_at':
					compareResult = (a.last_active_at || 0) - (b.last_active_at || 0);
					break;
				case 'created_at':
					compareResult = (a.created_at || 0) - (b.created_at || 0);
					break;
				default:
					compareResult = a.name.localeCompare(b.name);
			}

			return direction === 'asc' ? compareResult : -compareResult;
		});
</script>

{#snippet sortHeader(key, label)}
	<th scope="col" class="px-2.5 py-2 cursor-pointer select-none" on:click={() => setSortKey(key)}>
		<div class="flex gap-1.5 items-center">
			{$i18n.t(label)}
			<span class:invisible={orderBy !== key} class="w-2">
				{#if direction === 'asc'}
					<ChevronUp className="size-2" />
				{:else}
					<ChevronDown className="size-2" />
				{/if}
			</span>
		</div>
	</th>
{/snippet}

<div>
	<div class="flex w-full mb-3">
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
	</div>

	<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
		<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full">
			<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
				<tr class=" border-b-[1.5px] border-gray-50 dark:border-gray-850">
					<th scope="col" class="px-2.5 py-2">
						<Checkbox state={selectAllState} on:change={handleSelectAll} />
					</th>
					{@render sortHeader('role', 'Role')}
					{@render sortHeader('name', 'Name')}
					{@render sortHeader('email', 'Email')}
					{@render sortHeader('last_active_at', 'Last Active')}
					{@render sortHeader('created_at', 'Created at')}
				</tr>
			</thead>
			<tbody>
				{#if filteredUsers.length > 0}
					{#each filteredUsers as user (user.id)}
						<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
							<td class="px-3 py-1">
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
							</td>
							<td class="px-3 py-1 min-w-[7rem] w-28">
								<Badge type={getBadgeType(user.role)} content={$i18n.t(user.role)} />
							</td>
							<td class="px-3 py-1 font-medium text-gray-900 dark:text-white max-w-48">
								<div class="flex items-center">
									<img
										class="rounded-full w-6 h-6 object-cover mr-2.5 flex-shrink-0"
										src={getProfileImageUrl(user?.profile_image_url)}
										alt="user"
									/>
									<div class="font-medium truncate">{user.name}</div>
								</div>
							</td>
							<td class="px-3 py-1">{user.email}</td>
							<td class="px-3 py-1">
								{dayjs(user.last_active_at * 1000).fromNow()}
							</td>
							<td class="px-3 py-1">
								{dayjs(user.created_at * 1000).format('LL')}
							</td>
						</tr>
					{/each}
				{:else}
					<tr>
						<td colspan={COLUMN_COUNT} class="text-gray-500 text-xs text-center py-4">
							{$i18n.t('No users were found.')}
						</td>
					</tr>
				{/if}
			</tbody>
		</table>
	</div>
</div>
