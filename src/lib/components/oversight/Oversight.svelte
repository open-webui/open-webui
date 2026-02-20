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

	import { user } from '$lib/stores';

	import {
		getOversightTargets,
		getOversightTargetChats,
		getOversightAssignments,
		createOversightAssignment,
		deleteOversightAssignment,
		bulkAssignFromGroup,
		type OversightTarget,
		type OversightChat,
		type OversightAssignment
	} from '$lib/apis/oversight';

	import { getAllUsers } from '$lib/apis/users';
	import { getGroups } from '$lib/apis/groups';

	import Spinner from '$lib/components/common/Spinner.svelte';

	const i18n = getContext<Writable<i18nType>>('i18n');

	let loading = true;
	let targets: OversightTarget[] = [];
	let userSearch = '';
	let selectedTarget: OversightTarget | null = null;

	let userChats: OversightChat[] | null = null;
	let chatsLoading = false;
	let chatsSkip = 0;
	const CHATS_LIMIT = 50;
	let allChatsLoaded = false;

	let showAdminPanel = false;
	let assignments: OversightAssignment[] = [];
	let allUsers: { id: string; name: string; email: string }[] = [];
	let allGroups: { id: string; name: string }[] = [];
	let adminLoading = false;

	let newTargetId = '';
	let newOverseerId = '';
	let assignmentSubmitting = false;

	let bulkGroupId = '';
	let bulkOverseerId = '';
	let bulkSubmitting = false;

	$: filteredTargets = userSearch
		? targets.filter(
				(t) =>
					t.name.toLowerCase().includes(userSearch.toLowerCase()) ||
					t.email.toLowerCase().includes(userSearch.toLowerCase())
			)
		: targets;

	$: userMap = new Map(allUsers.map((u) => [u.id, { name: u.name, email: u.email }]));

	const fetchData = async () => {
		loading = true;
		const res = await getOversightTargets(localStorage.token).catch(() => null);
		if (res) {
			targets = res;
		} else {
			toast.error($i18n.t('Failed to load oversight targets'));
		}
		loading = false;
	};

	const loadAdminData = async () => {
		adminLoading = true;
		const [assignmentsRes, usersRes, groupsRes] = await Promise.allSettled([
			getOversightAssignments(localStorage.token),
			getAllUsers(localStorage.token),
			getGroups(localStorage.token)
		]);
		if (assignmentsRes.status === 'fulfilled' && assignmentsRes.value) {
			assignments = assignmentsRes.value;
		}
		if (usersRes.status === 'fulfilled' && usersRes.value) {
			// getAllUsers returns { users: [...], total: N }
			allUsers = usersRes.value.users ?? usersRes.value;
		}
		if (groupsRes.status === 'fulfilled' && groupsRes.value) {
			allGroups = groupsRes.value;
		}
		adminLoading = false;
	};

	const loadTargetChats = async (target: OversightTarget, reset = true) => {
		if (reset) {
			selectedTarget = target;
			userChats = null;
			chatsSkip = 0;
			allChatsLoaded = false;
		}
		chatsLoading = true;
		const res = await getOversightTargetChats(
			localStorage.token,
			target.id,
			chatsSkip,
			CHATS_LIMIT
		).catch(() => null);
		if (res) {
			userChats = reset ? res : [...(userChats ?? []), ...res];
			allChatsLoaded = res.length < CHATS_LIMIT;
		} else {
			toast.error($i18n.t('Failed to load chats'));
		}
		chatsLoading = false;
	};

	const loadMoreChats = async () => {
		if (!selectedTarget || chatsLoading || allChatsLoaded) return;
		chatsSkip += CHATS_LIMIT;
		await loadTargetChats(selectedTarget, false);
	};

	const toggleAdminPanel = async () => {
		showAdminPanel = !showAdminPanel;
		if (showAdminPanel && allUsers.length === 0) {
			await loadAdminData();
		}
	};

	const handleCreateAssignment = async () => {
		if (!newTargetId) return;
		assignmentSubmitting = true;
		try {
			const res = await createOversightAssignment(
				localStorage.token,
				newTargetId,
				newOverseerId || undefined
			);
			if (res) {
				assignments = [...assignments, res];
				newTargetId = '';
				newOverseerId = '';
				toast.success($i18n.t('Assignment created'));
			}
		} catch {
			toast.error($i18n.t('Failed to create assignment'));
		}
		assignmentSubmitting = false;
	};

	const handleDeleteAssignment = async (overseerId: string, targetId: string) => {
		try {
			await deleteOversightAssignment(localStorage.token, overseerId, targetId);
			assignments = assignments.filter(
				(a) => !(a.overseer_id === overseerId && a.target_id === targetId)
			);
			toast.success($i18n.t('Assignment removed'));
		} catch {
			toast.error($i18n.t('Failed to remove assignment'));
		}
	};

	const handleBulkAssign = async () => {
		if (!bulkGroupId || !bulkOverseerId) return;
		bulkSubmitting = true;
		try {
			const res = await bulkAssignFromGroup(localStorage.token, bulkGroupId, bulkOverseerId);
			if (res) {
				const updated = await getOversightAssignments(localStorage.token).catch(() => null);
				if (updated) assignments = updated;
				bulkGroupId = '';
				bulkOverseerId = '';
				toast.success($i18n.t('Bulk assignment created'));
			}
		} catch {
			toast.error($i18n.t('Failed to bulk assign'));
		}
		bulkSubmitting = false;
	};

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
					{$i18n.t('Oversight')}
				</h1>
			</div>
			<p class="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
				{$i18n.t('Monitor chats for users assigned to your oversight.')}
			</p>
		</div>

		{#if loading}
			<div class="flex items-center justify-center flex-1 py-12">
				<Spinner />
			</div>
		{:else}
			<div class="px-4 pt-3 pb-2">
				<p
					class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2"
				>
					{$i18n.t('Overseen Users')}
				</p>
				<div class="relative">
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

			<div class="px-2 overflow-y-auto flex-1 space-y-0.5 pb-2">
				{#if filteredTargets.length === 0}
					<p class="px-3 py-3 text-sm text-gray-400 dark:text-gray-500 italic">
						{$i18n.t('No users found.')}
					</p>
				{:else}
					{#each filteredTargets as target (target.id)}
						<button
							class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors
								{selectedTarget?.id === target.id && !showAdminPanel
								? 'bg-blue-50 dark:bg-blue-900/20 ring-1 ring-blue-200 dark:ring-blue-800'
								: 'hover:bg-gray-50 dark:hover:bg-gray-800/60'}"
							on:click={() => {
								showAdminPanel = false;
								loadTargetChats(target);
							}}
						>
							<div
								class="size-8 rounded-full bg-gradient-to-br from-gray-300 to-gray-400 dark:from-gray-600 dark:to-gray-700 flex items-center justify-center flex-shrink-0 text-xs font-semibold text-white uppercase"
							>
								{target.name.charAt(0)}
							</div>
							<div class="flex-1 min-w-0">
								<p class="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">
									{target.name}
								</p>
								<p class="text-xs text-gray-500 dark:text-gray-400 truncate">
									{target.email}
								</p>
							</div>
						</button>
					{/each}
				{/if}
			</div>

			{#if $user?.role === 'admin'}
				<div class="px-3 py-3 border-t border-gray-100 dark:border-gray-850">
					<button
						class="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors
							{showAdminPanel
							? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 ring-1 ring-blue-200 dark:ring-blue-800'
							: 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-700'}"
						on:click={toggleAdminPanel}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="size-4"
						>
							<path
								d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
							/>
						</svg>
						{$i18n.t('Manage Assignments')}
					</button>
				</div>
			{/if}
		{/if}
	</div>

	<div class="flex-1 flex flex-col overflow-hidden">
		{#if showAdminPanel && $user?.role === 'admin'}
			<div
				class="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-850"
			>
				<div>
					<h2 class="text-base font-semibold text-gray-800 dark:text-gray-100">
						{$i18n.t('Manage Assignments')}
					</h2>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
						{$i18n.t('Create and remove user-to-user oversight assignments.')}
					</p>
				</div>
				<button
					class="size-8 flex items-center justify-center rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
					on:click={() => (showAdminPanel = false)}
					title={$i18n.t('Close')}
				>
					<svg
						xmlns="http://www.w3.org/2000/svg"
						viewBox="0 0 16 16"
						fill="currentColor"
						class="size-4"
					>
						<path
							d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
						/>
					</svg>
				</button>
			</div>

			<div class="flex-1 overflow-y-auto px-6 py-4 space-y-6">
				{#if adminLoading}
					<div class="flex items-center justify-center py-12">
						<Spinner />
					</div>
				{:else}
					<section>
						<h3
							class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3"
						>
							{$i18n.t('Current Assignments')}
						</h3>
						{#if assignments.length === 0}
							<p class="text-sm text-gray-400 dark:text-gray-500 italic py-2">
								{$i18n.t('No assignments yet.')}
							</p>
						{:else}
							<div class="space-y-1.5">
								{#each assignments as a (a.id)}
									<div
										class="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-gray-50 dark:bg-gray-800/60 group"
									>
										<div class="flex-1 min-w-0 flex items-center gap-2 text-sm">
											<span
												class="font-medium text-gray-800 dark:text-gray-200 truncate max-w-[130px]"
												title={userMap.get(a.overseer_id)?.name ?? a.overseer_id}
											>
												{userMap.get(a.overseer_id)?.name ?? a.overseer_id}
											</span>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="size-3.5 flex-shrink-0 text-gray-400"
											>
												<path
													fill-rule="evenodd"
													d="M2 8a.75.75 0 0 1 .75-.75h8.69L8.22 4.03a.75.75 0 0 1 1.06-1.06l4.5 4.5a.75.75 0 0 1 0 1.06l-4.5 4.5a.75.75 0 0 1-1.06-1.06l3.22-3.22H2.75A.75.75 0 0 1 2 8Z"
													clip-rule="evenodd"
												/>
											</svg>
											<span
												class="font-medium text-gray-800 dark:text-gray-200 truncate max-w-[130px]"
												title={userMap.get(a.target_id)?.name ?? a.target_id}
											>
												{userMap.get(a.target_id)?.name ?? a.target_id}
											</span>
											{#if a.source}
												<span
													class="flex-shrink-0 text-xs bg-gray-200 dark:bg-gray-700 text-gray-500 dark:text-gray-400 rounded-full px-2 py-0.5"
												>
													{a.source}
												</span>
											{/if}
										</div>
										<span
											class="flex-shrink-0 text-xs text-gray-400 dark:text-gray-500"
											title={dayjs(a.created_at * 1000).format('LLLL')}
										>
											{dayjs(a.created_at * 1000).format('ll')}
										</span>
										<button
											class="flex-shrink-0 size-6 flex items-center justify-center rounded text-gray-300 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors opacity-0 group-hover:opacity-100"
											on:click={() => handleDeleteAssignment(a.overseer_id, a.target_id)}
											title={$i18n.t('Remove assignment')}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												viewBox="0 0 16 16"
												fill="currentColor"
												class="size-3.5"
											>
												<path
													d="M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 1 0 1.06 1.06L8 9.06l2.72 2.72a.75.75 0 1 0 1.06-1.06L9.06 8l2.72-2.72a.75.75 0 0 0-1.06-1.06L8 6.94 5.28 4.22Z"
												/>
											</svg>
										</button>
									</div>
								{/each}
							</div>
						{/if}
					</section>

					<section class="border-t border-gray-100 dark:border-gray-850 pt-5">
						<h3
							class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-3"
						>
							{$i18n.t('Add Assignment')}
						</h3>
						<form
							class="flex flex-wrap items-end gap-3"
							on:submit|preventDefault={handleCreateAssignment}
						>
							<div class="flex-1 min-w-[160px]">
								<label
									class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
									for="overseer-select"
								>
									{$i18n.t('Overseer')}
								</label>
								<select
									id="overseer-select"
									bind:value={newOverseerId}
									class="w-full text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border-0 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
								>
									<option value="">{$i18n.t('Self (current user)')}</option>
									{#each allUsers as u (u.id)}
										<option value={u.id}>{u.name}</option>
									{/each}
								</select>
							</div>
							<div class="flex-1 min-w-[160px]">
								<label
									class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
									for="target-select"
								>
									{$i18n.t('Target')}
								</label>
								<select
									id="target-select"
									bind:value={newTargetId}
									required
									class="w-full text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border-0 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
								>
									<option value="">{$i18n.t('Select target...')}</option>
									{#each allUsers as u (u.id)}
										<option value={u.id}>{u.name}</option>
									{/each}
								</select>
							</div>
							<button
								type="submit"
								disabled={assignmentSubmitting || !newTargetId}
								class="flex-shrink-0 px-4 py-1.5 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
							>
								{assignmentSubmitting ? $i18n.t('Adding...') : $i18n.t('Add')}
							</button>
						</form>
					</section>

					<section class="border-t border-gray-100 dark:border-gray-850 pt-5">
						<h3
							class="text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-1"
						>
							{$i18n.t('Bulk Assign from Group')}
						</h3>
						<p class="text-xs text-gray-400 dark:text-gray-500 mb-3">
							{$i18n.t('Assign all members of a group to an overseer at once.')}
						</p>
						<form
							class="flex flex-wrap items-end gap-3"
							on:submit|preventDefault={handleBulkAssign}
						>
							<div class="flex-1 min-w-[160px]">
								<label
									class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
									for="bulk-group-select"
								>
									{$i18n.t('Group')}
								</label>
								<select
									id="bulk-group-select"
									bind:value={bulkGroupId}
									required
									class="w-full text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border-0 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
								>
									<option value="">{$i18n.t('Select group...')}</option>
									{#each allGroups as g (g.id)}
										<option value={g.id}>{g.name}</option>
									{/each}
								</select>
							</div>
							<div class="flex-1 min-w-[160px]">
								<label
									class="block text-xs text-gray-500 dark:text-gray-400 mb-1"
									for="bulk-overseer-select"
								>
									{$i18n.t('Overseer')}
								</label>
								<select
									id="bulk-overseer-select"
									bind:value={bulkOverseerId}
									required
									class="w-full text-sm rounded-lg bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 border-0 px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/30"
								>
									<option value="">{$i18n.t('Select overseer...')}</option>
									{#each allUsers as u (u.id)}
										<option value={u.id}>{u.name}</option>
									{/each}
								</select>
							</div>
							<button
								type="submit"
								disabled={bulkSubmitting || !bulkGroupId || !bulkOverseerId}
								class="flex-shrink-0 px-4 py-1.5 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-colors"
							>
								{bulkSubmitting ? $i18n.t('Assigning...') : $i18n.t('Bulk Assign')}
							</button>
						</form>
					</section>
				{/if}
			</div>
		{:else if selectedTarget}
			<div class="flex items-center gap-4 px-6 py-4 border-b border-gray-100 dark:border-gray-850">
				<div
					class="size-10 rounded-full bg-gradient-to-br from-blue-400 to-indigo-500 flex items-center justify-center text-sm font-bold text-white uppercase flex-shrink-0"
				>
					{selectedTarget.name.charAt(0)}
				</div>
				<div class="flex-1 min-w-0">
					<h2 class="text-base font-semibold text-gray-800 dark:text-gray-100">
						{selectedTarget.name}
					</h2>
					<p class="text-xs text-gray-500 dark:text-gray-400">{selectedTarget.email}</p>
				</div>
				{#if selectedTarget.groups.length > 0}
					<div class="flex flex-wrap gap-1.5">
						{#each selectedTarget.groups as grp (grp.id)}
							<span
								class="text-xs bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400 rounded-full px-2.5 py-1"
							>
								{grp.name}
							</span>
						{/each}
					</div>
				{/if}
			</div>

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
		{:else}
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
					{$i18n.t('Choose a user from the left panel to view their chats.')}
				</p>
			</div>
		{/if}
	</div>
</div>
