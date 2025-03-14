<script>
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	import localizedFormat from 'dayjs/plugin/localizedFormat';
	dayjs.extend(relativeTime);
	dayjs.extend(localizedFormat);

	import { toast } from 'svelte-sonner';

	import { updateUserRole, getUsers, deleteUserById } from '$lib/apis/users';

	import Pagination from '$lib/components/common/Pagination.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';

	import EditUserModal from '$lib/components/admin/Users/UserList/EditUserModal.svelte';
	import UserChatsModal from '$lib/components/admin/Users/UserList/UserChatsModal.svelte';
	import AddUserModal from '$lib/components/admin/Users/UserList/AddUserModal.svelte';

	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import ChevronUp from '$lib/components/icons/ChevronUp.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import About from '$lib/components/chat/Settings/About.svelte';
	import Banner from '$lib/components/common/Banner.svelte';

	import {} from '$lib/apis/aifred/rag-data-create-mgmt/index';

	const i18n = getContext('i18n');

	export let users = [];

	let search = '';
	let selectedUser = null;

	let page = 1;

	let showDeleteConfirmDialog = false;
	let showAddUserModal = false;

	let showUserChatsModal = false;
	let showEditUserModal = false;

	const updateRoleHandler = async (id, role) => {
		const res = await updateUserRole(localStorage.token, id, role).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			users = await getUsers(localStorage.token);
		}
	};

	const deleteHandler = async (id) => {
		const res = await deleteUserById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (res) {
			users = await getUsers(localStorage.token);
		}
	};

	let sortKey = 'created_at'; // default sort key
	let sortOrder = 'asc'; // default sort order

	function setSortKey(key) {
		if (sortKey === key) {
			sortOrder = sortOrder === 'asc' ? 'desc' : 'asc';
		} else {
			sortKey = key;
			sortOrder = 'asc';
		}
	}

	let filteredData;

	$: filteredData = users
		.filter((user) => {
			if (search === '') {
				return true;
			} else {
				let name = user.name.toLowerCase();
				let email = user.email.toLowerCase();
				const query = search.toLowerCase();
				return name.includes(query) || email.includes(query);
			}
		})
		.sort((a, b) => {
			if (a[sortKey] < b[sortKey]) return sortOrder === 'asc' ? -1 : 1;
			if (a[sortKey] > b[sortKey]) return sortOrder === 'asc' ? 1 : -1;
			return 0;
		})
		.slice((page - 1) * 20, page * 20);
</script>

{#key selectedUser}
	<EditUserModal
		bind:show={showEditUserModal}
		{selectedUser}
		sessionUser={$user}
		on:save={async () => {
			users = await getUsers(localStorage.token);
		}}
	/>
{/key}

<AddUserModal
	bind:show={showAddUserModal}
	on:save={async () => {
		users = await getUsers(localStorage.token);
	}}
/>
<UserChatsModal bind:show={showUserChatsModal} user={selectedUser} />

<div class="mt-0.5 mb-2 gap-1 flex flex-col md:flex-row justify-between">
	<div class="flex md:self-center text-lg font-medium px-0.5">
		<div class="flex-shrink-0">
			{$i18n.t('Users')}
		</div>
		<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-50 dark:bg-gray-850" />

		<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{users.length}</span>
	</div>

	<div class="flex gap-1">
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
					bind:value={search}
					placeholder={$i18n.t('Search')}
				/>
			</div>

			<div>
				<Tooltip content={$i18n.t('Add User')}>
					<button
						class=" p-2 rounded-xl hover:bg-gray-100 dark:bg-gray-900 dark:hover:bg-gray-850 transition font-medium text-sm flex items-center space-x-1"
						on:click={() => {
							showAddUserModal = !showAddUserModal;
						}}
					>
						<Plus className="size-3.5" />
					</button>
				</Tooltip>
			</div>
		</div>
	</div>
</div>

<div
	class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full rounded-sm pt-0.5"
>
	<table
		class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full rounded-sm"
	>
		<thead
			class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400 -translate-y-0.5"
		>
			<tr class="">
				<th
					scope="col"
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('role')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Target Index')}

						{#if sortKey === 'role'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
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
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('name')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Target Path')}

						{#if sortKey === 'name'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
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
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('email')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Process Type')}

						{#if sortKey === 'email'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
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
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('last_active_at')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Complete Result')}

						{#if sortKey === 'last_active_at'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
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
					class="px-3 py-1.5 cursor-pointer select-none"
					on:click={() => setSortKey('created_at')}
				>
					<div class="flex gap-1.5 items-center">
						{$i18n.t('Execute Statuis')}
						{#if sortKey === 'created_at'}
							<span class="font-normal"
								>{#if sortOrder === 'asc'}
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
			{#each filteredData as user, userIdx}
				<tr class="bg-white dark:bg-gray-900 dark:border-gray-850 text-xs">
					<td class="px-3 py-1 min-w-[7rem] w-28">
						<button
							class=" translate-y-0.5"
							on:click={() => {
								if (user.role === 'user') {
									updateRoleHandler(user.id, 'admin');
								} else if (user.role === 'pending') {
									updateRoleHandler(user.id, 'user');
								} else {
									updateRoleHandler(user.id, 'pending');
								}
							}}
						>
							<Badge
								type={user.role === 'admin' ? 'info' : user.role === 'user' ? 'success' : 'muted'}
								content={$i18n.t(user.role)}
							/>
						</button>
					</td>
					<td class="px-3 py-1 font-medium text-gray-900 dark:text-white w-max">
						<div class="flex flex-row w-max">
							<img
								class=" rounded-full w-6 h-6 object-cover mr-2.5"
								src={user.profile_image_url.startsWith(WEBUI_BASE_URL) ||
								user.profile_image_url.startsWith('https://www.gravatar.com/avatar/') ||
								user.profile_image_url.startsWith('data:')
									? user.profile_image_url
									: `/user.png`}
								alt="user"
							/>

							<div class=" font-medium self-center">{user.name}</div>
						</div>
					</td>
					<td class=" px-3 py-1"> {user.email} </td>

					<td class=" px-3 py-1">
						{dayjs(user.last_active_at * 1000).fromNow()}
					</td>
					<td class=" px-3 py-1">
						{dayjs(user.created_at * 1000).format('LL')}
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>

<Pagination bind:page count={users.length} />
