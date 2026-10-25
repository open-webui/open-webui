<script lang="ts">
	import ProfileImage from '$lib/components/chat/Messages/ProfileImage.svelte';
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n') as any;

	import { user as _user } from '$lib/stores';
	import { getUserInfoById, searchUsers } from '$lib/apis/users';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import { getGroups } from '$lib/apis/groups';
	import type { App } from '$lib/apis/apps';
	import Grid from '$lib/components/icons/Grid.svelte';

	export let includeGroups = true;
	export let includeUsers = true;
	export let pagination = false;
	export let includeSessionUser = false;
	export let accessGrants: { principal_type: string; principal_id: string }[] = [];

	export let groupIds: string[] = [];
	export let userIds: string[] = [];
	export let appIds: string[] = [];
	export let apps: App[] = [];
	$: filteredApps = apps.filter((app) =>
		`${app.name} ${app.slug}`.toLowerCase().includes(query.toLowerCase())
	);

	let groups: any[] | null = null;
	let filteredGroups: any[] = [];

	const hasGrant = (principalType: string, principalId: string) =>
		accessGrants.some(
			(grant) => grant.principal_type === principalType && grant.principal_id === principalId
		);

	$: filteredGroups = groups
		? groups.filter(
				(group) =>
					group.name.toLowerCase().includes(query.toLowerCase()) && !hasGrant('group', group.id)
			)
		: [];

	$: filteredUsers = (users ?? []).filter(
		(user) => !hasGrant('user', user.id) && (includeSessionUser || user?.id !== $_user?.id)
	);

	let selectedGroup: Record<string, any> = {};
	let selectedUsers: Record<string, any> = {};

	const toggleUser = (user: { id: string; [key: string]: any }) => {
		if (userIds.includes(user.id)) {
			userIds = userIds.filter((id) => id !== user.id);
			delete selectedUsers[user.id];
		} else {
			userIds = [...userIds, user.id];
			selectedUsers[user.id] = user;
		}
	};

	let page = 1;
	let users: any[] | null = null;
	let total: number | null = null;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let orderBy = 'name'; // default sort key
	let direction = 'asc'; // default sort order

	const getUserList = async () => {
		try {
			const res = await searchUsers(localStorage.token, query, orderBy, direction, page).catch(
				(error) => {
					toast.error(`${error}`);
					return null;
				}
			);

			if (res) {
				users = res.users;
				total = res.total;
			}
		} catch (err) {
			console.error(err);
		}
	};

	const handleSearchInput = () => {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			if (includeUsers) getUserList();
		}, 300);
	};

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});

	$: if (includeUsers && page !== null && orderBy !== null && direction !== null) {
		getUserList();
	} else if (!includeUsers) {
		users = [];
		total = 0;
	}

	onMount(async () => {
		groups = includeGroups
			? await getGroups(localStorage.token, true).catch((error) => {
					console.error(error);
					return [];
				})
			: [];

		if (userIds.length > 0) {
			userIds.forEach(async (id) => {
				const res = await getUserInfoById(localStorage.token, id).catch((error) => {
					console.error(error);
					return null;
				});
				if (res) {
					selectedUsers[id] = res;
				}
			});
		}
	});
</script>

<div class="">
	{#if users === null || total === null}
		<div class="my-10">
			<Spinner className="size-5" />
		</div>
	{:else}
		{#if groupIds.length > 0}
			<div class="mx-1 mb-1.5">
				<div class="text-xs text-gray-500 mx-0.5 mb-1">
					{groupIds.length}
					{$i18n.t('groups')}
				</div>
				<div class="flex gap-1 flex-wrap">
					{#each groupIds as id}
						{#if selectedGroup[id]}
							<button
								type="button"
								class="inline-flex items-center space-x-1 px-2 py-1 bg-gray-100/50 dark:bg-gray-850 rounded-lg text-xs"
								on:click={() => {
									groupIds = groupIds.filter((gid) => gid !== id);
									delete selectedGroup[id];
								}}
							>
								<div>
									{selectedGroup[id].name}
									<span class="text-xs text-gray-500">{selectedGroup[id].member_count}</span>
								</div>

								<div>
									<XMark className="size-3" />
								</div>
							</button>
						{/if}
					{/each}
				</div>
			</div>
		{/if}

		{#if userIds.length > 0}
			<div class="mx-1 mb-1.5">
				<div class="text-xs text-gray-500 mx-0.5 mb-1">
					{userIds.length}
					{$i18n.t('users')}
				</div>
				<div class="flex gap-1 flex-wrap">
					{#each userIds as id}
						{#if selectedUsers[id]}
							<button
								type="button"
								class="inline-flex items-center space-x-1 px-2 py-1 bg-gray-100/50 dark:bg-gray-850 rounded-lg text-xs"
								on:click={() => {
									userIds = userIds.filter((uid) => uid !== id);
									delete selectedUsers[id];
								}}
							>
								<div>
									{selectedUsers[id].name}
								</div>

								<div>
									<XMark className="size-3" />
								</div>
							</button>
						{/if}
					{/each}
				</div>
			</div>
		{/if}

		{#if appIds.length > 0}
			<div class="mx-1 mb-1.5">
				<div class="text-xs text-gray-500 mx-0.5 mb-1">{appIds.length} {$i18n.t('Apps')}</div>
				<div class="flex gap-1 flex-wrap">
					{#each apps.filter((app) => appIds.includes(app.id)) as app (app.id)}
						<button
							type="button"
							class="inline-flex items-center space-x-1 px-2 py-1 bg-gray-100/50 dark:bg-gray-850 rounded-lg text-xs"
							on:click={() => (appIds = appIds.filter((id) => id !== app.id))}
						>
							<span>{app.name}</span><XMark className="size-3" />
						</button>
					{/each}
				</div>
			</div>
		{/if}
		<div class="mb-1 flex items-center gap-1.5 px-1 py-1 text-gray-400">
			<Search className="size-3.5 shrink-0" />
			<input
				class="min-w-0 flex-1 border-0 bg-transparent p-0 text-xs text-gray-900 shadow-none outline-none placeholder:text-gray-400 focus:ring-0 dark:text-gray-100"
				bind:value={query}
				on:input={handleSearchInput}
				placeholder={$i18n.t('Search')}
				aria-label={$i18n.t('Search')}
			/>
		</div>

		{#if (includeUsers && filteredUsers.length > 0) || (includeGroups && filteredGroups.length > 0) || filteredApps.length > 0}
			<div class="scrollbar-hidden relative whitespace-nowrap w-full max-w-full">
				<div class=" text-sm text-left text-gray-500 dark:text-gray-400 w-full max-w-full">
					<div class="w-full max-h-96 overflow-y-auto rounded-lg">
						{#if includeGroups && filteredGroups.length > 0}
							<div class="text-xs text-gray-500 mb-1 mx-1">
								{$i18n.t('Groups')}
							</div>

							<div class="mb-3">
								{#each filteredGroups as group, groupIdx (group.id)}
									<button
										class=" dark:border-gray-850 text-xs flex items-center justify-between w-full"
										type="button"
										on:click={() => {
											if ((groupIds ?? []).includes(group.id)) {
												groupIds = groupIds.filter((id) => id !== group.id);
												delete selectedGroup[group.id];
											} else {
												groupIds = [...groupIds, group.id];
												selectedGroup[group.id] = group;
											}
										}}
									>
										<div class="px-3 py-1.5 font-normal text-gray-900 dark:text-white flex-1">
											<div class="flex items-center gap-2">
												<Tooltip content={group.name} placement="top-start">
													<div class="font-normal truncate flex items-center gap-1">
														{group.name} <span class="text-gray-500">{group.member_count}</span>
													</div>
												</Tooltip>
											</div>
										</div>

										<div class="px-3 py-1">
											<div class=" translate-y-0.5">
												<Checkbox
													state={(groupIds ?? []).includes(group.id) ? 'checked' : 'unchecked'}
												/>
											</div>
										</div>
									</button>
								{/each}
							</div>
						{/if}

						{#if includeUsers && filteredUsers.length > 0}
							<div class="text-xs text-gray-500 mb-1 mx-1">
								{$i18n.t('Users')}
							</div>

							<div>
								{#each filteredUsers as user (user.id)}
									<div
										class=" dark:border-gray-850 text-xs flex items-center justify-between w-full"
									>
										<div class="px-3 py-1 font-normal text-gray-900 dark:text-white flex-1 min-w-0">
											<div class="flex items-center gap-2">
												<ProfilePreview {user} side="right" align="center" sideOffset={6}>
													<img
														class="rounded-2xl w-6 h-6 object-cover flex-shrink-0"
														src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
														alt=""
													/>
												</ProfilePreview>
												<button
													type="button"
													class="min-w-0 truncate text-left font-normal"
													aria-pressed={userIds.includes(user.id)}
													on:click={() => toggleUser(user)}>{user.name}</button
												>

												{#if user?.is_active}
													<div>
														<span class="relative flex size-1.5">
															<span
																class="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75"
															></span>
															<span class="relative inline-flex size-1.5 rounded-full bg-green-500"
															></span>
														</span>
													</div>
												{/if}
											</div>
										</div>

										<div class="px-3 py-1">
											<div class=" translate-y-0.5">
												<Checkbox
													ariaLabel={user.name || user.email || user.id}
													on:change={() => toggleUser(user)}
													state={(userIds ?? []).includes(user.id) ? 'checked' : 'unchecked'}
												/>
											</div>
										</div>
									</div>
								{/each}
							</div>
						{/if}

						{#if filteredApps.length > 0}
							<div class="text-xs text-gray-500 mb-1 mx-1 mt-3">{$i18n.t('Apps')}</div>
							<div>
								{#each filteredApps as app (app.id)}
									<div class="text-xs flex items-center justify-between w-full">
										<button
											type="button"
											class="px-3 py-1.5 font-normal text-gray-900 dark:text-white flex-1 min-w-0"
											on:click={() =>
												(appIds = appIds.includes(app.id)
													? appIds.filter((id) => id !== app.id)
													: [...appIds, app.id])}
										>
											<div class="flex items-center gap-2">
												<div
													class="size-6 rounded-lg bg-gray-100 dark:bg-gray-850 flex items-center justify-center shrink-0"
												>
													{#if app.data.manifest.profile_image_url}
														<ProfileImage
															src={app.data.manifest.profile_image_url}
															allowExternal
															className="size-6 rounded-lg!"
														/>
													{:else}<Grid className="size-3.5" />{/if}
												</div>
												<span class="truncate">{app.name}</span>
											</div>
										</button>
										<div class="px-3 py-1">
											<Checkbox
												ariaLabel={app.name}
												state={appIds.includes(app.id) ? 'checked' : 'unchecked'}
												on:change={() =>
													(appIds = appIds.includes(app.id)
														? appIds.filter((id) => id !== app.id)
														: [...appIds, app.id])}
											/>
										</div>
									</div>
								{/each}
							</div>
						{/if}
					</div>
				</div>
			</div>
		{:else}
			<div class="text-gray-500 text-xs text-center py-5 px-10">
				{$i18n.t('No users were found.')}
			</div>
		{/if}
	{/if}
</div>
