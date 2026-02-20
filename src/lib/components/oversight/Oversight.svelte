<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import type { Writable } from 'svelte/store';
	import type { i18n as i18nType } from 'i18next';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';

	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { goto } from '$app/navigation';
	import { user } from '$lib/stores';

	import {
		getOversightUsers,
		getOversightGroups,
		getOversightUserChats,
		getGroupExclusions,
		addGroupExclusion,
		removeGroupExclusion,
		type OversightUser,
		type OversightGroup,
		type OversightChat,
		type GroupExclusion
	} from '$lib/apis/oversight';

	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	// ─── State ───────────────────────────────────────────────────────────────────

	let loading = true;

	let groups: OversightGroup[] = [];
	let users: OversightUser[] = [];

	// groupId → exclusion set (user IDs excluded from oversight in that group)
	let exclusionsByGroup: Record<string, Set<string>> = {};
	// groupId → loading flag for exclusion toggles
	let exclusionLoading: Record<string, boolean> = {};

	let selectedGroupId: string | null = null;
	let selectedUser: OversightUser | null = null;

	let userChats: OversightChat[] | null = null;
	let chatsLoading = false;
	let chatsSkip = 0;
	const CHATS_LIMIT = 50;
	let allChatsLoaded = false;

	let userSearch = '';

	// ─── Derived ─────────────────────────────────────────────────────────────────

	$: filteredGroups = groups;

	$: usersInSelectedGroup = selectedGroupId
		? users.filter((u) => u.groups.some((g) => g.id === selectedGroupId))
		: users;

	$: filteredUsers = userSearch
		? usersInSelectedGroup.filter(
				(u) =>
					u.name.toLowerCase().includes(userSearch.toLowerCase()) ||
					u.email.toLowerCase().includes(userSearch.toLowerCase())
			)
		: usersInSelectedGroup;

	// ─── Data fetching ────────────────────────────────────────────────────────────

	const fetchData = async () => {
		loading = true;

		const [groupsRes, usersRes] = await Promise.allSettled([
			getOversightGroups(localStorage.token),
			getOversightUsers(localStorage.token)
		]);

		if (groupsRes.status === 'fulfilled' && groupsRes.value) {
			groups = groupsRes.value;
			// Pre-load exclusions for all groups
			await Promise.all(groups.map((g) => loadGroupExclusions(g.id)));
		} else if (groupsRes.status === 'rejected') {
			toast.error($i18n.t('Failed to load oversight groups'));
		}

		if (usersRes.status === 'fulfilled' && usersRes.value) {
			users = usersRes.value;
		} else if (usersRes.status === 'rejected') {
			toast.error($i18n.t('Failed to load oversight users'));
		}

		loading = false;
	};

	const loadGroupExclusions = async (groupId: string) => {
		const res = await getGroupExclusions(localStorage.token, groupId).catch(() => null);
		if (res) {
			exclusionsByGroup[groupId] = new Set(res.map((e: GroupExclusion) => e.user_id));
			exclusionsByGroup = { ...exclusionsByGroup };
		}
	};

	const loadUserChats = async (u: OversightUser, reset = true) => {
		if (reset) {
			selectedUser = u;
			userChats = null;
			chatsSkip = 0;
			allChatsLoaded = false;
		}

		chatsLoading = true;

		const res = await getOversightUserChats(localStorage.token, u.id, chatsSkip, CHATS_LIMIT).catch(
			() => null
		);

		if (res) {
			if (reset) {
				userChats = res;
			} else {
				userChats = [...(userChats ?? []), ...res];
			}
			allChatsLoaded = res.length < CHATS_LIMIT;
		} else {
			toast.error($i18n.t('Failed to load chats'));
		}

		chatsLoading = false;
	};

	const loadMoreChats = async () => {
		if (!selectedUser || chatsLoading || allChatsLoaded) return;
		chatsSkip += CHATS_LIMIT;
		await loadUserChats(selectedUser, false);
	};

	// ─── Exclusion toggle ─────────────────────────────────────────────────────────

	const toggleExclusion = async (groupId: string, userId: string) => {
		if (exclusionLoading[groupId + userId]) return;
		exclusionLoading = { ...exclusionLoading, [groupId + userId]: true };

		const excluded = exclusionsByGroup[groupId]?.has(userId) ?? false;

		try {
			if (excluded) {
				await removeGroupExclusion(localStorage.token, groupId, userId);
				exclusionsByGroup[groupId]?.delete(userId);
			} else {
				await addGroupExclusion(localStorage.token, groupId, userId);
				if (!exclusionsByGroup[groupId]) exclusionsByGroup[groupId] = new Set();
				exclusionsByGroup[groupId].add(userId);
			}
			exclusionsByGroup = { ...exclusionsByGroup };
		} catch (err) {
			toast.error($i18n.t('Failed to update exclusion'));
		}

		exclusionLoading = { ...exclusionLoading, [groupId + userId]: false };
	};

	// ─── Lifecycle ────────────────────────────────────────────────────────────────

	onMount(async () => {
		await fetchData();
	});
</script>

<div class="flex flex-col lg:flex-row w-full h-full pb-2 gap-0 overflow-hidden">
	<!-- ── Left panel ─────────────────────────────────────────────────── -->
	<div
		class="flex flex-col lg:w-72 xl:w-80 flex-shrink-0 border-r border-gray-100 dark:border-gray-850 overflow-y-auto"
	>
		<!-- Header -->
		<div class="px-4 pt-4 pb-3 border-b border-gray-100 dark:border-gray-850">
			<div class="flex items-center gap-2 mb-1">
				<!-- Eye icon -->
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="size-5 text-gray-500 dark:text-gray-400"
				>
					<path d="M10 12.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Z" />
					<path
						fill-rule="evenodd"
						d="M.664 10.59a1.651 1.651 0 0 1 0-1.186A10.004 10.004 0 0 1 10 3c4.257 0 7.893 2.66 9.336 6.41.147.381.146.804 0 1.186A10.004 10.004 0 0 1 10 17c-4.257 0-7.893-2.66-9.336-6.41ZM14 10a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z"
						clip-rule="evenodd"
					/>
				</svg>
				<h1 class="text-lg font-semibold text-gray-800 dark:text-gray-100">
					{$i18n.t('Group Oversight')}
				</h1>
			</div>
			<p class="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
				{$i18n.t('Monitor chats and manage exclusions for overseen groups.')}
			</p>
		</div>

		{#if loading}
			<div class="flex items-center justify-center flex-1 py-12">
				<Spinner />
			</div>
		{:else}
			<!-- Groups -->
			<div class="px-4 pt-3 pb-1">
				<p
					class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2"
				>
					{$i18n.t('Groups')}
				</p>
			</div>

			{#if groups.length === 0}
				<div class="px-4 py-3 text-sm text-gray-400 dark:text-gray-500 italic">
					{$i18n.t('No groups to oversee.')}
				</div>
			{:else}
				<div class="px-2 space-y-0.5 mb-3">
					<!-- "All" pseudo-group -->
					<button
						class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors
							{selectedGroupId === null
							? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-gray-100'
							: 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/60'}"
						on:click={() => {
							selectedGroupId = null;
							selectedUser = null;
							userChats = null;
						}}
					>
						<span>{$i18n.t('All groups')}</span>
						<span
							class="text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full px-2 py-0.5"
						>
							{users.length}
						</span>
					</button>

					{#each groups as group (group.id)}
						<button
							class="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm transition-colors
								{selectedGroupId === group.id
								? 'bg-gray-100 dark:bg-gray-800 font-medium text-gray-900 dark:text-gray-100'
								: 'text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-800/60'}"
							on:click={() => {
								selectedGroupId = group.id;
								selectedUser = null;
								userChats = null;
							}}
						>
							<span class="truncate text-left">{group.name}</span>
							<span
								class="ml-2 flex-shrink-0 text-xs bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full px-2 py-0.5"
							>
								{group.member_count}
							</span>
						</button>
					{/each}
				</div>
			{/if}

			<!-- Users -->
			<div class="px-4 pt-1 pb-1 border-t border-gray-100 dark:border-gray-850">
				<p
					class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mt-3 mb-2"
				>
					{$i18n.t('Overseen Users')}
				</p>
				<!-- Search -->
				<div class="relative mb-2">
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-gray-400"
					>
						<path
							fill-rule="evenodd"
							d="M9 3.5a5.5 5.5 0 1 0 0 11 5.5 5.5 0 0 0 0-11ZM2 9a7 7 0 1 1 12.452 4.391l3.328 3.329a.75.75 0 1 1-1.06 1.06l-3.329-3.328A7 7 0 0 1 2 9Z"
							clip-rule="evenodd"
						/>
					</svg>
					<input
						type="text"
						bind:value={userSearch}
						placeholder={$i18n.t('Search users...')}
						class="w-full pl-8 pr-3 py-1.5 text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 placeholder-gray-400 dark:placeholder-gray-500 border-0 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
					/>
				</div>
			</div>

			<!-- User list -->
			<div class="px-2 overflow-y-auto flex-1 space-y-0.5 pb-4">
				{#if filteredUsers.length === 0}
					<p class="px-3 py-3 text-sm text-gray-400 dark:text-gray-500 italic">
						{$i18n.t('No users found.')}
					</p>
				{:else}
					{#each filteredUsers as u (u.id)}
						<button
							class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors
								{selectedUser?.id === u.id
								? 'bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-200 dark:ring-blue-800'
								: 'hover:bg-gray-50 dark:hover:bg-gray-800/60'}"
							on:click={() => loadUserChats(u)}
						>
							<!-- Avatar -->
							<div
								class="size-8 rounded-full bg-gradient-to-br from-gray-300 to-gray-400 dark:from-gray-600 dark:to-gray-700 flex items-center justify-center flex-shrink-0 text-xs font-semibold text-white uppercase"
							>
								{u.name.charAt(0)}
							</div>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
									{u.name}
								</p>
								<p class="text-xs text-gray-500 dark:text-gray-400 truncate">
									{u.email}
								</p>
							</div>
						</button>
					{/each}
				{/if}
			</div>
		{/if}
	</div>

	<!-- ── Right panel ────────────────────────────────────────────────── -->
	<div class="flex-1 flex flex-col overflow-hidden">
		{#if !selectedUser}
			<!-- Empty state -->
			<div class="flex-1 flex flex-col items-center justify-center text-center px-8 py-16">
				<div
					class="size-16 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4"
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 20 20"
						fill="currentColor"
						class="size-8 text-gray-400 dark:text-gray-500"
					>
						<path
							d="M10 8a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM3.465 14.493a1.23 1.23 0 0 0 .41 1.412A9.957 9.957 0 0 0 10 18c2.31 0 4.438-.784 6.131-2.1.43-.333.604-.903.408-1.41a7.002 7.002 0 0 0-13.074.003Z"
						/>
					</svg>
				</div>
				<h2 class="text-base font-medium text-gray-700 dark:text-gray-300 mb-1">
					{$i18n.t('Select a user')}
				</h2>
				<p class="text-sm text-gray-400 dark:text-gray-500 max-w-xs">
					{$i18n.t(
						'Choose a user from the left panel to view their chats and manage oversight settings.'
					)}
				</p>
			</div>
		{:else}
			<!-- User detail header -->
			<div
				class="flex items-start justify-between gap-4 px-6 py-4 border-b border-gray-100 dark:border-gray-850"
			>
				<div class="flex items-center gap-3">
					<div
						class="size-10 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-sm font-bold text-white uppercase flex-shrink-0"
					>
						{selectedUser.name.charAt(0)}
					</div>
					<div>
						<h2 class="text-base font-semibold text-gray-800 dark:text-gray-100">
							{selectedUser.name}
						</h2>
						<p class="text-xs text-gray-500 dark:text-gray-400">{selectedUser.email}</p>
					</div>
				</div>

				<!-- Exclusion toggles for each group this user belongs to -->
				{#if selectedUser.groups.length > 0}
					<div class="flex flex-wrap gap-2">
						{#each selectedUser.groups as grp (grp.id)}
							{@const excluded = exclusionsByGroup[grp.id]?.has(selectedUser.id) ?? false}
							{@const togLoading = exclusionLoading[grp.id + selectedUser.id] ?? false}
							<button
								class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors
									{excluded
									? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-400'
									: 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 hover:border-gray-300 dark:hover:border-gray-600'}"
								disabled={togLoading}
								on:click={() => toggleExclusion(grp.id, selectedUser.id)}
								title={excluded
									? $i18n.t('Click to remove exclusion for {{group}}', { group: grp.name })
									: $i18n.t('Click to exclude from oversight in {{group}}', { group: grp.name })}
							>
								{#if togLoading}
									<svg
										class="size-3 animate-spin"
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
									>
										<circle
											class="opacity-25"
											cx="12"
											cy="12"
											r="10"
											stroke="currentColor"
											stroke-width="4"
										/>
										<path
											class="opacity-75"
											fill="currentColor"
											d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
										/>
									</svg>
								{:else if excluded}
									<!-- Eye-slash icon -->
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="size-3"
									>
										<path
											d="M2.22 2.22a.75.75 0 0 1 1.06 0l10.5 10.5a.75.75 0 1 1-1.06 1.06l-1.563-1.562a7.66 7.66 0 0 1-3.157.782c-3.942 0-7.094-2.833-7.665-6.61a.75.75 0 0 1 .624-.861.75.75 0 0 1 .861.624 6.168 6.168 0 0 0 4.124 4.894L5.94 9.94A2.5 2.5 0 0 1 8 5.5c.256 0 .504.038.737.109L7.5 4.362A7.64 7.64 0 0 0 .332 9.39a.75.75 0 0 1-1.484-.225A9.139 9.139 0 0 1 2.22 2.22Z"
										/>
										<path
											d="M8 3a7.63 7.63 0 0 1 4.84 1.719l-1.133 1.134A5.5 5.5 0 0 0 8 4.5c-.295 0-.582.024-.861.07l-1.354-1.355A7.6 7.6 0 0 1 8 3Z"
										/>
									</svg>
								{:else}
									<!-- Eye icon -->
									<svg
										xmlns="http://www.w3.org/2000/svg"
										viewBox="0 0 16 16"
										fill="currentColor"
										class="size-3"
									>
										<path d="M8 9.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3Z" />
										<path
											fill-rule="evenodd"
											d="M1.38 8.28a.87.87 0 0 1 0-.566 7.003 7.003 0 0 1 13.238.006.87.87 0 0 1 0 .566A7.003 7.003 0 0 1 1.379 8.28ZM11 8a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
											clip-rule="evenodd"
										/>
									</svg>
								{/if}
								<span class="truncate max-w-[120px]">{grp.name}</span>
								{#if excluded}
									<span class="italic opacity-70">{$i18n.t('excluded')}</span>
								{/if}
							</button>
						{/each}
					</div>
				{/if}
			</div>

			<!-- Chat list -->
			<div class="flex-1 overflow-y-auto px-6 py-4">
				<div class="flex items-center justify-between mb-3">
					<h3
						class="text-sm font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wider"
					>
						{$i18n.t('Chats')}
					</h3>
					{#if userChats !== null}
						<span class="text-xs text-gray-400 dark:text-gray-500">
							{userChats.length}{allChatsLoaded ? '' : '+'}
							{$i18n.t('chats')}
						</span>
					{/if}
				</div>

				{#if chatsLoading && userChats === null}
					<div class="flex items-center justify-center py-12">
						<Spinner />
					</div>
				{:else if userChats !== null && userChats.length === 0}
					<div class="flex flex-col items-center justify-center py-12 text-center">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="size-8 text-gray-300 dark:text-gray-600 mb-2"
						>
							<path
								fill-rule="evenodd"
								d="M2 10c0-4.418 3.582-8 8-8s8 3.582 8 8-3.582 8-8 8a7.963 7.963 0 0 1-4.95-1.707l-2.29.612a.75.75 0 0 1-.918-.919l.614-2.29A7.963 7.963 0 0 1 2 10Zm8.75-3.25a.75.75 0 0 0-1.5 0v2.5h-2.5a.75.75 0 0 0 0 1.5h2.5v2.5a.75.75 0 0 0 1.5 0v-2.5h2.5a.75.75 0 0 0 0-1.5h-2.5v-2.5Z"
								clip-rule="evenodd"
							/>
						</svg>
						<p class="text-sm text-gray-400 dark:text-gray-500">
							{$i18n.t('No chats found.')}
						</p>
					</div>
				{:else if userChats !== null}
					<div class="space-y-1">
						{#each userChats as chat (chat.id)}
							<a
								href="/c/{chat.id}"
								class="flex items-start gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors group"
							>
								<!-- Chat bubble icon -->
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="size-4 flex-shrink-0 mt-0.5 text-gray-300 dark:text-gray-600 group-hover:text-gray-400 dark:group-hover:text-gray-500 transition-colors"
								>
									<path
										fill-rule="evenodd"
										d="M2 10c0-4.418 3.582-8 8-8s8 3.582 8 8-3.582 8-8 8a7.963 7.963 0 0 1-4.95-1.707l-2.29.612a.75.75 0 0 1-.918-.919l.614-2.29A7.963 7.963 0 0 1 2 10Z"
										clip-rule="evenodd"
									/>
								</svg>
								<div class="flex-1 min-w-0">
									<p
										class="text-sm text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-gray-100 transition-colors truncate font-medium"
									>
										{chat.title || $i18n.t('Untitled chat')}
									</p>
									<p class="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
										{dayjs(chat.updated_at * 1000).format('ll')} ·
										<span title={dayjs(chat.updated_at * 1000).format('LLLL')}>
											{dayjs(chat.updated_at * 1000).fromNow()}
										</span>
									</p>
								</div>
								<!-- Arrow icon on hover -->
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 16 16"
									fill="currentColor"
									class="size-3.5 flex-shrink-0 mt-0.5 text-gray-300 dark:text-gray-600 opacity-0 group-hover:opacity-100 transition-opacity"
								>
									<path
										fill-rule="evenodd"
										d="M2 8a.75.75 0 0 1 .75-.75h8.69L8.22 4.03a.75.75 0 0 1 1.06-1.06l4.5 4.5a.75.75 0 0 1 0 1.06l-4.5 4.5a.75.75 0 0 1-1.06-1.06l3.22-3.22H2.75A.75.75 0 0 1 2 8Z"
										clip-rule="evenodd"
									/>
								</svg>
							</a>
						{/each}

						<!-- Load more -->
						{#if !allChatsLoaded}
							<button
								class="w-full flex items-center justify-center gap-2 py-3 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
								disabled={chatsLoading}
								on:click={loadMoreChats}
							>
								{#if chatsLoading}
									<svg
										class="size-4 animate-spin"
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
									>
										<circle
											class="opacity-25"
											cx="12"
											cy="12"
											r="10"
											stroke="currentColor"
											stroke-width="4"
										/>
										<path
											class="opacity-75"
											fill="currentColor"
											d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
										/>
									</svg>
									{$i18n.t('Loading...')}
								{:else}
									{$i18n.t('Load more')}
								{/if}
							</button>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Exclusion legend / help -->
			{#if selectedUser.groups.length > 0}
				<div
					class="px-6 py-3 border-t border-gray-100 dark:border-gray-850 text-xs text-gray-400 dark:text-gray-500"
				>
					{$i18n.t(
						"Exclusions prevent a user's chats from appearing in group oversight views. Toggle per group above."
					)}
				</div>
			{/if}
		{/if}
	</div>
</div>
