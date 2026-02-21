<script lang="ts">
	import { getContext, onDestroy } from 'svelte';
	const i18n = getContext('i18n');

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { getUsers } from '$lib/apis/users';
	import { toast } from 'svelte-sonner';

	import { addUserToGroup, removeUserFromGroup } from '$lib/apis/groups';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import Checkbox from '$lib/components/common/Checkbox.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Search from '$lib/components/icons/Search.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import Spinner from '$lib/components/common/Spinner.svelte';

	export let groupId: string;
	export let userCount = 0;

	let users = null;
	let total = null;

	let query = '';
	let searchDebounceTimer: ReturnType<typeof setTimeout>;
	let orderBy = 'created_at'; // default sort key
	let direction = 'desc'; // default sort order

	let page = 1;

	const setSortKey = (key) => {
		if (orderBy === key) {
			direction = direction === 'asc' ? 'desc' : 'asc';
		} else {
			orderBy = key;
			direction = 'asc';
		}
		page = 1;
	};

	const getUserList = async () => {
		try {
			const res = await getUsers(localStorage.token, query, orderBy, direction, page).catch(
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

	const toggleMember = async (userId, state) => {
		if (state === 'checked') {
			await addUserToGroup(localStorage.token, groupId, [userId]).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
		} else {
			await removeUserFromGroup(localStorage.token, groupId, [userId]).catch((error) => {
				toast.error(`${error}`);
				return null;
			});
		}

		getUserList();
	};

	$: if (page !== null && orderBy !== null && direction !== null) {
		getUserList();
	}

	$: if (query !== undefined) {
		clearTimeout(searchDebounceTimer);
		searchDebounceTimer = setTimeout(() => {
			page = 1;
			getUserList();
		}, 300);
	}

	onDestroy(() => {
		clearTimeout(searchDebounceTimer);
	});
</script>

<div class=" max-h-full h-full w-full flex flex-col overflow-y-hidden">
	<div class="w-full h-fit mb-1.5">
		<div class="flex flex-1 h-fit">
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

	{#if users === null || total === null}
		<div class="my-10">
			<Spinner className="size-5" />
		</div>
	{:else}
		{#if users.length > 0}
			<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
				<table
					class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full"
				>
					<thead class="text-xs text-gray-800 uppercase bg-transparent dark:text-gray-200">
						<tr class=" border-b-[1.5px] border-gray-50/50 dark:border-gray-800/10">
							<th
								scope="col"
								class="px-2.5 py-2 cursor-pointer text-left w-8"
								on:click={() => setSortKey(`group_id:${groupId}`)}
							>
								<div class="flex gap-1.5 items-center">
									{$i18n.t('MBR')}

									{#if orderBy === `group_id:${groupId}`}
										<span class="font-normal"
											>{#if direction === 'asc'}
												<ChevronUp className="size-2" />
											{:else}
												<ChevronDown className="size-2" />
											{/if}
										</span>
									{:else}
										<span class="invisible">
											<ChevronUp className="size-2" />
										</span>
									{/if}
								</div>
							</th>

							<th
								scope="col"
								class="px-2.5 py-2 cursor-pointer select-none"
								on:click={() => setSortKey('role')}
							>
								<div class="flex gap-1.5 items-center">
									{$i18n.t('Role')}

									{#if orderBy === 'role'}
										<span class="font-normal"
											>{#if direction === 'asc'}
												<ChevronUp className="size-2" />
											{:else}
												<ChevronDown className="size-2" />
											{/if}
										</span>
									{:else}
										<span class="invisible">
											<ChevronUp className="size-2" />
										</span>
									{/if}
								</div>
							</th>
							<th
								scope="col"
								class="px-2.5 py-2 cursor-pointer select-none"
								on:click={() => setSortKey('name')}
							>
								<div class="flex gap-1.5 items-center">
									{$i18n.t('Name')}

									{#if orderBy === 'name'}
										<span class="font-normal"
											>{#if direction === 'asc'}
												<ChevronUp className="size-2" />
											{:else}
												<ChevronDown className="size-2" />
											{/if}
										</span>
									{:else}
										<span class="invisible">
											<ChevronUp className="size-2" />
										</span>
									{/if}
								</div>
							</th>

							<th
								scope="col"
								class="px-2.5 py-2 cursor-pointer select-none"
								on:click={() => setSortKey('last_active_at')}
							>
								<div class="flex gap-1.5 items-center">
									{$i18n.t('Last Active')}

									{#if orderBy === 'last_active_at'}
										<span class="font-normal"
											>{#if direction === 'asc'}
												<ChevronUp className="size-2" />
											{:else}
												<ChevronDown className="size-2" />
											{/if}
										</span>
									{:else}
										<span class="invisible">
											<ChevronUp className="size-2" />
										</span>
									{/if}
								</div>
							</th>
						</tr>
					</thead>
					<tbody class="">
						{#each users as user, userIdx (user?.id ?? userIdx)}
							<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
								<td class=" px-3 py-1 w-8">
									<div class="flex w-full justify-center">
										<Checkbox
											state={(user?.group_ids ?? []).includes(groupId) ? 'checked' : 'unchecked'}
											on:change={(e) => {
												toggleMember(user.id, e.detail);
											}}
										/>
									</div>
								</td>
								<td class="px-3 py-1 min-w-[7rem] w-28">
									<div class=" translate-y-0.5">
										<Badge
											type={user.role === 'admin'
												? 'info'
												: user.role === 'user'
													? 'success'
													: 'muted'}
											content={$i18n.t(user.role)}
										/>
									</div>
								</td>
								<td class="px-3 py-1 font-medium text-gray-900 dark:text-white max-w-48">
									<Tooltip content={user.email} placement="top-start">
										<div class="flex items-center">
											<img
												class="rounded-full w-6 h-6 object-cover mr-2.5 flex-shrink-0"
												src={`${WEBUI_API_BASE_URL}/users/${user.id}/profile/image`}
												alt="user"
											/>

											<div class="font-medium truncate">{user.name}</div>
										</div>
									</Tooltip>
								</td>

								<td class=" px-3 py-1">
									{dayjs(user.last_active_at * 1000).fromNow()}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<div class="text-gray-500 text-xs text-center py-2 px-10">
				{$i18n.t('No users were found.')}
			</div>
		{/if}

		{#if total > 30}
			<Pagination bind:page count={total} perPage={30} />
		{/if}
	{/if}
</div>
