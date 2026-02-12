<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { getContext, onMount, onDestroy } from 'svelte';

	const i18n = getContext('i18n');

	import { user as _user } from '$lib/stores';
	import { getUserInfoById, searchUsers } from '$lib/apis/users';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import XMark from '$lib/components/icons/XMark.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import ProfilePreview from '$lib/components/channel/Messages/Message/ProfilePreview.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import { getGroups } from '$lib/apis/groups';

	export let includeGroups = true;
	export let pagination = false;

	export let groupIds = [];
	export let userIds = [];

	let groups = null;
	let filteredGroups = [];

	$: filteredGroups = groups
		? groups.filter((group) => group.name.toLowerCase().includes(query.toLowerCase()))
		: [];

	let selectedGroup = {};
	let selectedUsers = {};

	let page = 1;
	let users = null;
	let total = null;

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

	$: if (query !== undefined) {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			getUserList();
		}, 300);
	}

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});

	$: if (page !== null && orderBy !== null && direction !== null) {
		getUserList();
	}

	onMount(async () => {
		groups = await getGroups(localStorage.token, true).catch((error) => {
			console.error(error);
			return [];
		});

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

		<div class="flex gap-1 mb-1">
			<div class=" flex w-full space-x-2">
				<div class="flex flex-1">
					<div class=" self-center ml-1 mr-3">
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
								clip-rule="evenodd"
							/>
						</svg>
					</div>
					<input
						class=" w-full text-sm pr-4 py-1 rounded-r-xl outline-hidden bg-transparent"
						bind:value={query}
						placeholder={$i18n.t('Search')}
					/>
				</div>
			</div>
		</div>

		{#if users.length > 0}
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
										<div class="px-3 py-1.5 font-medium text-gray-900 dark:text-white flex-1">
											<div class="flex items-center gap-2">
												<Tooltip content={group.name} placement="top-start">
													<div class="font-medium truncate flex items-center gap-1">
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

						<div class="text-xs text-gray-500 mb-1 mx-1">
							{$i18n.t('Users')}
						</div>

						<div>
							{#each users as user, userIdx (user.id)}
								{#if user?.id !== $_user?.id}
									<button
										class=" dark:border-gray-850 text-xs flex items-center justify-between w-full"
										type="button"
										on:click={() => {
											if ((userIds ?? []).includes(user.id)) {
												userIds = userIds.filter((id) => id !== user.id);
												delete selectedUsers[user.id];
											} else {
												userIds = [...userIds, user.id];
												selectedUsers[user.id] = user;
											}
										}}
									>
										<div class="px-3 py-1.5 font-medium text-gray-900 dark:text-white flex-1">
											<div class="flex items-center gap-2">
												<ProfilePreview {user} side="right" align="center" sideOffset={6}>
													<img
														class="rounded-2xl w-6 h-6 object-cover flex-shrink-0"
														src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
														alt="user"
													/>
												</ProfilePreview>
												<Tooltip content={user.email} placement="top-start">
													<div class="font-medium truncate">{user.name}</div>
												</Tooltip>

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
													state={(userIds ?? []).includes(user.id) ? 'checked' : 'unchecked'}
												/>
											</div>
										</div>
									</button>
								{/if}
							{/each}
						</div>
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
