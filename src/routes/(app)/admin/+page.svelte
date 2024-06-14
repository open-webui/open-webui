<script>
	import { WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, showSidebar } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { onMount, getContext } from 'svelte';

	import dayjs from 'dayjs';
	import relativeTime from 'dayjs/plugin/relativeTime';
	dayjs.extend(relativeTime);

	import { toast } from 'svelte-sonner';

	import { updateUserRole, getUsers, deleteUserById } from '$lib/apis/users';

	import EditUserModal from '$lib/components/admin/EditUserModal.svelte';
	import Pagination from '$lib/components/common/Pagination.svelte';
	import ChatBubbles from '$lib/components/icons/ChatBubbles.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import UserChatsModal from '$lib/components/admin/UserChatsModal.svelte';
	import AddUserModal from '$lib/components/admin/AddUserModal.svelte';

	const i18n = getContext('i18n');

	let loaded = false;
	let tab = '';
	let users = [];

	let search = '';
	let selectedUser = null;

	let page = 1;

	let showAddUserModal = false;

	let showUserChatsModal = false;
	let showEditUserModal = false;

	const updateRoleHandler = async (id, role) => {
		const res = await updateUserRole(localStorage.token, id, role).catch((error) => {
			toast.error(error);
			return null;
		});

		if (res) {
			users = await getUsers(localStorage.token);
		}
	};

	const editUserPasswordHandler = async (id, password) => {
		const res = await deleteUserById(localStorage.token, id).catch((error) => {
			toast.error(error);
			return null;
		});
		if (res) {
			users = await getUsers(localStorage.token);
			toast.success($i18n.t('Successfully updated.'));
		}
	};

	const deleteUserHandler = async (id) => {
		const res = await deleteUserById(localStorage.token, id).catch((error) => {
			toast.error(error);
			return null;
		});
		if (res) {
			users = await getUsers(localStorage.token);
		}
	};

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		} else {
			users = await getUsers(localStorage.token);
		}
		loaded = true;
	});
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

{#if loaded}
	<div class="mt-0.5 mb-3 gap-1 flex flex-col md:flex-row justify-between">
		<div class="flex md:self-center text-lg font-medium px-0.5">
			{$i18n.t('All Users')}
			<div class="flex self-center w-[1px] h-6 mx-2.5 bg-gray-200 dark:bg-gray-700" />
			<span class="text-lg font-medium text-gray-500 dark:text-gray-300">{users.length}</span>
		</div>

		<div class="flex gap-1">
			<input
				class="w-full md:w-60 rounded-xl py-1.5 px-4 text-sm dark:text-gray-300 dark:bg-gray-850 outline-none"
				placeholder={$i18n.t('Search')}
				bind:value={search}
			/>

			<div class="flex gap-0.5">
				<Tooltip content={$i18n.t('Add User')}>
					<button
						class=" px-2 py-2 rounded-xl border border-gray-200 dark:border-gray-600 dark:border-0 hover:bg-gray-100 dark:bg-gray-850 dark:hover:bg-gray-800 transition font-medium text-sm flex items-center space-x-1"
						on:click={() => {
							showAddUserModal = !showAddUserModal;
						}}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 16 16"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								d="M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5a.75.75 0 0 0 0 1.5h3.5v3.5a.75.75 0 0 0 1.5 0v-3.5h3.5a.75.75 0 0 0 0-1.5h-3.5v-3.5Z"
							/>
						</svg>
					</button>
				</Tooltip>
			</div>
		</div>
	</div>

	<div class="scrollbar-hidden relative whitespace-nowrap overflow-x-auto max-w-full">
		<table class="w-full text-sm text-left text-gray-500 dark:text-gray-400 table-auto max-w-full">
			<thead class="text-xs text-gray-700 uppercase bg-gray-50 dark:bg-gray-850 dark:text-gray-400">
				<tr>
					<th scope="col" class="px-3 py-2"> {$i18n.t('Role')} </th>
					<th scope="col" class="px-3 py-2"> {$i18n.t('Name')} </th>
					<th scope="col" class="px-3 py-2"> {$i18n.t('Email')} </th>
					<th scope="col" class="px-3 py-2"> {$i18n.t('Last Active')} </th>

					<th scope="col" class="px-3 py-2"> {$i18n.t('Created at')} </th>

					<th scope="col" class="px-3 py-2 text-right" />
				</tr>
			</thead>
			<tbody>
				{#each users
					.filter((user) => {
						if (search === '') {
							return true;
						} else {
							let name = user.name.toLowerCase();
							const query = search.toLowerCase();
							return name.includes(query);
						}
					})
					.slice((page - 1) * 20, page * 20) as user}
					<tr class="bg-white border-b dark:bg-gray-900 dark:border-gray-850 text-xs">
						<td class="px-3 py-2 min-w-[7rem] w-28">
							<button
								class=" flex items-center gap-2 text-xs px-3 py-0.5 rounded-lg {user.role ===
									'admin' && 'text-sky-600 dark:text-sky-200 bg-sky-200/30'} {user.role ===
									'user' && 'text-green-600 dark:text-green-200 bg-green-200/30'} {user.role ===
									'pending' && 'text-gray-600 dark:text-gray-200 bg-gray-200/30'}"
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
								<div
									class="w-1 h-1 rounded-full {user.role === 'admin' &&
										'bg-sky-600 dark:bg-sky-300'} {user.role === 'user' &&
										'bg-green-600 dark:bg-green-300'} {user.role === 'pending' &&
										'bg-gray-600 dark:bg-gray-300'}"
								/>
								{$i18n.t(user.role)}</button
							>
						</td>
						<td class="px-3 py-2 font-medium text-gray-900 dark:text-white w-max">
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
						<td class=" px-3 py-2"> {user.email} </td>

						<td class=" px-3 py-2">
							{dayjs(user.last_active_at * 1000).fromNow()}
						</td>

						<td class=" px-3 py-2">
							{dayjs(user.created_at * 1000).format($i18n.t('MMMM DD, YYYY'))}
						</td>

						<td class="px-3 py-2 text-right">
							<div class="flex justify-end w-full">
								{#if user.role !== 'admin'}
									<Tooltip content={$i18n.t('Chats')}>
										<button
											class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											on:click={async () => {
												showUserChatsModal = !showUserChatsModal;
												selectedUser = user;
											}}
										>
											<ChatBubbles />
										</button>
									</Tooltip>

									<Tooltip content={$i18n.t('Edit User')}>
										<button
											class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											on:click={async () => {
												showEditUserModal = !showEditUserModal;
												selectedUser = user;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="w-4 h-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
												/>
											</svg>
										</button>
									</Tooltip>

									<Tooltip content={$i18n.t('Delete User')}>
										<button
											class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											on:click={async () => {
												deleteUserHandler(user.id);
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="w-4 h-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0"
												/>
											</svg>
										</button>
									</Tooltip>
								{:else}
									<Tooltip content={$i18n.t('Edit User')}>
										<button
											class="self-center w-fit text-sm px-2 py-2 hover:bg-black/5 dark:hover:bg-white/5 rounded-xl"
											on:click={async () => {
												showEditUserModal = !showEditUserModal;
												selectedUser = user;
											}}
										>
											<svg
												xmlns="http://www.w3.org/2000/svg"
												fill="none"
												viewBox="0 0 24 24"
												stroke-width="1.5"
												stroke="currentColor"
												class="w-4 h-4"
											>
												<path
													stroke-linecap="round"
													stroke-linejoin="round"
													d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125"
												/>
											</svg>
										</button>
									</Tooltip>
								{/if}
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<div class=" text-gray-500 text-xs mt-2 text-right">
		ⓘ {$i18n.t("Click on the user role button to change a user's role.")}
	</div>

	<Pagination bind:page count={users.length} />
{/if}

<style>
	.font-mona {
		font-family: 'Mona Sans';
	}

	.scrollbar-hidden::-webkit-scrollbar {
		display: none; /* for Chrome, Safari and Opera */
	}

	.scrollbar-hidden {
		-ms-overflow-style: none; /* IE and Edge */
		scrollbar-width: none; /* Firefox */
	}
</style>
